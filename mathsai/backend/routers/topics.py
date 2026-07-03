"""Topic browsing and curriculum structure routes (CLAUDE.md API Routes —
Topics Router)."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import Topic
from schemas import TopicRead

router = APIRouter(prefix="/api/topics", tags=["topics"])


@router.get("/ks3", response_model=List[TopicRead])
def list_ks3_topics(db: Session = Depends(get_db)):
    return (
        db.query(Topic)
        .filter(Topic.key_stage == "KS3")
        .order_by(Topic.strand, Topic.topic_name)
        .all()
    )


@router.get("/ks4", response_model=List[TopicRead])
def list_ks4_topics(db: Session = Depends(get_db)):
    return (
        db.query(Topic)
        .filter(Topic.key_stage == "KS4")
        .order_by(Topic.strand, Topic.topic_name)
        .all()
    )


@router.get("/search", response_model=List[TopicRead])
def search_topics(q: str, db: Session = Depends(get_db)):
    return (
        db.query(Topic)
        .filter(Topic.topic_name.ilike(f"%{q}%"))
        .order_by(Topic.key_stage, Topic.strand, Topic.topic_name)
        .all()
    )


@router.get("", response_model=List[TopicRead])
def list_topics(db: Session = Depends(get_db)):
    return (
        db.query(Topic)
        .order_by(Topic.key_stage, Topic.strand, Topic.topic_name)
        .all()
    )


@router.get("/{topic_id}", response_model=TopicRead)
def get_topic(topic_id: int, db: Session = Depends(get_db)):
    topic = db.query(Topic).filter(Topic.id == topic_id).first()
    if topic is None:
        raise HTTPException(status_code=404, detail=f"Topic {topic_id} not found")
    return topic
