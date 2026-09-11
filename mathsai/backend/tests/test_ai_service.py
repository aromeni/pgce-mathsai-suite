"""Phase 2 — ai_service.py. The Anthropic client is always mocked; these
tests never call the real API."""

import json
from unittest.mock import MagicMock, patch

import httpx
import pytest
from anthropic import APITimeoutError, RateLimitError

from services import ai_service

from lesson_fixtures import PART_MARKERS, VALID_LESSON_RAW

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
    in order across successive `.stream()` calls.

    ai_service streams and calls get_final_message(), so the mock stands in
    for the context manager rather than a plain return value.
    """
    queue = list(script)

    def side_effect(*args, **kwargs):
        item = queue.pop(0)
        if isinstance(item, Exception):
            raise item
        stream_ctx = MagicMock()
        stream_ctx.__enter__.return_value.get_final_message.return_value = (
            _text_response(item)
        )
        return stream_ctx

    client = MagicMock()
    client.with_options.return_value.messages.stream.side_effect = side_effect
    return client


def _mock_lesson_client(fail_parts: int = 0, always_fail: str = "") -> MagicMock:
    """Client mock for whole-lesson generation.

    generate_lesson fires three prompts concurrently, so responses cannot be
    scripted by position — the arrival order is not deterministic. This mock
    inspects the prompt it was handed and answers with the matching fragment.
    `fail_parts` raises a rate-limit error on the first N calls, to exercise
    the per-call retry. `always_fail` is a marker phrase whose part fails on
    every attempt — needed to test one part exhausting its retry, since
    scattering N failures across three concurrent parts would just be
    absorbed by three separate retries.
    """
    state = {"failures": fail_parts}

    def side_effect(*args, **kwargs):
        prompt = kwargs["messages"][0]["content"]
        if always_fail and always_fail in prompt:
            raise _rate_limit_error()
        if state["failures"] > 0:
            state["failures"] -= 1
            raise _rate_limit_error()
        for marker, fragment in PART_MARKERS.items():
            if marker in prompt:
                stream_ctx = MagicMock()
                stream_ctx.__enter__.return_value.get_final_message.return_value = (
                    _text_response(json.dumps(fragment))
                )
                return stream_ctx
        raise AssertionError(f"prompt matched no known lesson part: {prompt[:80]!r}")

    client = MagicMock()
    client.with_options.return_value.messages.stream.side_effect = side_effect
    return client


def test_generate_lesson_merges_all_three_fragments():
    """The three concurrent calls must all land in one merged lesson."""
    client = _mock_lesson_client()
    with patch.object(ai_service, "_get_client", return_value=client):
        result = ai_service.generate_lesson(
            "KS3", "Solving linear equations", "Algebra", year_group=8
        )

    for key in VALID_LESSON_RAW:
        assert key in result, f"{key} missing from merged lesson"
    assert result["i_do"][0]["steps"][0]["narration"]
    assert result["adaptive_teaching"]["language_support"]["false_friends"]
    assert client.with_options.return_value.messages.stream.call_count == 3


def test_generate_lesson_each_part_retries_once_on_rate_limit():
    # One failure, absorbed by that part's own retry: 3 parts + 1 retry.
    client = _mock_lesson_client(fail_parts=1)
    with patch.object(ai_service, "_get_client", return_value=client), patch.object(
        ai_service.time, "sleep", return_value=None
    ):
        result = ai_service.generate_lesson(
            "KS3", "Solving linear equations", "Algebra", year_group=8
        )

    assert "topic_introduction" in result
    assert client.with_options.return_value.messages.stream.call_count == 4


def test_generate_lesson_raises_when_a_part_fails_twice():
    """A lesson missing its adaptive teaching or starter is not a lesson this
    system should cache and present as complete — one part failing fails the
    whole generation."""
    client = _mock_lesson_client(always_fail="Produce the adaptive teaching plan")
    with patch.object(ai_service, "_get_client", return_value=client), patch.object(
        ai_service.time, "sleep", return_value=None
    ):
        with pytest.raises(ai_service.AIGenerationError):
            ai_service.generate_lesson(
                "KS3", "Solving linear equations", "Algebra", year_group=8
            )


def test_generate_lesson_invalid_json_raises_ai_generation_error():
    client = _mock_client("this is not json {", "also not json", "nor this")
    with patch.object(ai_service, "_get_client", return_value=client):
        with pytest.raises(ai_service.AIGenerationError):
            ai_service.generate_lesson(
                "KS3", "Solving linear equations", "Algebra", year_group=8
            )


def test_generate_lesson_strips_accidental_markdown_fences():
    fenced = "```json\n" + json.dumps(VALID_LESSON_RAW) + "\n```"
    client = _mock_client(fenced, fenced, fenced)
    with patch.object(ai_service, "_get_client", return_value=client):
        result = ai_service.generate_lesson(
            "KS3", "Solving linear equations", "Algebra", year_group=8
        )
    assert "topic_introduction" in result


def test_lesson_prompts_carry_the_year_group():
    """KS3 spans three years; the pitch depends on this reaching the prompt."""
    captured = []

    def capture(*args, **kwargs):
        captured.append(kwargs["messages"][0]["content"])
        stream_ctx = MagicMock()
        stream_ctx.__enter__.return_value.get_final_message.return_value = (
            _text_response(json.dumps({}))
        )
        return stream_ctx

    client = MagicMock()
    client.with_options.return_value.messages.stream.side_effect = capture
    with patch.object(ai_service, "_get_client", return_value=client):
        ai_service.generate_lesson("KS3", "Fractions", "Number", year_group=7)

    assert len(captured) == 3
    assert all("Year 7" in prompt for prompt in captured)


def test_generate_questions_success():
    client = _mock_client(QUESTIONS_JSON)
    with patch.object(ai_service, "_get_client", return_value=client):
        result = ai_service.generate_questions("KS4", "Quadratic Equations", "Fluency")

    assert isinstance(result, list)
    assert result[0]["question_number"] == 1


def test_generate_questions_invalid_difficulty_raises_value_error():
    with pytest.raises(ValueError):
        ai_service.generate_questions("KS4", "Quadratic Equations", "Impossible")
