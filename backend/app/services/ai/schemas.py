from pydantic import BaseModel, Field

from app.schemas.base import StrictSchema


class AIChatRequest(StrictSchema):
    message: str = Field(min_length=1, max_length=4000)
    conversation_id: int | None = None


class AISource(BaseModel):
    type: str
    id: int
    title: str
    url: str | None = None


class AIRetrieveRequest(BaseModel):
    query: str = Field(min_length=1, max_length=4000)
    limit: int = Field(default=16, ge=1, le=50)
    source_types: list[str] | None = None


class AIConversationCreate(BaseModel):
    title: str | None = Field(default=None, max_length=200)
