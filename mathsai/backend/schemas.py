from datetime import date, datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, RootModel

# Bumped whenever the shape of generated lesson content changes. Rows cached
# under an older version stay readable and are served as-is with an
# `outdated_format` flag — never silently regenerated, because that would
# spend Anthropic credits across every topic already generated without
# anyone asking for it (CLAUDE.md Production Hardening — Cost guardrails).
LESSON_SCHEMA_VERSION = 2

# The three tiers of independent practice ("You do"). Named for Edexcel's
# Assessment Objectives — AO1 fluency, AO2 reasoning, AO3 problem-solving —
# rather than the previous Foundation/Developing/Extending. Two reasons:
# "Foundation" already means Edexcel's tier of entry in `topics.
# difficulty_band`, so the same word carried two meanings in one database;
# and these names say what the pupil actually does, where "Developing" said
# only that it was harder than the last one.
PracticeTier = Literal["Fluency", "Reasoning", "Problem-solving"]
DifficultyTier = PracticeTier  # kept as the router-facing alias


class TopicRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    key_stage: str
    strand: str
    topic_name: str
    edexcel_ref: Optional[str] = None
    difficulty_band: Optional[str] = None
    year_group: Optional[int] = None
    created_at: datetime
    has_cached_lesson: bool = False


# --- Lesson content: the teaching sequence ------------------------------
#
# The lesson is a sequence to teach from, not a reference document. It
# follows gradual release — starter, then I do (modelled), We do (guided),
# then You do, which is the tiered question sets rather than a fourth block
# here. Keeping "You do" out of the lesson avoids generating practice
# questions twice in two different shapes.


class TopicIntroduction(BaseModel):
    what_it_is: str
    why_it_matters: str
    prior_knowledge_needed: List[str]
    leads_on_to: List[str]
    learning_objectives: List[str]
    success_criteria: List[str]


class StarterQuestion(BaseModel):
    question: str
    answer: str
    # Which earlier skill this retrieves. The starter rehearses the
    # prerequisites for today's topic, not today's topic itself.
    prerequisite: str
    tier: PracticeTier


class Starter(BaseModel):
    retrieval_focus: str
    questions: List[StarterQuestion]


class ModelledStep(BaseModel):
    """One step of an "I do" example.

    `working` is what goes on the board; `narration` is what you say while
    writing it. Splitting them is the point — narrating the reasoning is
    what makes modelling different from demonstrating.
    """

    working: str
    narration: str


class ModelledExample(BaseModel):
    title: str
    problem: str
    steps: List[ModelledStep]
    key_teaching_point: str
    requires_diagram: bool = False
    diagram_description: Optional[str] = None


class GuidedExample(BaseModel):
    """One "We do" example, faded.

    `scaffolded_working` shows the early steps completed and later ones left
    open; `faded_from_step` records where support stops. Fading progressively
    across examples is also the SEND adaptation — same task, same goal,
    different amount of support withdrawn.
    """

    title: str
    problem: str
    scaffolded_working: str
    faded_from_step: int
    questions_to_ask: List[str]
    full_answer: str
    requires_diagram: bool = False
    diagram_description: Optional[str] = None


class VocabularyItem(BaseModel):
    term: str
    definition: str
    # Mathematics reuses ordinary words with different meanings — product,
    # mean, table, power, root, face, volume, odd, similar. A pupil who knows
    # the everyday sense is actively misled, which bites hardest for EAL
    # learners. Optional so lessons cached under schema v1 still validate.
    everyday_meaning: Optional[str] = None
    notation: Optional[str] = None


class CommonError(BaseModel):
    error: str
    # A misconception you can anticipate is worth more than one you can only
    # name after the fact.
    why_it_happens: Optional[str] = None
    correction: str
    address_at: Optional[str] = None


# --- Adaptive teaching --------------------------------------------------
#
# Teachers' Standard 5. The governing principle, stated in the prompt as
# well as here: same learning goal, different route in — not different,
# easier work.


class Scaffold(BaseModel):
    barrier: str
    scaffold: str
    # A scaffold that never comes off becomes a ceiling, so the removal
    # condition is a required part of proposing one.
    remove_when: str


class ConcreteRepresentation(BaseModel):
    """Concrete-Pictorial-Abstract. Named resource and the bridge back to
    abstract notation — "use manipulatives" on its own is not teaching."""

    resource: str
    how_to_use: str
    bridge_to_abstract: str


class FalseFriend(BaseModel):
    word: str
    everyday_meaning: str
    maths_meaning: str


class Tier2Word(BaseModel):
    """Academic vocabulary that sinks word problems — altogether, remaining,
    share, exceeds, respectively."""

    word: str
    meaning_in_context: str


