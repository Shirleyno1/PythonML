"""Resolves a prompt and its model: from LangSmith when enabled, else the local copy."""
import logging
import time
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from langchain_core._api import suppress_langchain_beta_warning
from langchain_core.load.load import load
from langchain_core.prompts import ChatPromptTemplate
from langsmith.utils import LangSmithNotFoundError

from ai_prompts.catalog import ALL_PROMPTS, PromptSpec
from settings.config import settings

logger = logging.getLogger(__name__)

# A prompt that failed to pull isn't asked for again until then, so a missing
# prompt or a LangSmith outage doesn't add a network call to every request.
FAILED_PULL_RETRY_SECONDS = 300
LANGSMITH_TIMEOUT_MS = 5_000

_ROLES = {"system": "system", "human": "user", "ai": "assistant"}
_retry_after: dict[str, float] = {}


@dataclass(frozen=True)
class ResolvedPrompt:
    spec: PromptSpec
    template: ChatPromptTemplate
    model: str
    source: str

    def to_messages(self, **variables: Any) -> list[dict[str, str]]:
        """The prompt as Responses API input messages."""
        known = {key: value for key, value in variables.items() if key in self.template.input_variables}
        return [
            {"role": _ROLES.get(message.type, message.type), "content": message.content}
            for message in self.template.format_messages(**known)
        ]

    def text(self) -> str:
        """The first message, for prompts that are plain text such as tool descriptions."""
        messages = self.to_messages()
        return messages[0]["content"] if messages else ""


def get_prompt(spec: PromptSpec) -> ResolvedPrompt:
    local = _local_prompt(spec)
    if not settings.LANGSMITH_PROMPTS_ENABLED:
        return local
    if time.monotonic() < _retry_after.get(spec.name, 0):
        return local
    try:
        return _pull_prompt(spec, local)
    except Exception as error:
        _retry_after[spec.name] = time.monotonic() + FAILED_PULL_RETRY_SECONDS
        if isinstance(error, LangSmithNotFoundError):
            # Optional prompts are expected to be missing until someone creates them.
            log = logger.debug if spec.optional else logger.warning
            log("Using the local %s prompt: LangSmith has no %s", spec.name, _identifier(spec))
        else:
            logger.warning("Using the local %s prompt; LangSmith gave: %s", spec.name, error)
        return local


def warm_prompts() -> None:
    """Pulls every prompt once, so the first requests don't wait on LangSmith."""
    if settings.LANGSMITH_PROMPTS_ENABLED:
        for spec in ALL_PROMPTS:
            get_prompt(spec)


def _local_prompt(spec: PromptSpec) -> ResolvedPrompt:
    return ResolvedPrompt(
        spec=spec,
        template=ChatPromptTemplate.from_messages(list(spec.messages)),
        model=spec.model or settings.OPENAI_MODEL,
        source="local",
    )


def _pull_prompt(spec: PromptSpec, local: ResolvedPrompt) -> ResolvedPrompt:
    # The LangSmith client caches this and refreshes it in the background.
    manifest = _client().pull_prompt_commit(_identifier(spec), include_model=True).manifest
    prompt_manifest, model_manifest = _split_manifest(manifest)
    # "core" loads prompt templates only, never a model or other code.
    with suppress_langchain_beta_warning():
        template = load(prompt_manifest, allowed_objects="core")
    if not isinstance(template, ChatPromptTemplate):
        raise ValueError(f"expected a chat prompt, got {type(template).__name__}")

    missing = set(template.input_variables) - set(local.template.input_variables)
    if missing:
        raise ValueError(
            f"it uses variables the app doesn't supply: {', '.join(sorted(missing))}; "
            f"available: {', '.join(local.template.input_variables) or 'none'}"
        )

    return ResolvedPrompt(
        spec=spec,
        template=template,
        model=_openai_model_name(spec, model_manifest) or local.model,
        source="langsmith",
    )


def _identifier(spec: PromptSpec) -> str:
    if settings.LANGSMITH_PROMPT_TAG:
        return f"{spec.name}:{settings.LANGSMITH_PROMPT_TAG}"
    return spec.name


def _split_manifest(manifest: dict) -> tuple[dict, dict | None]:
    """A prompt saved with a model is stored as prompt | model."""
    if manifest.get("id", [])[-1:] == ["RunnableSequence"]:
        kwargs = manifest.get("kwargs", {})
        return kwargs["first"], kwargs.get("last")
    return manifest, None


def _openai_model_name(spec: PromptSpec, model_manifest: dict | None) -> str | None:
    if model_manifest is None or not spec.uses_model:
        return None
    # A model saved with settings such as temperature is wrapped in a binding.
    while model_manifest.get("id", [])[-1:] == ["RunnableBinding"]:
        model_manifest = model_manifest.get("kwargs", {}).get("bound", {})
    if model_manifest.get("id", [])[-1:] != ["ChatOpenAI"]:
        logger.warning(
            "Ignoring the model saved with %s: only OpenAI models are supported", spec.name
        )
        return None
    kwargs = model_manifest.get("kwargs", {})
    return kwargs.get("model_name") or kwargs.get("model")


@lru_cache(maxsize=1)
def _client():
    from langsmith import Client

    return Client(api_key=settings.LANGSMITH_API_KEY, timeout_ms=LANGSMITH_TIMEOUT_MS)
