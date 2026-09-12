"""All Anthropic API calls — single source of truth (CLAUDE.md AI Service Design).

No other module should call the Anthropic SDK directly. Every call gets a
timeout and one retry with a short backoff on timeout/429/5xx, per
CLAUDE.md Production Hardening — Resilience.

Lesson content is produced by three concurrent calls — teaching sequence,
supporting material, adaptive teaching — merged into one cached row. Split
for wall-clock reasons: the full lesson is roughly 2.5x the content of the
original single-call version, which in one request would run to ~95s and sit
uncomfortably close to the timeout. Three concurrent calls keep it near the
duration of the longest one.
"""

import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Optional

from anthropic import Anthropic, APIStatusError, APITimeoutError, RateLimitError

logger = logging.getLogger("mathsai")

# Opus rather than Sonnet because the failure mode that matters here is
# content failure — well-formed JSON containing wrong mathematics — which
# CLAUDE.md correctly says structural validation cannot catch. The design
# leans on a qualified teacher as the verifier, but mark-scheme allocation is
# a skill a trainee is still building, so model capability is standing in for
# a check that is not yet fully happening. Mathematical reasoning is exactly
# where Opus pulls ahead.
#
# Cost is a one-off per topic: `model_used` is recorded per cache row and
# content is never regenerated unless asked, so dropping back to Sonnet later
# for incremental topics leaves everything already cached untouched.
MODEL = "claude-opus-5"

# CLAUDE.md proposed 30s as "reasonable for one generation". Measured against
# the real workload it is not: a KS4 lesson returns thousands of output
# tokens and takes ~40s at ~100 tok/s, so every generation timed out,
# retried, timed out again, and surfaced a 503 after ~62s — while still
# being billed for both discarded completions, since the model had generated
# them in full before the client hung up.
REQUEST_TIMEOUT_SECONDS = 240.0
RETRY_BACKOFF_SECONDS = 2.0

# Thinking tokens count against this budget, so the 8000 that comfortably fit
# a non-thinking Sonnet response is no longer enough headroom.
MAX_TOKENS = 16000

# Thinking stays ON. Disabling it on Opus 5 is a documented trap: the model
# can leak <thinking> tags into the response, and since every response here is
# parsed as strict JSON that means a validation failure and a retry. Depth is
# controlled with `effort` instead. "high" is the default and the usual sweet
# spot; "max" would buy a little more care on hard problems at a noticeably
# higher token cost.
EFFORT = "high"

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
    "You are an experienced secondary mathematics teacher and subject lead in "
    "an English school, with deep expertise in the Edexcel KS3 and KS4 "
    "curriculum and in how pupils actually learn mathematics.\n\n"
    "You write lesson material a trainee teacher can take straight into a "
    "classroom. Your practice is grounded in:\n"
    "- Rosenshine's Principles of Instruction — daily review, small steps, "
    "modelling, guided practice, checking for understanding\n"
    "- Gradual release of responsibility — I do, We do, You do\n"
    "- Cognitive load theory — worked examples before problem solving, fading "
    "guidance progressively, avoiding split attention and redundancy\n"
    "- Adaptive teaching (Teachers' Standard 5) — the same learning goal for "
    "every pupil, reached by different routes\n\n"
    "You use Edexcel specification language, notation and command words "
    "throughout. Your explanations are precise and pitched for the year group "
    "given.\n\n"
    "You choose numbers deliberately. Examples use values that reveal the "
    "mathematical structure rather than obscure it, and that give clean "
    "answers — integers, or simple fractions — unless the topic is "
    "specifically about non-integer or irrational results. An example whose "
    "answer is an awkward fraction makes pupils doubt their method when the "
    "method was correct, and spends their working memory on arithmetic "
    "instead of on the idea being taught. Check the arithmetic of every "
    "example before you write it down.\n\n"
    "Write every field as finished material for a teacher to use. Do not "
    "narrate your own reasoning, correct yourself mid-sentence, or leave "
    "working notes in a field — revise and state the final version."
)

