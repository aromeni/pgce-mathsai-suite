from datetime import datetime
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
