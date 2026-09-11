"""Cache read/write logic (CLAUDE.md AI Service Design — Caching Logic).

get_lesson / get_questions implement the exact flow specified in CLAUDE.md:
check cache -> generate + validate on miss/force_refresh -> retry once on
validation failure -> store only validated content -> on repeated AI
failure, fall back to a stale cached row if one exists rather than raising.
"""

import json
import logging
from datetime import datetime
from typing import Optional

from pydantic import ValidationError
from sqlalchemy.orm import Session

from models import LessonCache, QuestionCache, RegenerationLog, Topic
from schemas import LESSON_SCHEMA_VERSION, LessonSchema, QuestionSetSchema
from services import ai_service

logger = logging.getLogger("mathsai")

VALID_DIFFICULTIES = {"Fluency", "Reasoning", "Problem-solving"}


class TopicNotFoundError(Exception):
    pass


class ContentNotCachedError(Exception):
    """Raised when marking content reviewed before anything has ever been
    generated for it — there is nothing to mark."""


def _get_topic_or_raise(db: Session, topic_id: int) -> Topic:
    topic = db.query(Topic).filter(Topic.id == topic_id).first()
    if topic is None:
        raise TopicNotFoundError(f"Topic {topic_id} not found")
    return topic


def _log_regeneration(db: Session, topic_id: int, content_type: str) -> None:
    """Every force_refresh=true call writes a row here (CLAUDE.md Production
    Hardening — Cost guardrails on regeneration), so accidental repeated
    clicks are visible after the fact regardless of whether generation goes
    on to succeed or fail."""
    db.add(RegenerationLog(topic_id=topic_id, content_type=content_type, timestamp=datetime.utcnow()))
    db.commit()


# --- Lessons -----------------------------------------------------------


def get_lesson(db: Session, topic_id: int, force_refresh: bool = False) -> dict:
    topic = _get_topic_or_raise(db, topic_id)
    existing = db.query(LessonCache).filter(LessonCache.topic_id == topic.id).first()

    if not force_refresh and existing is not None:
        logger.info("Cache hit: lesson topic_id=%d", topic.id)
        return _lesson_row_to_dict(existing)

    if force_refresh:
        _log_regeneration(db, topic.id, "lesson")

    try:
        validated = _generate_and_validate_lesson(topic)
    except ai_service.AIGenerationError:
        if existing is not None:
            logger.error(
                "Lesson generation failed for topic_id=%d; serving stale cache "
                "from %s",
                topic.id,
                existing.generated_at,
            )
            return _lesson_row_to_dict(existing, stale=True)
        logger.error(
            "Lesson generation failed for topic_id=%d; no cached content to fall back to",
            topic.id,
        )
        raise

    row = existing if existing is not None else LessonCache(topic_id=topic.id)
    row.content = validated.model_dump_json()
    row.schema_version = LESSON_SCHEMA_VERSION
    row.generated_at = datetime.utcnow()
    row.model_used = ai_service.MODEL
    row.reviewed = False
    row.reviewed_at = None
    if existing is None:
        db.add(row)

    db.commit()
    db.refresh(row)
    logger.info("Cache miss/refresh: generated lesson topic_id=%d", topic.id)
    return _lesson_row_to_dict(row)


def _generate_and_validate_lesson(topic: Topic) -> LessonSchema:
    def _generate():
        return ai_service.generate_lesson(
            topic.key_stage,
            topic.topic_name,
            topic.strand,
            year_group=topic.year_group,
            topic_id=topic.id,
        )

    raw = _generate()
    try:
        return LessonSchema.model_validate(raw)
    except ValidationError as exc:
        logger.error(
            "Lesson validation failed (attempt 1) topic_id=%d: %s", topic.id, exc
        )
        raw_retry = _generate()
        try:
            return LessonSchema.model_validate(raw_retry)
        except ValidationError as exc2:
            logger.error(
                "Lesson validation failed (attempt 2) topic_id=%d: %s", topic.id, exc2
            )
            raise ai_service.AIGenerationError(
                "Lesson content failed validation twice"
            ) from exc2