_CONTEXT_BLOCK = """\
Key Stage: {key_stage}
Year group: Year {year_group}
Strand: {strand}
Topic: {topic_name}
"""

_JSON_INSTRUCTION = "Return only valid JSON. No preamble, no markdown fences."

_DIAGRAM_RULE = """\
If something genuinely requires a diagram, set "requires_diagram" to true and \
describe precisely what to draw in "diagram_description". Never write "the \
diagram below" or "the diagram shows" without setting that flag — a question \
referring to a diagram that does not exist is unusable once printed."""


# --- Call A: the teaching sequence --------------------------------------

LESSON_CORE_PROMPT_TEMPLATE = (
    """\
Produce the teaching sequence for this lesson.

"""
    + _CONTEXT_BLOCK
    + """
topic_introduction — what the topic is, why it matters (a genuine reason, not
"it comes up on the exam"), the prior knowledge you are assuming, what it leads
on to later in the curriculum, the learning objectives, and success criteria
written so that a pupil could self-assess against them.

i_do — 2 modelled examples. Break each into steps. For every step give BOTH:
  - "working": exactly what you write on the board, in correct Edexcel notation
  - "narration": what you say aloud while writing it — the reasoning, the
    decision being made, why this step and not another
The narration is the teaching. Do not restate the working in words; explain the
thinking behind it. Choose the second example to vary something structurally
important, not merely the numbers.

we_do — 2 guided examples using PROGRESSIVE FADING:
  - Example 1 fades late: complete the early steps, leave the final step or two
    for the class.
  - Example 2 fades early: complete only the first step, leave the rest.
  Set "faded_from_step" to the step number at which support stops.
  "scaffolded_working" shows completed steps in full and open steps as clearly
  marked blanks, e.g. "Step 3: ________".
  "questions_to_ask" are what you put to the class at each open step — questions
  that probe reasoning, not ones that simply ask for the answer.
  "full_answer" is the complete worked solution, for the teacher's reference.

"""
    + _DIAGRAM_RULE
    + """

Return a JSON object with exactly this structure:

{{
  "topic_introduction": {{
    "what_it_is": "...",
    "why_it_matters": "...",
    "prior_knowledge_needed": ["..."],
    "leads_on_to": ["..."],
    "learning_objectives": ["..."],
    "success_criteria": ["..."]
  }},
  "i_do": [
    {{
      "title": "...",
      "problem": "...",
      "steps": [{{ "working": "...", "narration": "..." }}],
      "key_teaching_point": "...",
      "requires_diagram": false,
      "diagram_description": null
    }}
  ],
  "we_do": [
    {{
      "title": "...",
      "problem": "...",
      "scaffolded_working": "...",
      "faded_from_step": 3,
      "questions_to_ask": ["..."],
      "full_answer": "...",
      "requires_diagram": false,
      "diagram_description": null
    }}
  ]
}}

"""
    + _JSON_INSTRUCTION
)


# --- Call B: supporting material ----------------------------------------

LESSON_SUPPORT_PROMPT_TEMPLATE = (
    """\
Produce the supporting material for this lesson.

"""
    + _CONTEXT_BLOCK
    + """
starter — retrieval practice on the PREREQUISITES for this topic, not on the
topic itself. 6 questions forming a pool to select from. For each, name the
prerequisite skill it retrieves and give it a tier ("Fluency", "Reasoning" or
"Problem-solving") so the teacher can choose according to the class in front of
them. "retrieval_focus" explains what the set as a whole is checking is secure
before the lesson begins.

key_vocabulary — the terms pupils need. For each, a definition, and where the
word also has an everyday English meaning that differs from the mathematical
one (product, mean, table, power, root, face, volume, odd, similar, difference,
expression), give "everyday_meaning" as well. This matters most for EAL pupils,
who may know the everyday sense and be actively misled by it. Include
"notation" where the term has any.

common_errors — the misconceptions pupils genuinely hold for this topic. For
each: the error, "why_it_happens" (the faulty reasoning that produces it — not
"carelessness"), the correction, and "address_at" (the point in the lesson to
pre-empt it).

plenary — 3 exit ticket questions, each with what it checks. Between them they
should distinguish a pupil who has understood from one who has only imitated
the procedure.

Return a JSON object with exactly this structure:

{{
  "starter": {{
    "retrieval_focus": "...",
    "questions": [
      {{ "question": "...", "answer": "...", "prerequisite": "...", "tier": "Fluency" }}
    ]
  }},
  "key_vocabulary": [
    {{ "term": "...", "definition": "...", "everyday_meaning": null, "notation": null }}
  ],
  "common_errors": [
    {{ "error": "...", "why_it_happens": "...", "correction": "...", "address_at": "..." }}
  ],
  "plenary": [
    {{ "question": "...", "answer": "...", "checks": "..." }}
  ]
}}

"""
    + _JSON_INSTRUCTION
)