class RewordedProblem(BaseModel):
    original: str
    reworded: str
    # The equation or calculation both versions lead to. Requiring it makes a
    # change in mathematical demand visible at a glance — the first live
    # sample quietly turned "4n - 7 = 2n - 33" into "4n - 7 = n", which is a
    # different and easier problem. An asserted constraint the model can
    # silently break is worth less than one it has to show working for.
    same_maths_because: Optional[str] = None


class LanguageSupport(BaseModel):
    tier_2_vocabulary: List[Tier2Word]
    false_friends: List[FalseFriend]
    sentence_stems: List[str]
    # Reduced linguistic load, identical mathematical demand.
    reduced_language_versions: List[RewordedProblem]


class AdaptiveTeaching(BaseModel):
    scaffolds: List[Scaffold]
    concrete_representations: List[ConcreteRepresentation]
    language_support: LanguageSupport
    # Adaptive teaching runs upward too: depth on the same content rather
    # than acceleration onto next year's topic.
    stretch: List[str]


class ExitTicketQuestion(BaseModel):
    question: str
    answer: str
    checks: str


# --- Per-call fragments -------------------------------------------------
#
# Lesson content is generated by three concurrent API calls and merged into
# one cached row. Each fragment is validated on its own so a failure names
# the part that actually failed.


class LessonCoreSchema(BaseModel):
    topic_introduction: TopicIntroduction
    i_do: List[ModelledExample]
    we_do: List[GuidedExample]


class LessonSupportSchema(BaseModel):
    starter: Starter
    key_vocabulary: List[VocabularyItem]
    common_errors: List[CommonError]
    plenary: List[ExitTicketQuestion]


class AdaptiveSchema(BaseModel):
    adaptive_teaching: AdaptiveTeaching


class LessonSchema(BaseModel):
    """The merged result of all three fragments."""

    topic_introduction: TopicIntroduction
    starter: Starter
    i_do: List[ModelledExample]
    we_do: List[GuidedExample]
    key_vocabulary: List[VocabularyItem]
    common_errors: List[CommonError]
    adaptive_teaching: AdaptiveTeaching
    plenary: List[ExitTicketQuestion]


# --- Legacy lesson content (schema_version 1) ---------------------------


class LegacyWorkedExample(BaseModel):
    title: str
    problem: str
    solution: str
    teaching_note: str


# --- Question content ---------------------------------------------------

QuestionType = Literal["short_answer", "multiple_choice", "show_working", "exam_style"]


class QuestionItem(BaseModel):
    question_number: int
    type: QuestionType
    question_text: str
    options: Optional[List[str]] = None
    answer: str
    mark_scheme: str
    marks: int
    # The misconception this question is built to expose. For multiple
    # choice, the distractor that catches it — which turns a guessing
    # exercise into a diagnostic one.
    misconception_targeted: Optional[str] = None
    # A text model cannot draw. Rather than emit "in the diagram below" with
    # no diagram — a question that looks fine on screen and is unanswerable
    # once printed — it flags what needs drawing.
    requires_diagram: bool = False
    diagram_description: Optional[str] = None
    command_word: Optional[str] = None
    calculator_allowed: Optional[bool] = None


class QuestionSetSchema(RootModel[List[QuestionItem]]):
    pass


# --- API response / request schemas -------------------------------------


class LessonRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    topic_id: int
    schema_version: int = LESSON_SCHEMA_VERSION
    # True when this row was generated under an older schema version. It is
    # still served and still usable; the UI offers regeneration rather than
    # doing it automatically.
    outdated_format: bool = False

    # Current format
    topic_introduction: Optional[TopicIntroduction] = None
    starter: Optional[Starter] = None
    i_do: Optional[List[ModelledExample]] = None
    we_do: Optional[List[GuidedExample]] = None
    adaptive_teaching: Optional[AdaptiveTeaching] = None
    plenary: Optional[List[ExitTicketQuestion]] = None

    # Present in both formats
    key_vocabulary: List[VocabularyItem] = []
    common_errors: List[CommonError] = []

    # Legacy format only
    lesson_notes: Optional[str] = None
    worked_examples: Optional[List[LegacyWorkedExample]] = None

    generated_at: datetime
    model_used: Optional[str] = None
    reviewed: bool
    reviewed_at: Optional[datetime] = None
    stale: bool = False


class QuestionSetStatus(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    topic_id: int
    difficulty: DifficultyTier
    generated_at: Optional[datetime] = None
    model_used: Optional[str] = None
    reviewed: bool = False
    reviewed_at: Optional[datetime] = None


class TeachingLogCreate(BaseModel):
    topic_id: int
    taught_date: date
    class_label: Optional[str] = None
    notes: Optional[str] = None


class TeachingLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    topic_id: int
    taught_date: date
    class_label: Optional[str] = None
    notes: Optional[str] = None
