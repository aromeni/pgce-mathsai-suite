"""Teaching history and progress tracking routes (CLAUDE.md API Routes —
Progress Router). No AI dependency — implemented in full in Phase 3
(confirmed with the user, since Phase 6 is scoped to the frontend Progress
page/UI built on top of this API, not the API itself)."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import TeachingLog, Topic
from schemas import TeachingLogCreate, TeachingLogRead

router = APIRouter(prefix="/api/progress", tags=["progress"])


@router.get("", response_model=List[TeachingLogRead])
def list_progress(db: Session = Depends(get_db)):
    return db.query(TeachingLog).order_by(TeachingLog.taught_date.desc()).all()


@router.post("", response_model=TeachingLogRead, status_code=201)
def log_taught(entry: TeachingLogCreate, db: Session = Depends(get_db)):
    topic = db.query(Topic).filter(Topic.id == entry.topic_id).first()
    if topic is None:
        raise HTTPException(status_code=404, detail=f"Topic {entry.topic_id} not found")

    row = TeachingLog(**entry.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.get("/topic/{topic_id}", response_model=List[TeachingLogRead])
def get_topic_progress(topic_id: int, db: Session = Depends(get_db)):
    topic = db.query(Topic).filter(Topic.id == topic_id).first()
    if topic is None:
        raise HTTPException(status_code=404, detail=f"Topic {topic_id} not found")

    return (
        db.query(TeachingLog)
        .filter(TeachingLog.topic_id == topic_id)
        .order_by(TeachingLog.taught_date.desc())
        .all()
    )


@router.delete("/{log_id}", status_code=204)
def delete_progress(log_id: int, db: Session = Depends(get_db)):
    row = db.query(TeachingLog).filter(TeachingLog.id == log_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail=f"Progress log entry {log_id} not found")

    db.delete(row)
    db.commit()
