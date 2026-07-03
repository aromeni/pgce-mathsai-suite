"""Phase 3 — Questions router (/api/questions). cache_service is mocked
here for the same reason as test_lessons_route.py: these tests verify
routing/error-mapping, not generation behaviour."""

from unittest.mock import patch

import pytest

from models import Topic
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
        response = client.get(f"/api/questions/{topic.id}/Foundation")

    assert response.status_code == 200
    assert response.json() == QUESTIONS_LIST


def test_get_questions_invalid_difficulty_returns_422(client, topic):
    """No mocking needed — the DifficultyTier Literal type rejects this
    before the route body ever runs."""
    response = client.get(f"/api/questions/{topic.id}/NotATier")
    assert response.status_code == 422


def test_get_questions_topic_not_found_returns_404(client):
    with patch.object(
        cache_service, "get_questions", side_effect=cache_service.TopicNotFoundError("Topic 999 not found")
    ):
        response = client.get("/api/questions/999/Foundation")

    assert response.status_code == 404


def test_get_questions_generation_failure_returns_503(client, topic):
    with patch.object(
        cache_service, "get_questions", side_effect=ai_service.AIGenerationError("down")
    ):
        response = client.get(f"/api/questions/{topic.id}/Foundation")

    assert response.status_code == 503


def test_refresh_questions_calls_force_refresh(client, topic):
    with patch.object(cache_service, "get_questions", return_value=QUESTIONS_LIST) as mock_get:
        response = client.post(f"/api/questions/{topic.id}/Extending/refresh")

    assert response.status_code == 200
    assert mock_get.call_args.kwargs.get("force_refresh") is True


def test_refresh_questions_invalid_difficulty_returns_422(client, topic):
    response = client.post(f"/api/questions/{topic.id}/NotATier/refresh")
    assert response.status_code == 422