# --- Call C: adaptive teaching ------------------------------------------

ADAPTIVE_PROMPT_TEMPLATE = (
    """\
Produce the adaptive teaching plan for this lesson.

"""
    + _CONTEXT_BLOCK
    + """
The governing principle: every pupil works toward the SAME learning goal. You
are providing different routes to it, not different and easier destinations.
Never reduce mathematical demand.

scaffolds — for pupils with SEND and any pupil needing more support. For each:
the specific barrier, the scaffold that addresses it, and "remove_when" — the
observable point at which the scaffold should be withdrawn. A scaffold with no
removal condition becomes a ceiling.

concrete_representations — Concrete-Pictorial-Abstract. Name the actual resource
(algebra tiles, bar model, double-sided counters, Cuisenaire rods, number line,
place value counters, fraction strips), how to use it for THIS topic
specifically, and the bridge back to abstract notation. Generic advice to "use
manipulatives" is not usable.

language_support — for EAL learners:
  - "tier_2_vocabulary": academic words that carry the meaning in word problems
    (altogether, remaining, share, exceeds, respectively, in terms of)
  - "false_friends": words whose everyday meaning conflicts with the
    mathematical one
  - "sentence_stems": frames for explaining reasoning aloud and in writing, so
    pupils can access the reasoning marks rather than only the answer marks
  - "reduced_language_versions": take a realistic exam-style word problem for
    this topic and reword it with lower linguistic load and IDENTICAL
    mathematical demand. Give the original, the reworded version, and in
    "same_maths_because" the equation or calculation that BOTH versions lead
    to — they must be the same, with the same numbers and the same answer.
    Only the English changes: shorter sentences, familiar vocabulary, one
    clause at a time, no unnecessary narrative. Do NOT simplify the
    mathematics, change the numbers, or reduce the number of steps. A pupil
    whose barrier is language rather than mathematics must still meet the
    full mathematical demand of the topic; making the maths easier for them
    is lowering expectations, not adaptive teaching.

stretch — greater depth on the same content for pupils who need it: harder
reasoning, generalisation, proof, "always / sometimes / never" prompts, moving
between multiple representations. Not acceleration onto next year's content.

Return a JSON object with exactly this structure:

{{
  "adaptive_teaching": {{
    "scaffolds": [
      {{ "barrier": "...", "scaffold": "...", "remove_when": "..." }}
    ],
    "concrete_representations": [
      {{ "resource": "...", "how_to_use": "...", "bridge_to_abstract": "..." }}
    ],
    "language_support": {{
      "tier_2_vocabulary": [{{ "word": "...", "meaning_in_context": "..." }}],
      "false_friends": [
        {{ "word": "...", "everyday_meaning": "...", "maths_meaning": "..." }}
      ],
      "sentence_stems": ["..."],
      "reduced_language_versions": [
        {{ "original": "...", "reworded": "...", "same_maths_because": "..." }}
      ]
    }},
    "stretch": ["..."]
  }}
}}

"""
    + _JSON_INSTRUCTION
)


# --- Questions ("You do") -----------------------------------------------

TIER_DEFINITIONS = {
    "Fluency": (
        "single-step questions securing procedural fluency and recall of the "
        "core method. Weight towards short_answer and multiple_choice."
    ),
    "Reasoning": (
        "two or three step questions requiring method selection, explanation "
        "or justification. Weight towards show_working and short_answer, with "
        "some exam_style."
    ),
    "Problem-solving": (
        "multi-step questions in unfamiliar or applied contexts, requiring "
        "strategy, proof or generalisation. Weight towards exam_style and "
        "show_working."
    ),
}

