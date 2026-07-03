"""Phase 3 — Lessons router (/api/lessons). cache_service is mocked here —
its own generation/caching behaviour is already covered by
test_cache_service.py. These tests verify the router's error mapping:
404 for missing topics, 503 for generation failures."""

from unittest.mock import patch

import pytest

from models import Topic
from services import ai_service, cache_service

LESSON_DICT = {
    "topic_id": 1,
    "lesson_notes": "# Quadratic Equations",
    "worked_examples": [],
    "key_vocabulary": [],
    "common_errors": [],
    "generated_at": "2026-01-01T00:00:00",
    "model_used": ai_service.MODEL,
    "reviewed": False,
    "reviewed_at": None,
    "stale": False,
}


@pytest.fixture()
def topic(db_session) -> Topic:
    t = Topic(key_stage="KS4", strand="Algebra", topic_name="Quadratic Equations", edexcel_ref="A12")
    db_session.add(t)
    db_session.commit()
    db_session.refresh(t)
    return t


def test_get_lesson_success(client, topic):
    with patch.object(cache_service, "get_lesson", return_value={**LESSON_DICT, "topic_id": topic.id}):
        response = client.get(f"/api/lessons/{topic.id}")

    assert response.status_code == 200
    assert response.json()["lesson_notes"] == "# Quadratic Equations"


def test_get_lesson_topic_not_found_returns_404(client):
    with patch.object(
        cache_service, "get_lesson", side_effect=cache_service.TopicNotFoundError("Topic 999 not found")
    ):
        response = client.get("/api/lessons/999")

    assert response.status_code == 404


def test_get_lesson_generation_failure_returns_503(client, topic):
    with patch.object(
        cache_service,
        "get_lesson",
        side_effect=ai_service.AIGenerationError("Generation temporarily unavailable — please try again shortly."),
    ):
        response = client.get(f"/api/lessons/{topic.id}")

    assert response.status_code == 503


def test_refresh_lesson_calls_force_refresh(client, topic):
    with patch.object(
        cache_service, "get_lesson", return_value={**LESSON_DICT, "topic_id": topic.id}
    ) as mock_get:
        response = client.post(f"/api/lessons/{topic.id}/refresh")

    assert response.status_code == 200
    assert mock_get.call_args.kwargs.get("force_refresh") is True


def test_refresh_lesson_generation_failure_returns_503(client, topic):
    with patch.object(
        cache_service, "get_lesson", side_effect=ai_service.AIGenerationError("down")
    ):
        response = client.post(f"/api/lessons/{topic.id}/refresh")

    assert response.status_code == 503
