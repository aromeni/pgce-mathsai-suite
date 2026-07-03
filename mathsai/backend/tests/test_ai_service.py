"""Phase 2 — ai_service.py. The Anthropic client is always mocked; these
tests never call the real API."""

import json
from unittest.mock import MagicMock, patch

import httpx
import pytest
from anthropic import APITimeoutError, RateLimitError

from services import ai_service

LESSON_JSON = json.dumps(
    {
        "lesson_notes": "# Quadratic Equations\n\nLearning objectives...",
        "worked_examples": [
            {
                "title": "Example 1 — factorising",
                "problem": "x^2 - 5x + 6 = 0",
                "solution": "(x-2)(x-3)=0, so x=2 or x=3",
                "teaching_note": "Emphasise sign checking",
            }
        ],
        "key_vocabulary": [{"term": "quadratic", "definition": "a degree-2 polynomial equation"}],
        "common_errors": [{"error": "sign error when factorising", "correction": "check signs multiply to give constant term"}],
    }
)

QUESTIONS_JSON = json.dumps(
    [
        {
            "question_number": 1,
            "type": "short_answer",
            "question_text": "Solve x^2 = 9",
            "answer": "x = 3 or x = -3",
            "mark_scheme": "1 mark for each solution",
            "marks": 2,
        }
    ]
)


def _text_response(text: str) -> MagicMock:
    block = MagicMock()
    block.type = "text"
    block.text = text
    response = MagicMock()
    response.content = [block]
    return response


def _rate_limit_error() -> RateLimitError:
    request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    response = httpx.Response(status_code=429, request=request)
    return RateLimitError("rate limited", response=response, body=None)


def _timeout_error() -> APITimeoutError:
    request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    return APITimeoutError(request=request)


def _mock_client(*script) -> MagicMock:
    """`script` is a sequence of exceptions and/or raw text bodies, consumed
    in order across successive `.create()` calls."""
    queue = list(script)

    def side_effect(*args, **kwargs):
        item = queue.pop(0)
        if isinstance(item, Exception):
            raise item
        return _text_response(item)

    client = MagicMock()
    client.with_options.return_value.messages.create.side_effect = side_effect
    return client


def test_generate_lesson_success_first_try():
    client = _mock_client(LESSON_JSON)
    with patch.object(ai_service, "_get_client", return_value=client):
        result = ai_service.generate_lesson("KS4", "Quadratic Equations", "A12")

    assert result["lesson_notes"].startswith("# Quadratic Equations")
    assert len(result["worked_examples"]) == 1
    assert client.with_options.return_value.messages.create.call_count == 1


def test_generate_lesson_retries_once_on_rate_limit_then_succeeds():
    client = _mock_client(_rate_limit_error(), LESSON_JSON)
    with patch.object(ai_service, "_get_client", return_value=client), patch.object(
        ai_service.time, "sleep", return_value=None
    ):
        result = ai_service.generate_lesson("KS4", "Quadratic Equations", "A12")

    assert result["lesson_notes"].startswith("# Quadratic Equations")
    assert client.with_options.return_value.messages.create.call_count == 2


def test_generate_lesson_retries_once_on_timeout_then_succeeds():
    client = _mock_client(_timeout_error(), LESSON_JSON)
    with patch.object(ai_service, "_get_client", return_value=client), patch.object(
        ai_service.time, "sleep", return_value=None
    ):
        result = ai_service.generate_lesson("KS4", "Quadratic Equations", "A12")

    assert result["lesson_notes"].startswith("# Quadratic Equations")


def test_generate_lesson_raises_after_two_failures():
    client = _mock_client(_rate_limit_error(), _rate_limit_error())
    with patch.object(ai_service, "_get_client", return_value=client), patch.object(
        ai_service.time, "sleep", return_value=None
    ):
        with pytest.raises(ai_service.AIGenerationError):
            ai_service.generate_lesson("KS4", "Quadratic Equations", "A12")

    # not more than one retry — a teacher should see a fast, clear failure
    assert client.with_options.return_value.messages.create.call_count == 2


def test_generate_lesson_invalid_json_raises_ai_generation_error():
    client = _mock_client("this is not json {")
    with patch.object(ai_service, "_get_client", return_value=client):
        with pytest.raises(ai_service.AIGenerationError):
            ai_service.generate_lesson("KS4", "Quadratic Equations", "A12")


def test_generate_lesson_strips_accidental_markdown_fences():
    fenced = "```json\n" + LESSON_JSON + "\n```"
    client = _mock_client(fenced)
    with patch.object(ai_service, "_get_client", return_value=client):
        result = ai_service.generate_lesson("KS4", "Quadratic Equations", "A12")
    assert result["lesson_notes"].startswith("# Quadratic Equations")


def test_generate_questions_success():
    client = _mock_client(QUESTIONS_JSON)
    with patch.object(ai_service, "_get_client", return_value=client):
        result = ai_service.generate_questions("KS4", "Quadratic Equations", "Foundation")

    assert isinstance(result, list)
    assert result[0]["question_number"] == 1


def test_generate_questions_invalid_difficulty_raises_value_error():
    with pytest.raises(ValueError):
        ai_service.generate_questions("KS4", "Quadratic Equations", "Impossible")