QUESTIONS_USER_PROMPT_TEMPLATE = (
    """\
Generate 10 mathematics questions for independent practice ("You do").

"""
    + _CONTEXT_BLOCK
    + """Difficulty tier: {difficulty}
Tier definition: {tier_definition}
Exam board: Edexcel

The "type" field must be exactly one of these four strings (verbatim, no
variations): "short_answer", "multiple_choice", "show_working", "exam_style".
Weight the mix of types according to the tier definition above.

Use Edexcel command words in the question stems — "Work out", "Calculate",
"Show that", "Prove", "Write down", "Give a reason for your answer", "Hence",
"Estimate" — and record which one you used in "command_word". Pupils are
taught to read these; generic phrasing does not prepare them for the paper.

Write mark schemes in Edexcel notation: M1 for a method mark, A1 for accuracy,
B1 for an independent mark, with "oe" (or equivalent), "ft" (follow through)
and "cao" (correct answer only) where they apply. For example:
"M1 for 3x + 5 = 20 oe; A1 for x = 5".

Set "calculator_allowed" to false for skills assessed on Paper 1 (non-calculator
work such as surds, standard form by hand, estimation, fraction arithmetic),
true where a calculator is expected.

{misconception_block}
"""
    + _DIAGRAM_RULE
    + """

Return a JSON array with exactly this structure per question:

[
  {{
    "question_number": 1,
    "type": "short_answer",
    "question_text": "...",
    "answer": "...",
    "mark_scheme": "M1 for ... ; A1 for ...",
    "marks": 2,
    "command_word": "Work out",
    "calculator_allowed": true,
    "misconception_targeted": null,
    "requires_diagram": false,
    "diagram_description": null
  }}
]

For multiple_choice questions include an "options" array:
["A) ...", "B) ...", "C) ...", "D) ..."]

"""
    + _JSON_INSTRUCTION
)

_MISCONCEPTION_BLOCK_TEMPLATE = """\
These are the misconceptions identified for this topic in the lesson:

{misconceptions}

Build the questions to expose them. For EVERY multiple_choice question, at
least one distractor must be the answer a pupil would reach by holding one of
these misconceptions — not an arbitrary wrong number — and you must name that
misconception in "misconception_targeted". A distractor that nobody would
plausibly choose teaches you nothing about who is stuck and why; a distractor
that maps to a known misconception turns the question into a diagnostic.
Where a non-multiple-choice question targets one, name it in the same field.
"""


