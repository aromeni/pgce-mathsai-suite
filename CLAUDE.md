# CLAUDE.md — MathsAI: Automated KS3/KS4 Mathematics Teaching System

## Project Identity

**Project name:** MathsAI
**Owner:** Rashid Rashid — AI Engineer & PGCE Mathematics Trainee
**Purpose:** A teacher-facing web application that automates lesson planning, resource generation, and question creation for KS3 and KS4 mathematics, following the Edexcel curriculum. AI-generated content is cached to minimise API usage. The system is deployable both locally and online.

---

## Before You Start — Read This Fully

This is a plan-mode task. Before writing a single line of code, produce a full architectural plan covering:

1. Directory structure
2. Technology stack with justification
3. Database schema (SQLite)
4. API route design
5. Frontend component map
6. Caching strategy
7. AI integration design
8. Deployment approach

Wait for approval of the plan before proceeding to implementation. Build in clearly labelled phases. Do not combine phases. State assumptions explicitly.

---

## What This System Does

MathsAI is a single-teacher tool. The teacher (Abdul) uses it to:

- Browse KS3 and KS4 Edexcel mathematics topics via a structured dashboard
- Select a topic and automatically generate a full lesson package
- View and edit lesson notes, explanations, and worked examples
- Generate three tiers of practice questions (Foundation, Developing, Extending) with answers
- Track which topics have been taught and when
- Export lesson content and questions to PDF or printable format
- All AI-generated content is cached in SQLite so it is never regenerated unnecessarily

---

## Technology Stack

Use the following stack. Do not deviate without flagging a reason.

**Backend:** Python 3.11+ with FastAPI
**Database:** SQLite via SQLAlchemy ORM (no external DB server required)
**AI Integration:** Anthropic Python SDK (`anthropic`) using `claude-sonnet-4-6`
**Frontend:** Single-page React application (Vite \+ React 18\)
**Styling:** Tailwind CSS with a clean, dark professional aesthetic — dark charcoal background, teal accent (`#00d4b8`), mono font for content areas
**PDF Export:** `weasyprint` or `reportlab` for server-side PDF generation
**Caching:** SQLite-backed cache — generated content is stored on first generation and retrieved on subsequent requests, never regenerated unless explicitly refreshed
**Deployment:** Runs locally via `uvicorn`. Can be deployed to Railway, Render, or Fly.io with minimal change, or kept private via Tailscale — decided explicitly in Phase 8, see Production Hardening. Include a `Dockerfile` from the start.
**Testing:** `pytest` \+ FastAPI's `TestClient`, with the Anthropic client mocked via `unittest.mock`
**Migrations:** Alembic, from the first schema version onward
**Logging:** Python's standard `logging` module with a rotating file handler

---

## Directory Structure

Implement exactly this structure:

mathsai/

├── backend/

│   ├── main.py                  \# FastAPI app entry point

│   ├── database.py              \# SQLAlchemy setup, engine, session

│   ├── models.py                \# All ORM models

│   ├── schemas.py               \# Pydantic request/response schemas

│   ├── routers/

│   │   ├── topics.py            \# Topic browsing and curriculum structure

│   │   ├── lessons.py           \# Lesson generation and retrieval

│   │   ├── questions.py         \# Question generation and retrieval

│   │   ├── progress.py          \# Teaching history and progress tracking

│   │   └── export.py            \# PDF and print export

│   ├── services/

│   │   ├── ai\_service.py        \# All Anthropic API calls — single source of truth

│   │   ├── cache\_service.py     \# Cache read/write logic

│   │   ├── improvement\_agent.py \# Proposes revisions to existing content — never writes

│   │   │                        \# to lesson\_cache/question\_cache directly (Phase 10)

│   │   └── curriculum.py        \# Edexcel KS3/KS4 topic taxonomy (static data)

│   └── requirements.txt

├── frontend/

│   ├── src/

│   │   ├── App.jsx

│   │   ├── pages/

│   │   │   ├── Dashboard.jsx    \# Topic browser — main entry point

│   │   │   ├── Lesson.jsx       \# Lesson view with notes and examples

│   │   │   ├── Questions.jsx    \# Question display by difficulty tier

│   │   │   ├── Progress.jsx     \# Teaching history tracker

│   │   │   └── Suggestions.jsx  \# Pending content-revision suggestions (Phase 10)

│   │   ├── components/

│   │   │   ├── TopicCard.jsx

│   │   │   ├── DifficultyBadge.jsx

│   │   │   ├── QuestionBlock.jsx

│   │   │   ├── LessonPanel.jsx

│   │   │   └── Sidebar.jsx

│   │   └── api/

│   │       └── client.js        \# Axios API client

│   ├── index.html

