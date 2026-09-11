from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from database import Base


class Topic(Base):
    __tablename__ = "topics"

    id = Column(Integer, primary_key=True, index=True)
    key_stage = Column(String, nullable=False)  # 'KS3' or 'KS4'
    strand = Column(String, nullable=False)  # 'Number', 'Algebra', 'Geometry', 'Statistics'
    topic_name = Column(String, nullable=False)
    edexcel_ref = Column(String, nullable=True)
    difficulty_band = Column(String, nullable=True)  # 'Foundation', 'Higher', or 'Both'
    # KS3 spans Years 7-9 and KS4 Years 10-11, which is far too wide to pitch
    # content against — "KS3 fractions" could be Year 7 equivalent fractions
    # or Year 9 dividing mixed numbers in context. A default year per topic
    # gives generation something concrete to aim at; it is editable.
    year_group = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    lesson_cache = relationship("LessonCache", back_populates="topic", uselist=False)
    question_caches = relationship("QuestionCache", back_populates="topic")
    teaching_logs = relationship("TeachingLog", back_populates="topic")
    regeneration_logs = relationship("RegenerationLog", back_populates="topic")


class LessonCache(Base):
    __tablename__ = "lesson_cache"

    id = Column(Integer, primary_key=True, index=True)
    topic_id = Column(Integer, ForeignKey("topics.id"), nullable=False)

    # Whole validated lesson as one JSON document. The lesson schema is
    # expected to keep evolving (it has already gone from four flat fields to
    # a full teaching sequence), and a column per section would mean a
    # migration for every pedagogical change. `schema_version` records which
    # shape a row was written under.
    content = Column(Text, nullable=True)
    schema_version = Column(Integer, nullable=False, default=1)

    # Schema version 1 columns. Retained, not dropped: they hold real
    # generated content that is still perfectly usable to teach from, and
    # deleting it to tidy the table would cost money to replace.
    lesson_notes = Column(Text, nullable=True)
    worked_examples = Column(Text, nullable=True)  # JSON array
    key_vocabulary = Column(Text, nullable=True)  # JSON array
    common_errors = Column(Text, nullable=True)  # JSON array

    generated_at = Column(DateTime, default=datetime.utcnow)
    model_used = Column(String, nullable=True)
    reviewed = Column(Boolean, nullable=False, default=False)
    reviewed_at = Column(DateTime, nullable=True)

    topic = relationship("Topic", back_populates="lesson_cache")


class QuestionCache(Base):
    __tablename__ = "question_cache"

    id = Column(Integer, primary_key=True, index=True)
    topic_id = Column(Integer, ForeignKey("topics.id"), nullable=False)
    difficulty = Column(String, nullable=False)  # 'Fluency', 'Reasoning', 'Problem-solving'
    questions = Column(Text, nullable=False)  # JSON array of question objects
    generated_at = Column(DateTime, default=datetime.utcnow)
    model_used = Column(String, nullable=True)
    reviewed = Column(Boolean, nullable=False, default=False)
    reviewed_at = Column(DateTime, nullable=True)

    topic = relationship("Topic", back_populates="question_caches")


class TeachingLog(Base):
    __tablename__ = "teaching_log"

    id = Column(Integer, primary_key=True, index=True)
    topic_id = Column(Integer, ForeignKey("topics.id"), nullable=False)
    taught_date = Column(Date, nullable=False)
    class_label = Column(String, nullable=True)  # e.g. 'Year 9 Set 2'
    notes = Column(Text, nullable=True)

    topic = relationship("Topic", back_populates="teaching_logs")


class RegenerationLog(Base):
    __tablename__ = "regeneration_log"

    id = Column(Integer, primary_key=True, index=True)
    topic_id = Column(Integer, ForeignKey("topics.id"), nullable=False)
    content_type = Column(String, nullable=False)  # 'lesson' or 'question:<difficulty>'
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)

    topic = relationship("Topic", back_populates="regeneration_logs")
