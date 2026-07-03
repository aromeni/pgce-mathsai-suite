"""Lesson generation and retrieval routes (CLAUDE.md API Routes — Lessons
Router)."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from schemas import LessonRead
from services import cache_service
from services.ai_service import AIGenerationError

router = APIRouter(prefix="/api/lessons", tags=["lessons"])


@router.get("/{topic_id}", response_model=LessonRead)
def get_lesson(topic_id: int, db: Session = Depends(get_db)):
    try:
        return cache_service.get_lesson(db, topic_id)
    except cache_service.TopicNotFoundError:
        raise HTTPException(status_code=404, detail=f"Topic {topic_id} not found")
    except AIGenerationError as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@router.post("/{topic_id}/refresh", response_model=LessonRead)
def refresh_lesson(topic_id: int, db: Session = Depends(get_db)):
    try:
        return cache_service.get_lesson(db, topic_id, force_refresh=True)
    except cache_service.TopicNotFoundError:
        raise HTTPException(status_code=404, detail=f"Topic {topic_id} not found")
    except AIGenerationError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
