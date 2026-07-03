"""Phase 7 — Export router (/api/export). cache_service is mocked here —
its own generation/caching behaviour is already covered by
test_cache_service.py. These tests verify: PDF bytes actually come back
with the right content-type, 404 for missing topics, 503 for generation
failures, and that special characters (e.g. "<"/">" from inequalities)
are HTML-escaped rather than breaking the renderer."""

from unittest.mock import patch

import pytest

from models import Topic
from services import ai_service, cache_service

LESSON_DICT = {
    "topic_id": 1,
    "lesson_notes": "# Quadratics\n\nSolve for x < 5 and x > -2.",
    "worked_examples": [
        {
            "title": "Example 1 <tricky>",
            "problem": "x^2 - 4 = 0",
            "solution": "x = 2 or x = -2",
            "teaching_note": "Watch for the & sign in working.",
        }
    ],
    "key_vocabulary": [{"term": "Discriminant", "definition": "b^2 - 4ac"}],
    "common_errors": [{"error": "Forgetting +/-", "correction": "Always write both roots"}],
    "generated_at": "2026-01-01T00:00:00",
    "model_used": ai_service.MODEL,
    "reviewed": False,
    "reviewed_at": None,
    "stale": False,
}

QUESTIONS_BY_TIER = {
    "Foundation": [
        {
            "question_number": 1,
            "type": "short_answer",
            "question_text": "Solve x < 3",
            "options": None,
            "answer": "x < 3",
            "mark_scheme": "1 mark",
            "marks": 1,
        }
    ],
    "Developing": [
        {
            "question_number": 1,
            "type": "multiple_choice",
            "question_text": "Which satisfies x > 2?",
            "options": ["A) 1", "B) 3"],
            "answer": "B",
            "mark_scheme": "1 mark",
            "marks": 1,
        }
    ],
    "Extending": [
        {
            "question_number": 1,
            "type": "exam_style",
            "question_text": "Prove x^2 >= 0",
            "options": None,
            "answer": "See working",
            "mark_scheme": "2 marks",
            "marks": 2,
        }
    ],
}


@pytest.fixture()
def topic(db_session) -> Topic:
    t = Topic(key_stage="KS4", strand="Algebra", topic_name="Quadratic Equations", edexcel_ref="A12")
    db_session.add(t)
    db_session.commit()
    db_session.refresh(t)
    return t


# --- Lesson export -------------------------------------------------------


def test_export_lesson_pdf_success(client, topic):
    with patch.object(
        cache_service, "get_lesson", return_value={**LESSON_DICT, "topic_id": topic.id}
    ):
        response = client.get(f"/api/export/lesson/{topic.id}/pdf")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert "attachment" in response.headers["content-disposition"]
    assert response.content.startswith(b"%PDF")


def test_export_lesson_pdf_topic_not_found_returns_404(client):
    response = client.get("/api/export/lesson/999/pdf")
    assert response.status_code == 404


def test_export_lesson_pdf_generation_failure_returns_503(client, topic):
    with patch.object(
        cache_service,
        "get_lesson",
        side_effect=ai_service.AIGenerationError("Generation temporarily unavailable — please try again shortly."),
    ):
        response = client.get(f"/api/export/lesson/{topic.id}/pdf")

    assert response.status_code == 503


# --- Questions export -----------------------------------------------------


def _get_questions_side_effect(db, topic_id, difficulty, force_refresh=False):
    return QUESTIONS_BY_TIER[difficulty]


def test_export_questions_pdf_success(client, topic):
    with patch.object(cache_service, "get_questions", side_effect=_get_questions_side_effect):
        response = client.get(f"/api/export/questions/{topic.id}/pdf")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")


def test_export_questions_pdf_topic_not_found_returns_404(client):
    response = client.get("/api/export/questions/999/pdf")
    assert response.status_code == 404


def test_export_questions_pdf_generation_failure_returns_503(client, topic):
    with patch.object(
        cache_service, "get_questions", side_effect=ai_service.AIGenerationError("down")
    ):
        response = client.get(f"/api/export/questions/{topic.id}/pdf")

    assert response.status_code == 503
