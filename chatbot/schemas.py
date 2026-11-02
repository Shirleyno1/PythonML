from uuid import UUID

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    conversation_id: UUID
    message: str = Field(min_length=1, max_length=10_000)

class ChatResponse(BaseModel):
    answer: str