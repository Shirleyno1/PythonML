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


def configure_langsmith_prompts(environ: MutableMapping[str, str]) -> bool:
    value = environ.get("LANGSMITH_PROMPTS_ENABLED", "false")
    enabled = value.strip().lower() in {"1", "true", "yes", "on"}
    if enabled and not environ.get("LANGSMITH_API_KEY"):
        raise ValueError(
            "LANGSMITH_API_KEY is required when LANGSMITH_PROMPTS_ENABLED is on."
        )
    return enabled


_langsmith_tracing_enabled = configure_langsmith(os.environ)
_langsmith_prompts_enabled = configure_langsmith_prompts(os.environ)


class Settings:
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    # Used by every model call unless its LangSmith prompt names another model.
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5-mini")

    LANGSMITH_TRACING = _langsmith_tracing_enabled
    LANGSMITH_TRACKING = LANGSMITH_TRACING
    LANGSMITH_API_KEY = os.getenv("LANGSMITH_API_KEY")
    LANGSMITH_PROJECT = os.getenv("LANGSMITH_PROJECT", "ai-post-management")
    # Pull prompts (and their models) from LangSmith instead of ai_prompts/catalog.py.
    LANGSMITH_PROMPTS_ENABLED = _langsmith_prompts_enabled
    # A commit tag such as "production"; unset means each prompt's latest commit.
    LANGSMITH_PROMPT_TAG = os.getenv("LANGSMITH_PROMPT_TAG") or None


settings = Settings()
