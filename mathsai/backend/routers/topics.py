"""Topic browsing and curriculum structure routes (CLAUDE.md API Routes —
Topics Router)."""

import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import LessonCache, Topic
from schemas import TopicRead

logger = logging.getLogger("mathsai")

router = APIRouter(prefix="/api/topics", tags=["topics"])


def _cached_lesson_topic_ids(db: Session, topic_ids: List[int]) -> set:
    """One bulk query for whether each topic already has a cached lesson —
    never generate content just to answer this, and never N+1 per topic."""
    if not topic_ids:
        return set()
    rows = (
        db.query(LessonCache.topic_id)
        .filter(LessonCache.topic_id.in_(topic_ids))
        .all()
    )
    return {row[0] for row in rows}


def _to_read(topic: Topic, cached_ids: set) -> TopicRead:
    return TopicRead(
        id=topic.id,
        key_stage=topic.key_stage,
        strand=topic.strand,
        topic_name=topic.topic_name,
        edexcel_ref=topic.edexcel_ref,
        difficulty_band=topic.difficulty_band,
        created_at=topic.created_at,
        has_cached_lesson=topic.id in cached_ids,
    )


@router.get("/ks3", response_model=List[TopicRead])
def list_ks3_topics(db: Session = Depends(get_db)):
    topics = (
        db.query(Topic)
        .filter(Topic.key_stage == "KS3")
        .order_by(Topic.strand, Topic.topic_name)
        .all()
    )
    cached_ids = _cached_lesson_topic_ids(db, [t.id for t in topics])
    return [_to_read(t, cached_ids) for t in topics]


@router.get("/ks4", response_model=List[TopicRead])
def list_ks4_topics(db: Session = Depends(get_db)):
    topics = (
        db.query(Topic)
        .filter(Topic.key_stage == "KS4")
        .order_by(Topic.strand, Topic.topic_name)
        .all()
    )
    cached_ids = _cached_lesson_topic_ids(db, [t.id for t in topics])
    return [_to_read(t, cached_ids) for t in topics]


@router.get("/search", response_model=List[TopicRead])
def search_topics(q: str, db: Session = Depends(get_db)):
    topics = (
        db.query(Topic)
        .filter(Topic.topic_name.ilike(f"%{q}%"))
        .order_by(Topic.key_stage, Topic.strand, Topic.topic_name)
        .all()
    )
    logger.info("Topic search q=%r results=%d", q, len(topics))
    cached_ids = _cached_lesson_topic_ids(db, [t.id for t in topics])
    return [_to_read(t, cached_ids) for t in topics]


@router.get("", response_model=List[TopicRead])
def list_topics(db: Session = Depends(get_db)):
    topics = (
        db.query(Topic)
        .order_by(Topic.key_stage, Topic.strand, Topic.topic_name)
        .all()
    )
    cached_ids = _cached_lesson_topic_ids(db, [t.id for t in topics])
    return [_to_read(t, cached_ids) for t in topics]


@router.get("/{topic_id}", response_model=TopicRead)
def get_topic(topic_id: int, db: Session = Depends(get_db)):
    topic = db.query(Topic).filter(Topic.id == topic_id).first()
    if topic is None:
        logger.error("Topic view failed: topic_id=%d not found endpoint=/api/topics/{id}", topic_id)
        raise HTTPException(status_code=404, detail=f"Topic {topic_id} not found")
    logger.info("Topic viewed topic_id=%d", topic_id)
    cached_ids = _cached_lesson_topic_ids(db, [topic.id])
    return _to_read(topic, cached_ids)
