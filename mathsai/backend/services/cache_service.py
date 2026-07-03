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

from models import LessonCache, QuestionCache, Topic
from schemas import LessonSchema, QuestionSetSchema
from services import ai_service

logger = logging.getLogger("mathsai")

VALID_DIFFICULTIES = {"Foundation", "Developing", "Extending"}


class TopicNotFoundError(Exception):
    pass


def _get_topic_or_raise(db: Session, topic_id: int) -> Topic:
    topic = db.query(Topic).filter(Topic.id == topic_id).first()
    if topic is None:
        raise TopicNotFoundError(f"Topic {topic_id} not found")
    return topic


# --- Lessons -----------------------------------------------------------


def get_lesson(db: Session, topic_id: int, force_refresh: bool = False) -> dict:
    topic = _get_topic_or_raise(db, topic_id)
    existing = db.query(LessonCache).filter(LessonCache.topic_id == topic.id).first()

    if not force_refresh and existing is not None:
        logger.info("Cache hit: lesson topic_id=%d", topic.id)
        return _lesson_row_to_dict(existing)

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
        raise

    row = existing if existing is not None else LessonCache(topic_id=topic.id)
    row.lesson_notes = validated.lesson_notes
    row.worked_examples = json.dumps([e.model_dump() for e in validated.worked_examples])
    row.key_vocabulary = json.dumps([v.model_dump() for v in validated.key_vocabulary])
    row.common_errors = json.dumps([c.model_dump() for c in validated.common_errors])
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
    raw = ai_service.generate_lesson(topic.key_stage, topic.topic_name, topic.edexcel_ref)
    try:
        return LessonSchema.model_validate(raw)
    except ValidationError as exc:
        logger.error(
            "Lesson validation failed (attempt 1) topic_id=%d: %s", topic.id, exc
        )
        raw_retry = ai_service.generate_lesson(
            topic.key_stage, topic.topic_name, topic.edexcel_ref
        )
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
    return {
        "topic_id": row.topic_id,
        "lesson_notes": row.lesson_notes,
        "worked_examples": json.loads(row.worked_examples),
        "key_vocabulary": json.loads(row.key_vocabulary),
        "common_errors": json.loads(row.common_errors),
        "generated_at": row.generated_at,
        "model_used": row.model_used,
        "reviewed": row.reviewed,
        "reviewed_at": row.reviewed_at,
        "stale": stale,
    }


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

    try:
        validated = _generate_and_validate_questions(topic, difficulty)
    except ai_service.AIGenerationError:
        if existing is not None:
            logger.error(
                "Question generation failed for topic_id=%d difficulty=%s; "
                "serving stale cache",
                topic.id,
                difficulty,
            )
            return json.loads(existing.questions)
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


def _generate_and_validate_questions(topic: Topic, difficulty: str) -> QuestionSetSchema:
    raw = ai_service.generate_questions(topic.key_stage, topic.topic_name, difficulty)
    validated = _validate_questions_or_none(raw)
    if validated is not None:
        return validated

    logger.error(
        "Question generation returned invalid or empty content (attempt 1) "
        "topic_id=%d difficulty=%s",
        topic.id,
        difficulty,
    )
    raw_retry = ai_service.generate_questions(topic.key_stage, topic.topic_name, difficulty)
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