│   ├── vite.config.js

│   └── tailwind.config.js

├── Dockerfile

├── docker-compose.yml

└── README.md

---

## Database Schema

Implement all of the following tables in `models.py` using SQLAlchemy declarative base.

### Table: `topics`

Stores the full Edexcel KS3/KS4 curriculum taxonomy. Seeded on first run.

id              INTEGER PRIMARY KEY

key\_stage       TEXT NOT NULL          \-- 'KS3' or 'KS4'

strand          TEXT NOT NULL          \-- e.g. 'Number', 'Algebra', 'Geometry'

topic\_name      TEXT NOT NULL          \-- e.g. 'Fractions', 'Quadratic Equations'

edexcel\_ref     TEXT                   \-- e.g. 'N5', 'A12'

difficulty\_band TEXT                   \-- 'Foundation', 'Higher', or 'Both'

created\_at      DATETIME

### Table: `lesson_cache`

Stores AI-generated lesson content. One row per topic. Never regenerated unless `force_refresh=true`.

id              INTEGER PRIMARY KEY

topic\_id        INTEGER FK → topics.id

lesson\_notes    TEXT                   \-- Full markdown lesson notes

worked\_examples TEXT                   \-- JSON array of worked examples

key\_vocabulary  TEXT                   \-- JSON array of key terms and definitions

common\_errors   TEXT                   \-- JSON array of common misconceptions

generated\_at    DATETIME

model\_used      TEXT                   \-- e.g. 'claude-sonnet-4-6'

reviewed        BOOLEAN NOT NULL DEFAULT FALSE   \-- teacher has checked content before classroom use

reviewed\_at     DATETIME                          \-- null until reviewed

### Table: `question_cache`

Stores AI-generated questions per topic per difficulty tier. Three rows per topic (one per tier).

id              INTEGER PRIMARY KEY

topic\_id        INTEGER FK → topics.id

difficulty      TEXT NOT NULL          \-- 'Foundation', 'Developing', 'Extending'

questions       TEXT NOT NULL          \-- JSON array of question objects

generated\_at    DATETIME

model\_used      TEXT

reviewed        BOOLEAN NOT NULL DEFAULT FALSE   \-- teacher has checked mark schemes before classroom use

reviewed\_at     DATETIME                          \-- null until reviewed

Question object structure (JSON):

{

  "question\_number": 1,

  "type": "short\_answer | multiple\_choice | show\_working | exam\_style",

  "question\_text": "...",

  "options": \["A", "B", "C", "D"\],   // only for multiple\_choice

  "answer": "...",

  "mark\_scheme": "...",

  "marks": 2

}

### Table: `teaching_log`

Records each time a topic is taught, for progress tracking.

id              INTEGER PRIMARY KEY

topic\_id        INTEGER FK → topics.id

taught\_date     DATE NOT NULL

class\_label     TEXT                   \-- e.g. 'Year 9 Set 2'

notes           TEXT                   \-- Optional teacher notes

### Table: `regeneration_log`

Audit trail of every forced regeneration, so accidental repeated clicks are visible after the fact even though the UI also guards against them at the point of click (see Production Hardening).

id              INTEGER PRIMARY KEY

topic\_id        INTEGER FK → topics.id

content\_type    TEXT NOT NULL          \-- 'lesson' or 'question:\<difficulty\>'

timestamp       DATETIME NOT NULL

### Table: `content_feedback`

Captures a signal that existing cached content might need revisiting. Written by the frontend when an edit is saved, by the teacher after a lesson, or manually when a spec change is noticed. Never triggers a change by itself — it's raw material for the improvement agent to read.

id              INTEGER PRIMARY KEY

topic\_id        INTEGER FK → topics.id

content\_type    TEXT NOT NULL          \-- 'lesson' or 'question:\<difficulty\>'

signal\_type     TEXT NOT NULL          \-- 'edit\_diff' | 'post\_lesson\_note' | 'spec\_drift' | 'self\_critique'

payload         TEXT NOT NULL          \-- JSON, shape depends on signal\_type — see Improvement Agent

created\_at      DATETIME NOT NULL

### Table: `suggested_revisions`

What the improvement agent proposes in response to feedback. Never applied automatically — see Improvement Agent for why.

id                      INTEGER PRIMARY KEY

topic\_id                INTEGER FK → topics.id

content\_type            TEXT NOT NULL          \-- 'lesson' or 'question:\<difficulty\>'

triggering\_feedback\_id  INTEGER FK → content\_feedback.id (nullable — a suggestion can be

                                                            general, not tied to one signal)

proposed\_content        TEXT NOT NULL          \-- JSON, same shape as lesson\_cache/question\_cache

rationale               TEXT NOT NULL          \-- plain-English explanation of the proposed change

