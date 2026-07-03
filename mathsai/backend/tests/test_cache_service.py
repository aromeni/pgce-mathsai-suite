"""Phase 2 — cache_service.py. ai_service is always mocked; no real API
calls. Covers the exact flow specified in CLAUDE.md's Caching Logic:
cache hit, cache miss, force-refresh, validation-failure-retry, and
serving a stale row when regeneration fails."""

import json
from unittest.mock import patch

import pytest

from models import LessonCache, QuestionCache, Topic
from services import ai_service, cache_service

VALID_LESSON_RAW = {
    "lesson_notes": "# Quadratic Equations\n\nLearning objectives...",
    "worked_examples": [
        {
            "title": "Example 1 — factorising",
            "problem": "x^2 - 5x + 6 = 0",
            "solution": "(x-2)(x-3) = 0, so x = 2 or x = 3",
            "teaching_note": "Check the factor pair multiplies to +6 and sums to -5",
        }
    ],
    "key_vocabulary": [{"term": "quadratic", "definition": "a degree-2 polynomial equation"}],
    "common_errors": [{"error": "sign slip when factorising", "correction": "recheck the factor pair"}],
}

INVALID_LESSON_RAW = {"lesson_notes": "missing every other required field"}

VALID_QUESTIONS_RAW = [
    {
        "question_number": 1,
        "type": "short_answer",
        "question_text": "Solve x^2 = 9",
        "answer": "x = 3 or x = -3",
        "mark_scheme": "1 mark for each solution",
        "marks": 2,
    }
]

# cache_service round-trips every question through QuestionItem, which
# always emits "options" (None when the AI response didn't include one) —
# so the stored/returned shape has one more key than the raw AI response.
EXPECTED_QUESTIONS_STORED = [{**VALID_QUESTIONS_RAW[0], "options": None}]

INVALID_QUESTIONS_RAW = [{"question_number": 1}]


@pytest.fixture()
def topic(db_session) -> Topic:
    t = Topic(
        key_stage="KS4",
        strand="Algebra",
        topic_name="Quadratic Equations",
        edexcel_ref="A12",
        difficulty_band=None,
    )
    db_session.add(t)
    db_session.commit()
    db_session.refresh(t)
    return t


# --- Lessons -------------------------------------------------------------


def test_get_lesson_cache_miss_generates_and_stores(db_session, topic):
    with patch.object(ai_service, "generate_lesson", return_value=VALID_LESSON_RAW) as mock_gen:
        result = cache_service.get_lesson(db_session, topic.id)

    assert mock_gen.call_count == 1
    assert result["lesson_notes"] == VALID_LESSON_RAW["lesson_notes"]
    assert result["stale"] is False

    row = db_session.query(LessonCache).filter_by(topic_id=topic.id).one()
    assert json.loads(row.worked_examples) == VALID_LESSON_RAW["worked_examples"]
    assert row.reviewed is False
    assert row.model_used == ai_service.MODEL


def test_get_lesson_cache_hit_does_not_call_ai_again(db_session, topic):
    with patch.object(ai_service, "generate_lesson", return_value=VALID_LESSON_RAW) as mock_gen:
        cache_service.get_lesson(db_session, topic.id)
        cache_service.get_lesson(db_session, topic.id)

    assert mock_gen.call_count == 1


def test_get_lesson_force_refresh_regenerates(db_session, topic):
    with patch.object(ai_service, "generate_lesson", return_value=VALID_LESSON_RAW) as mock_gen:
        cache_service.get_lesson(db_session, topic.id)
        cache_service.get_lesson(db_session, topic.id, force_refresh=True)

    assert mock_gen.call_count == 2
    assert db_session.query(LessonCache).filter_by(topic_id=topic.id).count() == 1


def test_get_lesson_retries_once_on_validation_failure_then_succeeds(db_session, topic):
    with patch.object(
        ai_service, "generate_lesson", side_effect=[INVALID_LESSON_RAW, VALID_LESSON_RAW]
    ) as mock_gen:
        result = cache_service.get_lesson(db_session, topic.id)

    assert mock_gen.call_count == 2
    assert result["lesson_notes"] == VALID_LESSON_RAW["lesson_notes"]


def test_get_lesson_raises_after_validation_fails_twice_and_stores_nothing(db_session, topic):
    with patch.object(
        ai_service, "generate_lesson", side_effect=[INVALID_LESSON_RAW, INVALID_LESSON_RAW]
    ) as mock_gen:
        with pytest.raises(ai_service.AIGenerationError):
            cache_service.get_lesson(db_session, topic.id)

    assert mock_gen.call_count == 2
    assert db_session.query(LessonCache).filter_by(topic_id=topic.id).count() == 0


