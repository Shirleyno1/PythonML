from pydantic import BaseModel, ConfigDict, Field


class AgUiRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    message: str
    thread_id: str = Field(alias="threadId")
    run_id: str = Field(alias="runId")
