from functools import lru_cache
import os

from dotenv import load_dotenv
from openai import OpenAI

from ai_prompts import catalog, get_prompt
from chatbot.models import AIResponse
from chatbot.classifier import UserIntent
from observability.tracing import (
    ai_traceable,
    traced_openai,
    trace_intent_output,
    trace_message_input,
)

load_dotenv()


@lru_cache(maxsize=1)
def _get_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY must be configured to use AI features.")
    return traced_openai(OpenAI(api_key=api_key))


def generate_structured_response(
        message: str
) -> AIResponse:

    prompt = get_prompt(catalog.STRUCTURED_ANSWER)
    response = _get_client().responses.parse(
        model=prompt.model,
        input=prompt.to_messages(message=message),
        text_format=AIResponse
    )
    result = response.output_parsed
    print(f"Title is {result.title}\nSummary is {result.summary}")

    return result

@ai_traceable(
    name="AI Intent Classification",
    component="intent-classification",
    run_type="chain",
    process_inputs=trace_message_input,
    process_outputs=trace_intent_output,
)
def classify_message(message: str) -> UserIntent:
    prompt = get_prompt(catalog.INTENT_CLASSIFIER)
    response = _get_client().responses.parse(
        model=prompt.model,
        input=prompt.to_messages(message=message),
        text_format=UserIntent
    )
    result = response.output_parsed
    if result is None:
        raise RuntimeError("The intent classifier returned no result.")
    return result
