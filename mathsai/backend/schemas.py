from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class TopicRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    key_stage: str
    strand: str
    topic_name: str
    edexcel_ref: Optional[str] = None
    difficulty_band: Optional[str] = None
    created_at: datetime
