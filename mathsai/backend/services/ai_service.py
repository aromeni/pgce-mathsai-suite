"""All Anthropic API calls — single source of truth (CLAUDE.md AI Service Design).

No other module should call the Anthropic SDK directly. Every call gets a
timeout and one retry with a short backoff on timeout/429/5xx, per
CLAUDE.md Production Hardening — Resilience.
"""

import json
import logging
import time
from typing import Any, Optional

from anthropic import Anthropic, APIStatusError, APITimeoutError, RateLimitError

logger = logging.getLogger("mathsai")

MODEL = "claude-sonnet-5"

# CLAUDE.md proposed 30s as "reasonable for one generation". Measured against
# the real workload it is not: a KS4 lesson (e.g. Circle theorems) returns
# ~4,100 output tokens and takes ~40s end to end at ~100 tok/s, so every
# generation timed out, retried, timed out again, and surfaced a 503 after
# ~62s of waiting — while still being billed for both discarded completions,
# since the model had generated them in full before the client hung up.
# 120s clears the worst case (MAX_TOKENS at the observed throughput ≈ 77s)
# with headroom.
REQUEST_TIMEOUT_SECONDS = 120.0
RETRY_BACKOFF_SECONDS = 2.0
MAX_TOKENS = 8000

_client: Optional[Anthropic] = None


def _get_client() -> Anthropic:
    global _client
    if _client is None:
        _client = Anthropic()
    return _client


class AIGenerationError(Exception):
    """Raised when generation fails after the internal retry, or the
    response cannot be parsed as JSON. Callers (cache_service) decide
    whether to serve a stale cached row or propagate as a 503."""


SYSTEM_PROMPT = (
    "You are an experienced secondary mathematics teacher with deep expertise "
    "in the Edexcel KS3 and KS4 curriculum. You write clear, pedagogically "
    "sound lesson content for a trainee teacher to use directly in the "
    "classroom. Your explanations are precise, your examples are well-chosen, "
    "and your language is appropriate for secondary school pupils in England. "
    "You always follow Edexcel specification language and notation."
)

LESSON_USER_PROMPT_TEMPLATE = """\
Generate a complete lesson package for the following mathematics topic:

Key Stage: {key_stage}
Topic: {topic_name}
Edexcel Reference: {edexcel_ref}

Return your response as a valid JSON object with exactly this structure:

{{
  "lesson_notes": "Full markdown lesson notes including: learning objectives, key concept explanation, step-by-step method, at least two fully worked examples with commentary",
  "worked_examples": [
    {{
      "title": "Example 1 — [description]",
      "problem": "...",
      "solution": "Step-by-step solution with working shown",
      "teaching_note": "What the teacher should draw attention to"
    }}
  ],
  "key_vocabulary": [
    {{ "term": "...", "definition": "..." }}
  ],
  "common_errors": [
    {{ "error": "...", "correction": "..." }}
  ]
}}

Return only valid JSON. No preamble, no markdown fences.
"""

TIER_DEFINITIONS = {
    "Foundation": "straightforward single-step questions testing basic recall and application",
    "Developing": "two or three step questions requiring method selection",
    "Extending": "multi-step, exam-style questions requiring reasoning, proof, or problem-solving",
}

QUESTIONS_USER_PROMPT_TEMPLATE = """\
Generate 10 mathematics questions for the following:

Key Stage: {key_stage}
Topic: {topic_name}
Difficulty tier: {difficulty}
Tier definition: {tier_definition}
Exam board: Edexcel

Include a mix of question types. The "type" field for each question must be
exactly one of these four strings (verbatim, no variations): "short_answer",
"multiple_choice", "show_working", "exam_style".

Return a valid JSON array with exactly this structure per question:

[
  {{
    "question_number": 1,
    "type": "short_answer",
    "question_text": "...",
    "answer": "...",
    "mark_scheme": "Award 1 mark for... Award 2 marks for...",
    "marks": 2
  }}
]

For multiple_choice questions, include an "options" array: ["A) ...", "B) ...", "C) ...", "D) ..."]

Return only a valid JSON array. No preamble, no markdown fences.
"""


