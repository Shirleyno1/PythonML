from pydantic import BaseModel, Field


class AIResponse(BaseModel):
    title: str = Field(description="The title of the answer")

    summary: str = Field(description="A concise summary of the answer")

    key_points: list[str] = Field(description="The keypoints of the answer")
