"""Question generation and retrieval routes (CLAUDE.md API Routes —
Questions Router).

`difficulty` is typed as the `DifficultyTier` Literal, so FastAPI rejects
any other value with a 422 before this code ever runs — satisfying
CLAUDE.md's "Invalid difficulty tier -> return 422 with validation error"
without a manual check here.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from schemas import DifficultyTier, QuestionItem, QuestionSetStatus
from services import cache_service
from services.ai_service import AIGenerationError

router = APIRouter(prefix="/api/questions", tags=["questions"])


@router.get("/{topic_id}/{difficulty}", response_model=List[QuestionItem])
def get_questions(topic_id: int, difficulty: DifficultyTier, db: Session = Depends(get_db)):
    try:
        return cache_service.get_questions(db, topic_id, difficulty)
    except cache_service.TopicNotFoundError:
        raise HTTPException(status_code=404, detail=f"Topic {topic_id} not found")
    except AIGenerationError as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@router.post("/{topic_id}/{difficulty}/refresh", response_model=List[QuestionItem])
def refresh_questions(topic_id: int, difficulty: DifficultyTier, db: Session = Depends(get_db)):
    try:
        return cache_service.get_questions(db, topic_id, difficulty, force_refresh=True)
    except cache_service.TopicNotFoundError:
        raise HTTPException(status_code=404, detail=f"Topic {topic_id} not found")
    except AIGenerationError as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@router.get("/{topic_id}/{difficulty}/status", response_model=Optional[QuestionSetStatus])
def get_questions_status(topic_id: int, difficulty: DifficultyTier, db: Session = Depends(get_db)):
    """Read-only metadata (reviewed/generated_at) for the `reviewed` marker
    in the UI — never triggers generation, unlike the main GET route above."""
    try:
        return cache_service.get_questions_status(db, topic_id, difficulty)
    except cache_service.TopicNotFoundError:
        raise HTTPException(status_code=404, detail=f"Topic {topic_id} not found")


@router.post("/{topic_id}/{difficulty}/review", response_model=QuestionSetStatus)
def mark_questions_reviewed(topic_id: int, difficulty: DifficultyTier, db: Session = Depends(get_db)):
    try:
        return cache_service.mark_questions_reviewed(db, topic_id, difficulty)
    except cache_service.TopicNotFoundError:
        raise HTTPException(status_code=404, detail=f"Topic {topic_id} not found")
    except cache_service.ContentNotCachedError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