status                  TEXT NOT NULL DEFAULT 'pending'   \-- 'pending' | 'accepted' | 'rejected'

created\_at              DATETIME NOT NULL

resolved\_at             DATETIME

---

## Curriculum Data — Edexcel KS3 and KS4 Topic Taxonomy

Seed the `topics` table on first run using the following taxonomy. This is static data — implement it in `curriculum.py` as a list of dicts and call a seed function at startup if the table is empty.

### KS3 Topics (Year 7–9)

**Number**

- Place value and ordering
- Addition and subtraction
- Multiplication and division
- Fractions
- Decimals
- Percentages
- Ratio and proportion
- Powers and roots
- Order of operations (BIDMAS)
- Negative numbers

**Algebra**

- Introduction to algebra (expressions and terms)
- Simplifying expressions
- Expanding brackets
- Factorising
- Solving linear equations
- Sequences (term-to-term and nth term)
- Coordinates and straight-line graphs
- Substitution

**Geometry and Measures**

- Angles (types, rules, parallel lines)
- Properties of 2D shapes
- Properties of 3D shapes
- Perimeter and area
- Volume and surface area
- Transformations (reflection, rotation, translation, enlargement)
- Symmetry
- Constructions and loci
- Pythagoras' theorem (introduction)
- Units and measurement

**Statistics and Probability**

- Collecting and organising data
- Bar charts, pie charts, pictograms
- Mean, median, mode and range
- Scatter graphs and correlation
- Basic probability
- Frequency tables and two-way tables

### KS4 Topics (Year 10–11) — Edexcel GCSE

**Number**

- Indices and surds
- Standard form
- Bounds and error intervals
- Fractions (complex operations)
- Percentage change, reverse percentage
- Ratio and proportion (advanced)
- Recurring decimals

**Algebra**

- Expanding and factorising (advanced)
- Quadratic equations (factorising, formula, completing the square)
- Simultaneous equations
- Inequalities
- nth term of quadratic sequences
- Functions and function notation
- Graph transformations
- Linear and quadratic graphs
- Cubic and reciprocal graphs
- Real-life graphs
- Iteration
- Algebraic proof

**Ratio, Proportion and Rates of Change**

- Direct and inverse proportion
- Compound measures (speed, density, pressure)
- Growth and decay
- Rates of change from graphs

**Geometry and Measures**

- Circle theorems
- Arc length and sector area
- Pythagoras in 3D
- Trigonometry (SOHCAHTOA)
- Sine and cosine rules
- Vectors
- Congruence and similarity
- Plans and elevations
- Surface area and volume (advanced)
- Bearings

**Probability and Statistics**

- Venn diagrams and set notation
- Tree diagrams
- Conditional probability
- Cumulative frequency and box plots
- Histograms
- Sampling methods
- Averages from grouped frequency tables

---

## AI Service Design

All Anthropic API calls live exclusively in `ai_service.py`. No other file calls the API directly.

### Lesson Generation Prompt

When generating a lesson for a given topic, call `claude-sonnet-4-6` with the following system prompt and structure. Store the result in `lesson_cache`.

**System prompt:**

You are an experienced secondary mathematics teacher with deep expertise in the Edexcel KS3 and KS4 curriculum. You write clear, pedagogically sound lesson content for a trainee teacher to use directly in the classroom. Your explanations are precise, your examples are well-chosen, and your language is appropriate for secondary school pupils in England. You always follow Edexcel specification language and notation.

**User prompt template:**

Generate a complete lesson package for the following mathematics topic:

Key Stage: {key\_stage}

Topic: {topic\_name}

Edexcel Reference: {edexcel\_ref}

Return your response as a valid JSON object with exactly this structure:

{

  "lesson\_notes": "Full markdown lesson notes including: learning objectives, key concept explanation, step-by-step method, at least two fully worked examples with commentary",

  "worked\_examples": \[

    {

    "title": "Example 1 —\[description\]",

    "problem": "...",

    "solution": "Step-by-step solution with working shown",

    "teaching\_note": "What the teacher should draw attention to"

    }

  \],

  "key\_vocabulary": \[

    { "term": "...", "definition": "..." }

  \],

  "common\_errors": \[

    { "error": "...", "correction": "..." }

  \]

}

Return only valid JSON. No preamble, no markdown fences.

### Question Generation Prompt

Generate questions for a specific topic and difficulty tier. Store in `question_cache`.

**Difficulty tier definitions to include in the prompt:**

- Foundation: straightforward single-step questions testing basic recall and application
- Developing: two or three step questions requiring method selection
- Extending: multi-step, exam-style questions requiring reasoning, proof, or problem-solving

**User prompt template:**

