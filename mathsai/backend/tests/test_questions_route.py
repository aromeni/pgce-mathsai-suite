"""Phase 3 — Questions router (/api/questions). cache_service is mocked
here for the same reason as test_lessons_route.py: these tests verify
routing/error-mapping, not generation behaviour."""

from unittest.mock import patch

import pytest

from models import Topic
from schemas import QuestionItem
from services import ai_service, cache_service

QUESTIONS_LIST = [
    {
        "question_number": 1,
        "type": "short_answer",
        "question_text": "Solve x^2 = 9",
        "options": None,
        "answer": "x = 3 or x = -3",
        "mark_scheme": "1 mark for each solution",
        "marks": 2,
    }
]


@pytest.fixture()
def topic(db_session) -> Topic:
    t = Topic(key_stage="KS4", strand="Algebra", topic_name="Quadratic Equations", edexcel_ref="A12")
    db_session.add(t)
    db_session.commit()
    db_session.refresh(t)
    return t


def test_get_questions_success(client, topic):
    with patch.object(cache_service, "get_questions", return_value=QUESTIONS_LIST):
        response = client.get(f"/api/questions/{topic.id}/Fluency")

    assert response.status_code == 200
    # Compared against the serialised schema rather than the raw input, so
    # adding an optional question field does not break this expectation.
    assert response.json() == [QuestionItem(**q).model_dump() for q in QUESTIONS_LIST]


def test_get_questions_invalid_difficulty_returns_422(client, topic):
    """No mocking needed — the DifficultyTier Literal type rejects this
    before the route body ever runs."""
    response = client.get(f"/api/questions/{topic.id}/NotATier")
    assert response.status_code == 422


def test_get_questions_topic_not_found_returns_404(client):
    with patch.object(
        cache_service, "get_questions", side_effect=cache_service.TopicNotFoundError("Topic 999 not found")
    ):
        response = client.get("/api/questions/999/Fluency")

    assert response.status_code == 404


def test_get_questions_generation_failure_returns_503(client, topic):
    with patch.object(
        cache_service, "get_questions", side_effect=ai_service.AIGenerationError("down")
    ):
        response = client.get(f"/api/questions/{topic.id}/Fluency")

    assert response.status_code == 503


def test_refresh_questions_calls_force_refresh(client, topic):
    with patch.object(cache_service, "get_questions", return_value=QUESTIONS_LIST) as mock_get:
        response = client.post(f"/api/questions/{topic.id}/Problem-solving/refresh")

    assert response.status_code == 200
    assert mock_get.call_args.kwargs.get("force_refresh") is True


def test_refresh_questions_invalid_difficulty_returns_422(client, topic):
    response = client.post(f"/api/questions/{topic.id}/NotATier/refresh")
    assert response.status_code == 422


# --- Phase 9: status + reviewed workflow -----------------------------------

STATUS_DICT = {
    "topic_id": 1,
    "difficulty": "Fluency",
    "generated_at": "2026-01-01T00:00:00",
    "model_used": ai_service.MODEL,
    "reviewed": False,
    "reviewed_at": None,
}


def test_get_questions_status_returns_metadata(client, topic):
    with patch.object(cache_service, "get_questions_status", return_value={**STATUS_DICT, "topic_id": topic.id}):
        response = client.get(f"/api/questions/{topic.id}/Fluency/status")

    assert response.status_code == 200
    assert response.json()["reviewed"] is False


def test_get_questions_status_returns_null_when_not_cached(client, topic):
    with patch.object(cache_service, "get_questions_status", return_value=None):
        response = client.get(f"/api/questions/{topic.id}/Fluency/status")

    assert response.status_code == 200
    assert response.json() is None


def test_get_questions_status_topic_not_found_returns_404(client):
    with patch.object(
        cache_service, "get_questions_status", side_effect=cache_service.TopicNotFoundError("nope")
    ):
        response = client.get("/api/questions/999/Fluency/status")

    assert response.status_code == 404


def test_mark_questions_reviewed_success(client, topic):
    reviewed = {**STATUS_DICT, "topic_id": topic.id, "reviewed": True, "reviewed_at": "2026-01-02T00:00:00"}
    with patch.object(cache_service, "mark_questions_reviewed", return_value=reviewed):
        response = client.post(f"/api/questions/{topic.id}/Fluency/review")

    assert response.status_code == 200
    assert response.json()["reviewed"] is True


def test_mark_questions_reviewed_not_cached_returns_404(client, topic):
    with patch.object(
        cache_service, "mark_questions_reviewed", side_effect=cache_service.ContentNotCachedError("nothing yet")
    ):
        response = client.post(f"/api/questions/{topic.id}/Fluency/review")

    assert response.status_code == 404


def test_mark_questions_reviewed_topic_not_found_returns_404(client):
    with patch.object(
        cache_service, "mark_questions_reviewed", side_effect=cache_service.TopicNotFoundError("nope")
    ):
        response = client.post("/api/questions/999/Fluency/review")

    assert response.status_code == 404
