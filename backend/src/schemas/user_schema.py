import uuid
from datetime import datetime

from pydantic import BaseModel


class UserResponse(BaseModel):
    id: uuid.UUID
    spotify_id: str
    created_at: datetime

    model_config = {"from_attributes": True}
