from pydantic import BaseModel

from langchain.models import model


class Intent(BaseModel):
    intent: str
    query: str | None = None


structured_model = model.with_structured_output(
    Intent
)

result = structured_model.invoke(
    "Find Italian restaurants"
)

print(result.intent)
print(result.query)