Generate 10 mathematics questions for the following:

Key Stage: {key\_stage}

Topic: {topic\_name}

Difficulty tier: {difficulty}

Tier definition: {tier\_definition}

Exam board: Edexcel

Include a mix of question types: multiple choice, short answer, show-your-working, and exam-style.

Return a valid JSON array with exactly this structure per question:

\[

  {

    "question\_number": 1,

    "type": "short\_answer",

    "question\_text": "...",

    "answer": "...",

    "mark\_scheme": "Award 1 mark for... Award 2 marks for...",

    "marks": 2

  }

\]

For multiple\_choice questions, include an "options" array: \["A) ...", "B) ...", "C) ...", "D) ..."\]

Return only a valid JSON array. No preamble, no markdown fences.

### Caching Logic

In `cache_service.py`, implement the following logic cleanly:

def get\_lesson(topic\_id: int, force\_refresh: bool \= False) \-\> dict | None:

    \# 1\. If force\_refresh is False, check lesson\_cache for existing row

    \# 2\. If found, parse and return the cached JSON

    \# 3\. If not found or force\_refresh:

    \#    a. call ai\_service.generate\_lesson() — this already retries once internally

    \#       on timeout/rate-limit (see Production Hardening)

    \#    b. validate the response against the LessonSchema Pydantic model

    \#    c. if validation fails, retry generation once with the same prompt

    \#    d. if it fails again, raise — do not store invalid content

    \# 4\. Store validated result in lesson\_cache with reviewed=False

    \# 5\. If step 3 raises and a stale cached row already exists, log the failure

    \#    and return the stale row rather than propagating the error (see

    \#    Production Hardening — Resilience)

    \# 6\. Return result

def get\_questions(topic\_id: int, difficulty: str, force\_refresh: bool \= False) \-\> list | None:

    \# Same pattern as above but validated against QuestionSetSchema

    \# difficulty must be one of: 'Foundation', 'Developing', 'Extending'

---

## Improvement Agent

This is additive, not a replacement for anything above. `ai_service.py` still owns first-generation of content from a bare topic; this module owns proposing *changes* to content that already exists and is (or was) reviewed. Keep them separate files — they have different inputs, different prompts, and different consequences if they go wrong.

### The constraint this design exists to satisfy

The `reviewed` flag means "a qualified maths teacher has personally checked this." An agent that edits cached content on its own authority, however well-intentioned, breaks that guarantee silently — content marked reviewed would no longer be what was reviewed. So the rule is absolute: this module never writes to `lesson_cache` or `question_cache`. It only ever writes to `suggested_revisions`. The only path from a suggestion to live content is a human clicking Accept.

### Where signals come from

Four `signal_type` values, each with its own `payload` shape in `content_feedback`:

`edit_diff` — logged automatically whenever a teacher edits AI-generated content before use. Payload: `{"field": "lesson_notes", "before": "...", "after": "..."}`. This is the strongest signal available, because it's not a guess about what's wrong — it's a direct record of what you personally changed. **Note: this depends on an in-place content-editing UI that does not exist yet in `Lesson.jsx`/`Questions.jsx` (those pages currently display and regenerate, not edit) — building that editing capability is a prerequisite for this signal type, not a detail to defer.**

`post_lesson_note` — an optional free-text prompt after a `teaching_log` entry: did anything land badly, need more scaffolding than expected, or cause confusion? Payload: `{"note": "...", "class_label": "..."}`.

`spec_drift` — logged manually when Edexcel updates a specification or publishes new sample assessment material. Payload: `{"description": "...", "source_url": "..."}`.

`self_critique` — a confidence/concern field the model emits as part of its *original* generation response (never a separate follow-up call — a second "double-check yourself" call repeats the exact self-verification weakness described in Production Hardening — Validating AI output, at extra cost, for no reliability gain). Payload: `{"concern": "...", "confidence": "low|medium|high"}`. Treat this one as the weakest signal of the four — it triages what to look at first, it does not verify anything.

### What the agent does with a signal

def generate\_suggestion(topic\_id: int, content\_type: str, feedback\_id: int | None \= None) \-\> dict:

    \# 1\. Load the current cached content for (topic\_id, content\_type) — this must

    \#    already exist; there is nothing to improve on a topic that's never been generated

    \# 2\. Load the triggering feedback row if feedback\_id is given, otherwise load all

    \#    unresolved content\_feedback rows for this (topic\_id, content\_type)

    \# 3\. Build a prompt that explicitly frames this as revision, not regeneration:

    \#    "Here is the existing reviewed content. Here is a signal suggesting a gap.

    \#     Propose a specific, targeted change and explain your reasoning. Do not

    \#     rewrite what isn't implicated by the signal."

    \# 4\. Validate the proposed JSON against the same LessonSchema / QuestionSetSchema

    \#    used in ai\_service.py — reuse those models, don't redefine them

    \# 5\. Write a row to suggested\_revisions with status='pending'

    \# 6\. Return the created row