def _lesson_row_to_dict(row: LessonCache, stale: bool = False) -> dict:
    """Render a cached row, whichever schema version it was written under.

    Rows from before the teaching-sequence rewrite are still served — they
    contain real, usable content — flagged `outdated_format` so the UI can
    offer regeneration. Regenerating them automatically would spend credits
    across every topic already generated without anyone asking.
    """
    version = row.schema_version or 1
    result = {
        "topic_id": row.topic_id,
        "schema_version": version,
        "outdated_format": version < LESSON_SCHEMA_VERSION,
        "generated_at": row.generated_at,
        "model_used": row.model_used,
        "reviewed": row.reviewed,
        "reviewed_at": row.reviewed_at,
        "stale": stale,
    }

    if row.content:
        result.update(json.loads(row.content))
        return result

    # Schema version 1: four flat columns.
    result.update(
        {
            "lesson_notes": row.lesson_notes,
            "worked_examples": json.loads(row.worked_examples or "[]"),
            "key_vocabulary": json.loads(row.key_vocabulary or "[]"),
            "common_errors": json.loads(row.common_errors or "[]"),
        }
    )
    return result


def _cached_common_errors(db: Session, topic_id: int) -> Optional[list]:
    """The misconceptions from this topic's cached lesson, if there is one.

    Feeds question generation so distractors can be built from misconceptions
    the lesson actually identified, rather than arbitrary wrong answers.
    Returns None when no lesson exists yet — questions are still generated,
    just without the diagnostic targeting.
    """
    row = db.query(LessonCache).filter(LessonCache.topic_id == topic_id).first()
    if row is None:
        return None
    return _lesson_row_to_dict(row).get("common_errors") or None


def mark_lesson_reviewed(db: Session, topic_id: int) -> dict:
    """Sets reviewed=True/reviewed_at=now on the cached lesson row (CLAUDE.md
    Production Hardening — the `reviewed` workflow). Raises
    ContentNotCachedError if no lesson has been generated yet."""
    topic = _get_topic_or_raise(db, topic_id)
    row = db.query(LessonCache).filter(LessonCache.topic_id == topic.id).first()
    if row is None:
        raise ContentNotCachedError(f"No lesson has been generated for topic {topic_id} yet")

    row.reviewed = True
    row.reviewed_at = datetime.utcnow()
    db.commit()
    db.refresh(row)
    logger.info("Lesson marked reviewed topic_id=%d", topic.id)
    return _lesson_row_to_dict(row)


# --- Questions -----------------------------------------------------------


def get_questions(
    db: Session, topic_id: int, difficulty: str, force_refresh: bool = False
) -> list:
    if difficulty not in VALID_DIFFICULTIES:
        raise ValueError(
            f"Invalid difficulty '{difficulty}'. Must be one of "
            f"{sorted(VALID_DIFFICULTIES)}."
        )

    topic = _get_topic_or_raise(db, topic_id)
    existing = (
        db.query(QuestionCache)
        .filter(QuestionCache.topic_id == topic.id, QuestionCache.difficulty == difficulty)
        .first()
    )

    if not force_refresh and existing is not None:
        logger.info(
            "Cache hit: questions topic_id=%d difficulty=%s", topic.id, difficulty
        )
        return json.loads(existing.questions)

    if force_refresh:
        _log_regeneration(db, topic.id, f"question:{difficulty}")

    try:
        validated = _generate_and_validate_questions(
            topic, difficulty, _cached_common_errors(db, topic.id)
        )
    except ai_service.AIGenerationError:
        if existing is not None:
            logger.error(
                "Question generation failed for topic_id=%d difficulty=%s; "
                "serving stale cache",
                topic.id,
                difficulty,
            )
            return json.loads(existing.questions)
        logger.error(
            "Question generation failed for topic_id=%d difficulty=%s; no "
            "cached content to fall back to",
            topic.id,
            difficulty,
        )
        raise

    questions_json = json.dumps([q.model_dump() for q in validated.root])

    row = existing if existing is not None else QuestionCache(
        topic_id=topic.id, difficulty=difficulty
    )
    row.questions = questions_json
    row.generated_at = datetime.utcnow()
    row.model_used = ai_service.MODEL
    row.reviewed = False
    row.reviewed_at = None
    if existing is None:
        db.add(row)

    db.commit()
    db.refresh(row)
    logger.info(
        "Cache miss/refresh: generated questions topic_id=%d difficulty=%s",
        topic.id,
        difficulty,
    )
    return json.loads(row.questions)