def _call_with_retry(system: str, user_prompt: str, log_context: Optional[dict] = None) -> str:
    """Call the Anthropic API with a streamed request and a
    REQUEST_TIMEOUT_SECONDS timeout, retrying once on timeout/429/5xx with a
    short backoff. Raises AIGenerationError if both attempts fail.

    Prompt caching (`cache_control` on the system block) was tried and
    reverted — SYSTEM_PROMPT is well under Anthropic's minimum cacheable
    block size for Sonnet-tier models, so the marker was silently ignored
    (confirmed live: cache_creation_input_tokens and cache_read_input_tokens
    both came back 0). The SQLite content cache in cache_service.py is what
    actually keeps generation calls rare here.

    Logs request metadata on success — topic_id, difficulty, duration,
    token count (CLAUDE.md Production Hardening — Logging) — never the
    request/response bodies themselves.
    """
    client = _get_client()
    last_exc: Optional[Exception] = None
    context = log_context or {}
    start = time.monotonic()

    for attempt in range(2):
        try:
            # Streamed rather than a single blocking response. At MAX_TOKENS
            # = 8000 the Anthropic SDK documents streaming as the way to
            # avoid HTTP timeouts on long generations, and a live stream also
            # stops an intermediary proxy (Render's load balancer) treating a
            # long generation as an idle connection. get_final_message()
            # reassembles the complete response, so .content and .usage are
            # unchanged downstream.
            with client.with_options(
                timeout=REQUEST_TIMEOUT_SECONDS
            ).messages.stream(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                thinking={"type": "adaptive"},
                output_config={"effort": EFFORT},
                system=system,
                messages=[{"role": "user", "content": user_prompt}],
            ) as stream:
                response = stream.get_final_message()
            duration = time.monotonic() - start
            usage = getattr(response, "usage", None)
            logger.info(
                "AI generation succeeded topic_id=%s part=%s difficulty=%s "
                "duration=%.2fs input_tokens=%s output_tokens=%s",
                context.get("topic_id"),
                context.get("part"),
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
                "AI generation attempt %d failed topic_id=%s part=%s difficulty=%s: %s: %s",
                attempt + 1,
                context.get("topic_id"),
                context.get("part"),
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


LESSON_PARTS = ("core", "support", "adaptive")

_LESSON_PART_TEMPLATES = {
    "core": LESSON_CORE_PROMPT_TEMPLATE,
    "support": LESSON_SUPPORT_PROMPT_TEMPLATE,
    "adaptive": ADAPTIVE_PROMPT_TEMPLATE,
}


def generate_lesson(
    key_stage: str,
    topic_name: str,
    strand: str,
    year_group: Optional[int] = None,
    topic_id: Optional[int] = None,
) -> dict:
    """Generate a full lesson package for one topic.

    Runs the three prompts concurrently and merges the fragments into a
    single dict matching LessonSchema. Raises AIGenerationError if any part
    fails after its own retry, or if any part returns invalid JSON.
    """
    context = {
        "key_stage": key_stage,
        "year_group": year_group if year_group is not None else "unspecified",
        "strand": strand,
        "topic_name": topic_name,
    }

    merged: dict = {}
    with ThreadPoolExecutor(max_workers=len(LESSON_PARTS)) as pool:
        futures = {
            pool.submit(
                _call_with_retry,
                SYSTEM_PROMPT,
                _LESSON_PART_TEMPLATES[part].format(**context),
                {"topic_id": topic_id, "part": part},
            ): part
            for part in LESSON_PARTS
        }
        for future in as_completed(futures):
            part = futures[future]
            # A failure in any part raises here and fails the whole lesson.
            # A lesson missing its adaptive teaching or its starter is not a
            # lesson this system should cache and present as complete.
            merged.update(_parse_json(future.result()))

    return merged


def generate_questions(
    key_stage: str,
    topic_name: str,
    difficulty: str,
    strand: str = "",
    year_group: Optional[int] = None,
    common_errors: Optional[list] = None,
    topic_id: Optional[int] = None,
) -> list:
    """Generate 10 independent-practice questions for one topic and tier.

    `common_errors` comes from the cached lesson when one exists, so the
    distractors can be built from the misconceptions the lesson identified.
    Omitted when no lesson has been generated yet — the questions are still
    produced, just without the diagnostic targeting.
    """
    if difficulty not in TIER_DEFINITIONS:
        raise ValueError(
            f"Invalid difficulty tier '{difficulty}'. "
            f"Must be one of {sorted(TIER_DEFINITIONS)}."
        )

    if common_errors:
        listed = "\n".join(
            f"- {item.get('error', '')} (why: {item.get('why_it_happens', 'not stated')})"
            for item in common_errors
        )
        misconception_block = _MISCONCEPTION_BLOCK_TEMPLATE.format(misconceptions=listed)
    else:
        misconception_block = ""

    user_prompt = QUESTIONS_USER_PROMPT_TEMPLATE.format(
        key_stage=key_stage,
        year_group=year_group if year_group is not None else "unspecified",
        strand=strand,
        topic_name=topic_name,
        difficulty=difficulty,
        tier_definition=TIER_DEFINITIONS[difficulty],
        misconception_block=misconception_block,
    )
    raw = _call_with_retry(
        SYSTEM_PROMPT,
        user_prompt,
        log_context={"topic_id": topic_id, "difficulty": difficulty, "part": "questions"},
    )
    return _parse_json(raw)