The prompt instruction in step 3 matters more than it looks — a generic "regenerate this topic" prompt will happily rewrite parts that were already fine, which defeats the point of showing a focused diff for review. Constrain it explicitly to the signal.

### Accepting or rejecting a suggestion

POST /api/suggestions/{id}/accept

POST /api/suggestions/{id}/reject

Reject: set `status='rejected'`, `resolved_at=now`. No other effect.

Accept: copy `proposed_content` into the relevant cache table, set `status='accepted'`, `resolved_at=now` — and set the cache row's `reviewed` back to `false`, not `true`. This is deliberate, not an oversight: accepting means "this direction looks right," reviewing means "I have personally checked this is classroom-ready," and those are different judgements made at different moments. Collapsing them would let a suggestion reach `reviewed=true` status without the actual check the flag exists to represent. Also write a row to `regeneration_log` with `content_type` suffixed `:agent-suggested`, so the audit trail distinguishes an agent-driven change from a manual `force_refresh` at a glance.

### Trigger: on-demand, not scheduled

No background scheduler, no cron, no always-running process. A `POST /api/topics/{id}/generate-suggestions` route runs `generate_suggestion` against any unresolved feedback for that topic when you ask for it — from the UI, when you're actually looking at a topic and want to know if anything's changed. This was the deliberate call from the earlier proportionality discussion: an always-on poller needs its own scheduler, its own failure handling independent of any request-response cycle, and its own logging — real operational surface for a single-teacher tool that doesn't need to be running unattended. If usage later shows the on-demand trigger gets forgotten and feedback piles up unread, a scheduled batch job is a small, well-contained addition at that point — not a reason to build it now.

---

## API Routes

Implement all routes in the relevant router files. All routes return JSON.

### Topics Router (`/api/topics`)

GET  /api/topics                          \# All topics, grouped by key\_stage and strand

GET  /api/topics/{id}                     \# Single topic detail

GET  /api/topics/ks3                      \# KS3 topics only

GET  /api/topics/ks4                      \# KS4 topics only

GET  /api/topics/search?q={query}         \# Search topics by name

### Lessons Router (`/api/lessons`)

GET  /api/lessons/{topic\_id}              \# Get lesson (from cache or generate)

POST /api/lessons/{topic\_id}/refresh      \# Force regenerate lesson

### Questions Router (`/api/questions`)

GET  /api/questions/{topic\_id}/{difficulty}         \# Get questions for tier

POST /api/questions/{topic\_id}/{difficulty}/refresh \# Force regenerate

### Progress Router (`/api/progress`)

GET  /api/progress                        \# All teaching log entries

POST /api/progress                        \# Log a topic as taught

GET  /api/progress/topic/{topic\_id}       \# Has this topic been taught? When?

DELETE /api/progress/{id}                 \# Remove a log entry

### Export Router (`/api/export`)

GET  /api/export/lesson/{topic\_id}/pdf    \# Export lesson notes as PDF

GET  /api/export/questions/{topic\_id}/pdf \# Export all three tiers as PDF

### Feedback & Suggestions Router (`/api/feedback`, `/api/suggestions`)

POST /api/feedback                              \# Log a signal: edit\_diff, post\_lesson\_note,

                                                 \# spec\_drift, or self\_critique

GET  /api/suggestions?topic\_id=\&status=         \# List suggestions, filterable

POST /api/topics/{id}/generate-suggestions      \# On-demand: run the improvement agent

                                                 \# against unresolved feedback for this topic

POST /api/suggestions/{id}/accept               \# Apply proposed\_content, reset reviewed=false

POST /api/suggestions/{id}/reject               \# Mark rejected, no cache write

---

## Frontend Design

### Dashboard Page (`Dashboard.jsx`)

This is the main view. It shows:

- A sidebar with KS3 / KS4 toggle and strand filter (Number, Algebra, Geometry, Statistics)
- A main grid of topic cards
- Each topic card shows: topic name, key stage badge, strand, whether it has been taught (green tick), whether content is cached (blue lightning bolt icon)
- Clicking a topic card navigates to the Lesson page for that topic

### Lesson Page (`Lesson.jsx`)

This view shows the full lesson package for a selected topic. Layout:

- Top: topic name, key stage, strand, Edexcel reference
- Tab 1 — Lesson Notes: rendered markdown with learning objectives, explanation, worked examples
- Tab 2 — Key Vocabulary: term/definition pairs in a clean table
- Tab 3 — Common Errors: misconception cards with correction
- Bottom bar: three buttons — Foundation Questions / Developing Questions / Extending Questions — each navigates to the Questions page with that tier selected
- A "Regenerate" button that calls the force\_refresh endpoint
- A "Mark as Taught" button that logs the topic

### Questions Page (`Questions.jsx`)

Shows questions for the selected topic and difficulty tier.

- Difficulty selector at the top (three tabs: Foundation / Developing / Extending)
- Each question displayed in a clean card showing: question number, type badge, question text, marks
- An "Show Answer" toggle per question that reveals the answer and mark scheme
- A "Regenerate Questions" button
- Export to PDF button

### Progress Page (`Progress.jsx`)

A simple table showing all topics that have been logged as taught, with date and class label. Filterable by key stage and strand.

### Suggestions Page (`Suggestions.jsx`)

Shows pending suggestions across all topics, or scoped to one topic when reached from the Lesson/Questions page.

- Each suggestion shown as a card: topic name, content type, the rationale in plain text, and a field-aware before/after — not a raw JSON diff. For `lesson_notes`, render both versions as markdown side by side; for structured fields like `worked_examples` or `questions`, diff item by item rather than as one undifferentiated blob. This is the one genuinely fiddly piece of UI in the whole system — a wall of changed JSON is unreadable, so it's worth the extra render logic to keep each field's diff legible on its own terms.
- Accept and Reject buttons per suggestion. Accepting shows a brief confirmation that the content still needs review before classroom use — don't let the act of accepting read as "this is now safe."
- A "Check for improvements" button on the Lesson and Questions pages, scoped to the current topic, calling `generate-suggestions` on demand.

---

## Aesthetic and UI Requirements

Follow these design rules precisely.

Background: `#0d0d14` (near-black)
Surface: `#13131e`
Border: `rgba(255,255,255,0.07)`
Accent: `#00d4b8` (teal)
Text primary: `#e8e8f0`
Text secondary: `#7070a0`
Font: `DM Mono` for content and code areas, `Syne` for headings
Import both from Google Fonts.

Difficulty tier colours:

- Foundation: `#4ade80` (green)
- Developing: `#facc15` (amber)
- Extending: `#f87171` (red)

All cards should have subtle hover states. No excessive animation. Clean, information-dense, professional.

---

## Implementation Phases

Build in this sequence. Complete and confirm each phase before starting the next.

### Phase 1 — Project Scaffold

Set up the full directory structure, install dependencies, initialise FastAPI, initialise SQLite database, and run the seed function to populate all topics. Verify by hitting `/api/topics` and receiving the full curriculum list.

### Phase 2 — AI Service and Caching

Implement `ai_service.py` and `cache_service.py`. Test lesson generation and question generation for a single topic (e.g. KS4 Quadratic Equations). Verify caching works by calling twice and confirming the second call returns cached data without an API call.

### Phase 3 — All API Routes

Implement all routers. Test every route with example data. Ensure error handling is in place for missing topics, failed generation, and invalid difficulty values.

### Phase 4 — Frontend Scaffold

Set up Vite \+ React \+ Tailwind. Implement routing (React Router). Build the Sidebar and Dashboard with topic cards. Connect to the topics API. Verify all topics display correctly grouped by strand.

### Phase 5 — Lesson and Questions UI

Implement the Lesson page and Questions page fully. Connect to the lesson and questions APIs. Implement the Show Answer toggle. Test the full flow: select topic → view lesson → switch to questions → change difficulty tier.

### Phase 6 — Progress Tracking

Implement the teaching log — Mark as Taught button, Progress page, taught indicator on topic cards.

### Phase 7 — PDF Export

Implement server-side PDF generation for lesson notes and questions. Test download in browser.

### Phase 8 — Dockerfile and Deployment

Confirm the network-access decision from Production Hardening (private via Tailscale, or public with mandatory password auth) before writing deployment code — this determines whether auth middleware is in scope for this phase. Write `Dockerfile` and `docker-compose.yml`. Configure CORS for the confirmed frontend origin. Add the `/api/health` route. Test local container build. Document the chosen path in `README.md`, including how the SQLite file is persisted (a mounted volume, not ephemeral container storage).

### Phase 9 — Production Hardening

Implement the rest of the Production Hardening section in full: retries and timeouts on all Anthropic calls, Pydantic validation with one retry on parse failure, the `reviewed` workflow in the UI (amber marker, "Mark reviewed" action), the `regeneration_log` table with the confirm-before-refresh dialog, structured logging, Alembic migrations retrofitted as the first revision against the Phase 1 schema, and the pytest suite with mocked API calls plus the GitHub Actions workflow. Treat this as part of the definition of done, not a stretch goal.

