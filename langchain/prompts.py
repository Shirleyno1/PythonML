from langchain_core.prompts import ChatPromptTemplate

from langchain.models import model
from observability.tracing import langsmith_run_config

prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        "You are an expert {domain} assistant."
    ),
    (
        "human",
        "{question}"
    )
])

chain = (prompt | model).with_config(langsmith_run_config("prompt"))


def main() -> None:
    response = chain.invoke({"domain": "AI", "question": "What is RAG?"})
    print(response.content)


if __name__ == "__main__":
    main()
