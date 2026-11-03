from langchain_core.runnables import RunnableLambda

from observability.tracing import langsmith_run_config


def clean_text(text: str) -> str:
    return text.strip().lower()


def main() -> None:
    cleaner = RunnableLambda(clean_text).with_config(
        langsmith_run_config("runnable")
    )
    result = cleaner.invoke("    HELLO WORLD  ")
    print(result)


if __name__ == "__main__":
    main()