### Phase 10 — Improvement Agent

**Before writing any code in this phase:** read the actual current `models.py`, `routers/`, and `services/` in this project and reconcile them against this spec. This section was designed against the plan, not against the live codebase, and Phase 9 in particular (Alembic, the exact shape of `reviewed`/`reviewed_at`) may have been implemented with reasonable deviations during the real build. Where the real code differs from what's written here, follow the real code's existing conventions rather than forcing this spec's wording — consistency with what's already running matters more than matching this document exactly. (Alembic is already wired up from Phase 9 — this phase adds one more revision to it, nothing needs setting up from scratch.)

Add the `content_feedback` and `suggested_revisions` tables as a new Alembic revision. Implement `improvement_agent.py` per the Improvement Agent section, reusing the existing `LessonSchema`/`QuestionSetSchema` Pydantic models rather than redefining them. Add the Feedback & Suggestions router. Build `Suggestions.jsx` with field-aware diffing — this is the part most likely to take longer than it looks; budget for it. Wire the "Check for improvements" action into the existing Lesson and Questions pages rather than treating Suggestions as a disconnected fifth page. Note the `edit_diff` signal's prerequisite (an in-place content-editing UI that doesn't exist yet) called out in the Improvement Agent section above — either build it as part of this phase or scope the first cut of Phase 10 to the other three signal types and land editing separately. Verify by manually creating a feedback row (`post_lesson_note` or `spec_drift` are the two signal types with no UI prerequisite), triggering `generate-suggestions`, confirming a `pending` suggestion appears with a sensible rationale, accepting it, and confirming the target cache row now shows `reviewed=false`.

This is the first slice of a broader move toward automating more of the teaching workflow, not the whole of it — deliberately scoped to content QA/revision rather than scheme-of-work planning, pacing, or anything that decides *what* gets taught *when*. Revisit scope for any further agentic phase only after this one is built and actually used for a while.

---

## Code Quality Requirements

- All Python follows PEP 8\.
- All API responses use consistent Pydantic schemas.
- Database sessions use dependency injection via FastAPI `Depends`.
- All AI prompts are defined as constants or templates in `ai_service.py`, never hardcoded inline in routes.
- SQLite WAL mode should be enabled for better concurrent read performance.
- Environment variables used for: `ANTHROPIC_API_KEY`, `DATABASE_URL`, `ENVIRONMENT`. No password/auth variable is needed — see Production Hardening, Network access and authentication.
- Use `python-dotenv` for local `.env` loading.
- Include a `.env.example` file.
- All JSON stored in SQLite TEXT fields must be validated on write and parsed on read.
- Frontend API calls all go through `api/client.js` — no raw fetch calls scattered through components.
- React components should be clean and single-purpose. No component should exceed 200 lines.

---

## Error Handling

Handle the following cases explicitly:

- Anthropic API rate limit or timeout → return 503 with a clear message, do not crash
- Topic not found → return 404
- Invalid difficulty tier → return 422 with validation error
- Cache read failure → fall through to regeneration, log the error
- PDF generation failure → return 500 with detail
- Empty question response from AI → retry once, then return error

---

## Production Hardening

This system will be reachable beyond a single laptop, and it calls a metered external API on every generation. Both facts make the following load-bearing rather than optional polish. Scale everything here to a single-teacher tool — no microservices, no message queues, no multi-user auth. The goal is safety and robustness at the right size, not enterprise architecture for its own sake.

### Network access and authentication

Resolved: Tailscale-only, no public hosting, no password layer. This reaches every device on the tailnet without putting the app or the Anthropic API key on the open internet at all — the network itself is the perimeter. The public-hosting-with-password-auth alternative that was left open earlier no longer applies now the project is confirmed personal-use only; if that changes later, revisit it then rather than carrying unused conditional logic in the codebase now.

### Secrets management

`ANTHROPIC_API_KEY` never reaches the frontend bundle or a client-visible request — this already follows from all Anthropic calls living in `ai_service.py`. In addition:

- `.env` is in `.gitignore` from the first commit, not added retroactively once something has already leaked into history.
- `.env.example` lists variable names with placeholder values only.
- If public hosting is chosen, the key is set via the platform's own secret manager, never committed.
- Logs capture request metadata (topic\_id, difficulty, duration, token count) — never full request/response bodies, which could contain the key in headers.

### Resilience: retries, timeouts, and graceful degradation

Handle all of this inside `ai_service.py`, not scattered across routes:

