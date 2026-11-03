from langchain.models import model
from langchain.prompts import prompt
from observability.tracing import langsmith_run_config

chain = (prompt | model).with_config(langsmith_run_config("chain"))


def main() -> None:
    response = chain.invoke(
        {
            "domain": "AI",
            "question": "What is RAG?",
        }
    )
    print(response.content)


if __name__ == "__main__":
    main()
