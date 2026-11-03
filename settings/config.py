import os
from collections.abc import MutableMapping

from dotenv import load_dotenv

load_dotenv()


def configure_langsmith(environ: MutableMapping[str, str]) -> bool:
    tracing_value = environ.get(
        "LANGSMITH_TRACING",
        environ.get("LANGSMITH_TRACKING", "false"),
    )
    tracing_enabled = tracing_value.strip().lower() in {"1", "true", "yes", "on"}
    api_key = environ.get("LANGSMITH_API_KEY")

    if tracing_enabled and not api_key:
        raise ValueError(
            "LANGSMITH_API_KEY is required when LangSmith tracing is enabled."
        )

    environ["LANGSMITH_TRACING"] = str(tracing_enabled).lower()
    if tracing_enabled:
        environ.setdefault("LANGSMITH_PROJECT", "ai-post-management")
    return tracing_enabled


_langsmith_tracing_enabled = configure_langsmith(os.environ)


class Settings:
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

    LANGSMITH_TRACING = _langsmith_tracing_enabled
    LANGSMITH_TRACKING = LANGSMITH_TRACING
    LANGSMITH_API_KEY = os.getenv("LANGSMITH_API_KEY")
    LANGSMITH_PROJECT = os.getenv("LANGSMITH_PROJECT", "ai-post-management")


settings = Settings()
