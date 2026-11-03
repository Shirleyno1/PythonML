from pydantic import BaseModel

from langchain.models import model
from observability.tracing import langsmith_run_config


class Intent(BaseModel):
    intent: str
    query: str | None = None


structured_model = model.with_structured_output(Intent).with_config(
    langsmith_run_config("structured-output")
)


def main() -> None:
    result = structured_model.invoke("Find Italian restaurants")
    print(result.model_dump())


if __name__ == "__main__":
    main()