def test_get_lesson_serves_stale_cache_when_refresh_fails(db_session, topic):
    with patch.object(ai_service, "generate_lesson", return_value=VALID_LESSON_RAW):
        cache_service.get_lesson(db_session, topic.id)

    with patch.object(
        ai_service, "generate_lesson", side_effect=ai_service.AIGenerationError("down")
    ):
        result = cache_service.get_lesson(db_session, topic.id, force_refresh=True)

    assert result["stale"] is True
    assert result["lesson_notes"] == VALID_LESSON_RAW["lesson_notes"]


def test_get_lesson_unknown_topic_raises(db_session):
    with pytest.raises(cache_service.TopicNotFoundError):
        cache_service.get_lesson(db_session, topic_id=9999)


# --- Questions -------------------------------------------------------------


def test_get_questions_cache_miss_generates_and_stores(db_session, topic):
    with patch.object(ai_service, "generate_questions", return_value=VALID_QUESTIONS_RAW) as mock_gen:
        result = cache_service.get_questions(db_session, topic.id, "Foundation")

    assert mock_gen.call_count == 1
    assert result == EXPECTED_QUESTIONS_STORED

    row = db_session.query(QuestionCache).filter_by(topic_id=topic.id, difficulty="Foundation").one()
    assert row.reviewed is False


def test_get_questions_cache_hit_does_not_call_ai_again(db_session, topic):
    with patch.object(ai_service, "generate_questions", return_value=VALID_QUESTIONS_RAW) as mock_gen:
        cache_service.get_questions(db_session, topic.id, "Foundation")
        cache_service.get_questions(db_session, topic.id, "Foundation")

    assert mock_gen.call_count == 1


def test_get_questions_different_tiers_cache_independently(db_session, topic):
    with patch.object(ai_service, "generate_questions", return_value=VALID_QUESTIONS_RAW) as mock_gen:
        cache_service.get_questions(db_session, topic.id, "Foundation")
        cache_service.get_questions(db_session, topic.id, "Extending")

    assert mock_gen.call_count == 2
    assert db_session.query(QuestionCache).filter_by(topic_id=topic.id).count() == 2


def test_get_questions_invalid_difficulty_raises_value_error(db_session, topic):
    with pytest.raises(ValueError):
        cache_service.get_questions(db_session, topic.id, "NotATier")


def test_get_questions_retries_once_on_validation_failure_then_succeeds(db_session, topic):
    with patch.object(
        ai_service, "generate_questions", side_effect=[INVALID_QUESTIONS_RAW, VALID_QUESTIONS_RAW]
    ) as mock_gen:
        result = cache_service.get_questions(db_session, topic.id, "Foundation")

    assert mock_gen.call_count == 2
    assert result == EXPECTED_QUESTIONS_STORED


def test_get_questions_serves_stale_cache_when_refresh_fails(db_session, topic):
    with patch.object(ai_service, "generate_questions", return_value=VALID_QUESTIONS_RAW):
        cache_service.get_questions(db_session, topic.id, "Foundation")

    with patch.object(
        ai_service, "generate_questions", side_effect=ai_service.AIGenerationError("down")
    ):
        result = cache_service.get_questions(db_session, topic.id, "Foundation", force_refresh=True)

    assert result == EXPECTED_QUESTIONS_STORED


def test_get_questions_empty_response_retries_then_succeeds(db_session, topic):
    """CLAUDE.md Error Handling: 'Empty question response from AI -> retry
    once, then return error.' An empty list passes schema validation
    trivially, so it needs its own check distinct from validation failure."""
    with patch.object(
        ai_service, "generate_questions", side_effect=[[], VALID_QUESTIONS_RAW]
    ) as mock_gen:
        result = cache_service.get_questions(db_session, topic.id, "Foundation")

    assert mock_gen.call_count == 2
    assert result == EXPECTED_QUESTIONS_STORED


def test_get_questions_empty_response_twice_raises_and_stores_nothing(db_session, topic):
    with patch.object(ai_service, "generate_questions", side_effect=[[], []]) as mock_gen:
        with pytest.raises(ai_service.AIGenerationError):
            cache_service.get_questions(db_session, topic.id, "Foundation")

    assert mock_gen.call_count == 2
    assert db_session.query(QuestionCache).filter_by(topic_id=topic.id).count() == 0
