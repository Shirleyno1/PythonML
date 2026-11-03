from langchain_core.messages import SystemMessage, HumanMessage

from langchain.models import model
from observability.tracing import langsmith_run_config


def main() -> None:
    messages = [
        SystemMessage(content="You are an AI assistant."),
        HumanMessage(content="What is TAG?"),
    ]
    traced_model = model.with_config(langsmith_run_config("messages"))
    response = traced_model.invoke(messages)
    print(response.content)


if __name__ == "__main__":
    main()
