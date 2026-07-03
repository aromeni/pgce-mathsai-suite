"""Question generation and retrieval routes (CLAUDE.md API Routes —
Questions Router).

`difficulty` is typed as the `DifficultyTier` Literal, so FastAPI rejects
any other value with a 422 before this code ever runs — satisfying
CLAUDE.md's "Invalid difficulty tier -> return 422 with validation error"
without a manual check here.
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from schemas import DifficultyTier, QuestionItem
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
