from datetime import date, datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, RootModel


class TopicRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    key_stage: str
    strand: str
    topic_name: str
    edexcel_ref: Optional[str] = None
    difficulty_band: Optional[str] = None
    created_at: datetime
    has_cached_lesson: bool = False


# --- AI-generated lesson content validation (CLAUDE.md AI Service Design) ---


class WorkedExample(BaseModel):
    title: str
    problem: str
    solution: str
    teaching_note: str


class VocabularyItem(BaseModel):
    term: str
    definition: str


class CommonError(BaseModel):
    error: str
    correction: str


class LessonSchema(BaseModel):
    lesson_notes: str
    worked_examples: List[WorkedExample]
    key_vocabulary: List[VocabularyItem]
    common_errors: List[CommonError]


# --- AI-generated question content validation ---

QuestionType = Literal["short_answer", "multiple_choice", "show_working", "exam_style"]


class QuestionItem(BaseModel):
    question_number: int
    type: QuestionType
    question_text: str
    options: Optional[List[str]] = None
    answer: str
    mark_scheme: str
    marks: int


class QuestionSetSchema(RootModel[List[QuestionItem]]):
    pass


# --- API response / request schemas (Phase 3 routers) ---


class LessonRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    topic_id: int
    lesson_notes: str
    worked_examples: List[WorkedExample]
    key_vocabulary: List[VocabularyItem]
    common_errors: List[CommonError]
    generated_at: datetime
    model_used: Optional[str] = None
    reviewed: bool
    reviewed_at: Optional[datetime] = None
    stale: bool = False


DifficultyTier = Literal["Foundation", "Developing", "Extending"]


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
