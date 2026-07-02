import logging
import os
from contextlib import asynccontextmanager
from logging.handlers import RotatingFileHandler

from fastapi import Depends, FastAPI
from sqlalchemy import inspect
from sqlalchemy.orm import Session

from database import engine, get_db
from schemas import TopicRead
from services.curriculum import seed_topics
from models import Topic  # noqa: F401 — ensures models are registered on Base

LOG_DIR = os.path.join(os.path.dirname(__file__), "logs")
os.makedirs(LOG_DIR, exist_ok=True)

logger = logging.getLogger("mathsai")
logger.setLevel(logging.INFO)
_handler = RotatingFileHandler(
    os.path.join(LOG_DIR, "mathsai.log"), maxBytes=1_000_000, backupCount=3
)
_handler.setFormatter(
    logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
)
logger.addHandler(_handler)
logger.addHandler(logging.StreamHandler())


@asynccontextmanager
async def lifespan(app: FastAPI):
    inspector = inspect(engine)
    if "topics" not in inspector.get_table_names():
        logger.warning(
            "Database tables not found — run `alembic upgrade head` before starting the app."
        )
    else:
        db: Session = next(get_db())
        try:
            seed_topics(db)
        finally:
            db.close()
    yield


app = FastAPI(title="MathsAI", lifespan=lifespan)


@app.get("/api/topics", response_model=list[TopicRead])
def list_topics(db: Session = Depends(get_db)):
    logger.info("GET /api/topics")
    return db.query(Topic).order_by(Topic.key_stage, Topic.strand, Topic.topic_name).all()
