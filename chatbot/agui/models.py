from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AgUiRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    message: str = Field(min_length=1, max_length=10_000)
    thread_id: UUID = Field(alias="threadId")
    run_id: str = Field(alias="runId", min_length=1, max_length=128)