- Every Anthropic call gets a timeout (30s is reasonable for one generation) and one retry with a short backoff on timeout or a 429/5xx — not more than one; a teacher waiting on a lesson to load should see a fast, clear failure, not a silent minute-long retry loop.
- On repeated failure, return a 503 with a plain-language message ("Generation temporarily unavailable — please try again shortly"), never a raw stack trace.
- If regeneration fails but a stale cached version already exists, serve the stale version rather than an error, with a small UI note ("Last generated \[date\] — refresh failed, showing previous version"). An outdated lesson is more useful mid-planning than a blank screen.

### Validating AI output — and being honest about what validation can't catch

Two different failure modes, two different defences — don't conflate them.

**Structural failure** (malformed JSON, missing field) is fully preventable: define `LessonSchema` and `QuestionSetSchema` as Pydantic models, validate every AI response against them immediately, retry once on failure, and never write invalid content to the cache. This is what the updated Caching Logic above implements.

**Content failure** (well-formed JSON, wrong mathematics — a mark scheme that doesn't match the question, an arithmetic slip) is not reliably caught by asking the model to check its own working. Self-verification of arithmetic is a known weak point, and a second API call to "double-check" adds cost without a strong correctness guarantee. Don't build a false sense of safety here.

Instead, the `reviewed` flag added to `lesson_cache` and `question_cache` does the honest job: new content surfaces in the UI with a visible amber "Not yet checked" marker until Abdul opens it and clicks "Mark reviewed." The one reliable verifier in this system is a qualified maths teacher, so put him in the loop before anything reaches a classroom — cheaper and more trustworthy than an automated pass.

### Cost guardrails on regeneration

Every `force_refresh=true` call writes a row to `regeneration_log`. On the frontend, the Regenerate button opens a one-line confirmation ("This will use API credits — continue?") rather than firing on click — deliberate friction against an accidental double-click costing money, not a rate limiter against legitimate use.

Separately: the Phase 1 seed function populates `topics` (names, strands, references) only. It must never trigger content generation for all \~70+ topics on first run — that's 200+ generation calls before a single lesson has been taught. Content generates lazily on first view and is cached from that point.

### Logging

Python's `logging` module with a rotating file handler, not `print()`. `INFO` for normal operation (generation requests, cache hits/misses, topic views), `ERROR` for failures with enough context to debug without reproducing (topic\_id, endpoint, exception type). No bodies containing the API key.

### Testing strategy

Proportionate to a single-user tool, not exhaustive:

- Unit tests for `cache_service.py` covering cache hit, cache miss, force-refresh, and validation-failure-retry paths, with the Anthropic client mocked — never call the real API in tests.
- Integration tests per router via FastAPI's `TestClient`, covering the happy path and the documented error cases (topic not found, invalid difficulty).
- No frontend test suite is required at this scale; the manual per-phase verification already specified in Implementation Phases is sufficient there.
- A minimal `.github/workflows/test.yml` running `pytest` on push, using a dummy `ANTHROPIC_API_KEY` value so mocked tests run in CI without a real key or cost.

### Database migrations and backups

SQLite has no built-in migration tool — use Alembic from Phase 1 onward, even though the schema starts small. Retrofitting migrations onto a database that already holds a term's worth of taught lesson content is far more painful than starting with them. Every schema change from Phase 6 onward is an Alembic revision, not a manual `ALTER TABLE`.

The `.db` file is the only copy of everything generated and taught. Document in the README: back it up before any migration, and if deployed to a platform with an ephemeral filesystem (some free tiers), it must live on a persistent volume, not local container storage that resets on redeploy.

### CORS and health checks

CORS in `main.py` allows only the known frontend origin(s) — never `*`. A `GET /api/health` route returns `{"status": "ok"}` for uptime checks and the deployment platform's health probe.

### Dependency pinning

`requirements.txt` and `package.json` pin exact or minimum-safe versions (`fastapi==0.11x`, not a bare `fastapi`), so a clone six months from now installs what was actually tested, not whatever happens to be latest.

---

## README Requirements

The `README.md` must include:

1. What MathsAI is and what it does
2. Tech stack overview
3. Local setup instructions (clone, install, `.env`, seed, run)
4. Docker setup instructions
5. Deployment instructions for Railway or Render
6. API route reference
7. How to force-refresh cached content
8. How to add new curriculum topics
9. Network access setup — Tailscale instructions, or password auth setup if public hosting was chosen
10. How to run the test suite locally and in CI
11. How database migrations work (Alembic commands: revision, upgrade, downgrade) and the backup step to take before running one

---

## Final Note to Claude Code

This system is being built by an AI Engineer with a First Class BEng in Software Engineering and a Distinction MSc in AI who is also training to be a secondary mathematics teacher. He understands the code deeply and will review every decision. Do not cut corners, do not skip error handling, do not produce placeholder stubs without flagging them clearly. Build it properly from the start. Ask before assuming on anything architectural. Surface trade-offs where they exist.