def _call_with_retry(system: str, user_prompt: str, log_context: Optional[dict] = None) -> str:
    """Call the Anthropic API with a streamed request and a
    REQUEST_TIMEOUT_SECONDS timeout, retrying once on timeout/429/5xx with a
    short backoff. Raises AIGenerationError if both
    attempts fail.

    Prompt caching (`cache_control` on the system block) was tried and
    reverted — SYSTEM_PROMPT is ~80-120 tokens, well under Anthropic's
    ~1024-token minimum cacheable block size for Sonnet-tier models, so the
    marker was silently ignored (confirmed live: cache_creation_input_tokens
    and cache_read_input_tokens both came back 0). The SQLite content cache
    in cache_service.py is what actually keeps generation calls rare here;
    nothing in these prompts is large enough for Anthropic's own caching to
    help on top of that.

    Logs request metadata on success — topic_id, difficulty, duration,
    token count (CLAUDE.md Production Hardening — Logging) — never the
    request/response bodies themselves, which could carry the API key in
    headers if ever logged at a lower level.
    """
    client = _get_client()
    last_exc: Optional[Exception] = None
    context = log_context or {}
    start = time.monotonic()

    for attempt in range(2):
        try:
            # Streamed rather than a single blocking response. At MAX_TOKENS
            # = 8000 the Anthropic SDK documents streaming as the way to
            # avoid HTTP timeouts on long generations, and a stream keeps
            # bytes moving over the connection, which also stops an
            # intermediary proxy (Render's load balancer) treating a 40s
            # generation as an idle connection. get_final_message()
            # reassembles the complete response, so everything downstream —
            # .content, .usage — is unchanged.
            with client.with_options(
                timeout=REQUEST_TIMEOUT_SECONDS
            ).messages.stream(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                thinking={"type": "disabled"},
                system=system,
                messages=[{"role": "user", "content": user_prompt}],
            ) as stream:
                response = stream.get_final_message()
            duration = time.monotonic() - start
            usage = getattr(response, "usage", None)
            logger.info(
                "AI generation succeeded topic_id=%s difficulty=%s duration=%.2fs "
                "input_tokens=%s output_tokens=%s",
                context.get("topic_id"),
                context.get("difficulty"),
                duration,
                getattr(usage, "input_tokens", "unknown"),
                getattr(usage, "output_tokens", "unknown"),
            )
            return "".join(
                block.text for block in response.content if block.type == "text"
            ).strip()
        except (APITimeoutError, RateLimitError, APIStatusError) as exc:
            last_exc = exc
            logger.error(
                "AI generation attempt %d failed topic_id=%s difficulty=%s: %s: %s",
                attempt + 1,
                context.get("topic_id"),
                context.get("difficulty"),
                type(exc).__name__,
                exc,
            )
            if attempt == 0:
                time.sleep(RETRY_BACKOFF_SECONDS)

    raise AIGenerationError(
        "Generation temporarily unavailable — please try again shortly."
    ) from last_exc


def _parse_json(raw_text: str) -> Any:
    text = raw_text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
        text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise AIGenerationError(f"AI returned invalid JSON: {exc}") from exc


def generate_lesson(
    key_stage: str,
    topic_name: str,
    edexcel_ref: Optional[str],
    topic_id: Optional[int] = None,
) -> dict:
    """Generate a lesson package for one topic. Returns parsed JSON (dict).
    Raises AIGenerationError on repeated API failure or invalid JSON.
    `topic_id` is optional and used only for log context."""
    user_prompt = LESSON_USER_PROMPT_TEMPLATE.format(
        key_stage=key_stage,
        topic_name=topic_name,
        edexcel_ref=edexcel_ref or "N/A",
    )
    raw = _call_with_retry(SYSTEM_PROMPT, user_prompt, log_context={"topic_id": topic_id})
    return _parse_json(raw)


def generate_questions(
    key_stage: str,
    topic_name: str,
    difficulty: str,
    topic_id: Optional[int] = None,
) -> list:
    """Generate 6 questions for one topic/difficulty tier. Returns parsed
    JSON (list). Raises AIGenerationError on repeated API failure, invalid
    JSON, or an unknown difficulty tier. `topic_id` is optional and used
    only for log context."""
    if difficulty not in TIER_DEFINITIONS:
        raise ValueError(
            f"Invalid difficulty tier '{difficulty}'. "
            f"Must be one of {sorted(TIER_DEFINITIONS)}."
        )
    user_prompt = QUESTIONS_USER_PROMPT_TEMPLATE.format(
        key_stage=key_stage,
        topic_name=topic_name,
        difficulty=difficulty,
        tier_definition=TIER_DEFINITIONS[difficulty],
    )
    raw = _call_with_retry(
        SYSTEM_PROMPT, user_prompt, log_context={"topic_id": topic_id, "difficulty": difficulty}
    )
    return _parse_json(raw)