def _question_status_to_dict(row: QuestionCache) -> dict:
    return {
        "topic_id": row.topic_id,
        "difficulty": row.difficulty,
        "generated_at": row.generated_at,
        "model_used": row.model_used,
        "reviewed": row.reviewed,
        "reviewed_at": row.reviewed_at,
    }


def get_questions_status(db: Session, topic_id: int, difficulty: str) -> Optional[dict]:
    """Read-only cache-row metadata (generated_at/model_used/reviewed) for
    one topic+tier, without ever triggering generation — used by the
    frontend to show the `reviewed` marker beside the question list.
    Returns None if nothing has been generated for this tier yet."""
    if difficulty not in VALID_DIFFICULTIES:
        raise ValueError(
            f"Invalid difficulty '{difficulty}'. Must be one of "
            f"{sorted(VALID_DIFFICULTIES)}."
        )
    topic = _get_topic_or_raise(db, topic_id)
    row = (
        db.query(QuestionCache)
        .filter(QuestionCache.topic_id == topic.id, QuestionCache.difficulty == difficulty)
        .first()
    )
    if row is None:
        return None
    return _question_status_to_dict(row)


def mark_questions_reviewed(db: Session, topic_id: int, difficulty: str) -> dict:
    """Sets reviewed=True/reviewed_at=now on the cached question-tier row.
    Raises ContentNotCachedError if no questions have been generated yet
    for this tier."""
    if difficulty not in VALID_DIFFICULTIES:
        raise ValueError(
            f"Invalid difficulty '{difficulty}'. Must be one of "
            f"{sorted(VALID_DIFFICULTIES)}."
        )
    topic = _get_topic_or_raise(db, topic_id)
    row = (
        db.query(QuestionCache)
        .filter(QuestionCache.topic_id == topic.id, QuestionCache.difficulty == difficulty)
        .first()
    )
    if row is None:
        raise ContentNotCachedError(
            f"No questions have been generated for topic {topic_id} difficulty {difficulty} yet"
        )

    row.reviewed = True
    row.reviewed_at = datetime.utcnow()
    db.commit()
    db.refresh(row)
    logger.info("Questions marked reviewed topic_id=%d difficulty=%s", topic.id, difficulty)
    return _question_status_to_dict(row)


def _validate_questions_or_none(raw) -> Optional[QuestionSetSchema]:
    try:
        validated = QuestionSetSchema.model_validate(raw)
    except ValidationError:
        return None
    if not validated.root:
        # An empty list passes schema validation trivially but is useless —
        # treated as a failure needing the same retry-then-raise handling
        # (CLAUDE.md Error Handling: "Empty question response from AI →
        # retry once, then return error").
        return None
    return validated


def _generate_and_validate_questions(
    topic: Topic, difficulty: str, common_errors: Optional[list] = None
) -> QuestionSetSchema:
    def _generate():
        return ai_service.generate_questions(
            topic.key_stage,
            topic.topic_name,
            difficulty,
            strand=topic.strand,
            year_group=topic.year_group,
            common_errors=common_errors,
            topic_id=topic.id,
        )

    raw = _generate()
    validated = _validate_questions_or_none(raw)
    if validated is not None:
        return validated

    logger.error(
        "Question generation returned invalid or empty content (attempt 1) "
        "topic_id=%d difficulty=%s",
        topic.id,
        difficulty,
    )
    raw_retry = _generate()
    validated_retry = _validate_questions_or_none(raw_retry)
    if validated_retry is not None:
        return validated_retry

    logger.error(
        "Question generation returned invalid or empty content (attempt 2) "
        "topic_id=%d difficulty=%s",
        topic.id,
        difficulty,
    )
    raise ai_service.AIGenerationError(
        "Question content was empty or failed validation twice"
    )
