from typing import Literal

from pydantic import BaseModel, Field


class UserIntent(BaseModel):

    intent: Literal[
        "search",
        "create",
        "delete",
        "general"
    ]

    query: str = Field(
        default=None,
        description="Search query if the user wants to search"
    )

    confidence: float = Field(
        ge=0,
        le=1,
        description="Confidence score of the answer from 0 to 1"
    )
