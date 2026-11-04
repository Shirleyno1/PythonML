from collections.abc import Callable
from typing import Any, Literal, ParamSpec, TypeVar

from langsmith import traceable

from settings.config import settings

P = ParamSpec("P")
R = TypeVar("R")


def ai_traceable(
    *,
    name: str,
    component: str,
    run_type: Literal[
        "tool",
        "chain",
        "llm",
        "retriever",
        "embedding",
        "prompt",
        "parser",
    ],
    process_inputs: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
    process_outputs: Callable[[Any], Any] | None = None,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    return traceable(
        name=name,
        run_type=run_type,
        project_name=settings.LANGSMITH_PROJECT,
        tags=["pythonml", "ai", component],
        metadata={"component": component},
        enabled=settings.LANGSMITH_TRACING,
        process_inputs=process_inputs,
        process_outputs=process_outputs,
    )


def langsmith_run_config(
    component: str,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "run_name": f"langchain-{component}",
        "tags": ["pythonml", "langchain", component],
        "metadata": {
            "component": component,
            "project": settings.LANGSMITH_PROJECT,
            **(metadata or {}),
        },
    }


def trace_message_input(inputs: dict[str, Any]) -> dict[str, Any]:
    return {"message": inputs.get("message")}


def trace_ai_request_input(inputs: dict[str, Any]) -> dict[str, Any]:
    request = inputs.get("request")
    if isinstance(request, dict):
        message = request.get("message")
    else:
        message = getattr(request, "message", None)
    return {"message": message}


def trace_agent_input(inputs: dict[str, Any]) -> dict[str, Any]:
    return {
        "message": inputs.get("message"),
        "history": inputs.get("history", []),
    }


def trace_intent_output(output: Any) -> dict[str, Any]:
    if output is None:
        return {"classification": None}
    return output.model_dump()


def trace_ai_result(output: Any) -> dict[str, Any]:
    if not isinstance(output, dict):
        return {"result_type": type(output).__name__}

    summary = {
        key: output[key]
        for key in ("intent", "status")
        if key in output
    }
    if isinstance(output.get("results"), list):
        summary["result_count"] = len(output["results"])
    return summary or {"result_type": "dict"}


def trace_model_output(output: Any) -> dict[str, Any]:
    calls = [
        {
            "name": item.name,
            "arguments": item.arguments,
        }
        for item in getattr(output, "output", [])
        if getattr(item, "type", None) == "function_call"
    ]
    return {
        "output_text": getattr(output, "output_text", None),
        "tool_calls": calls,
    }


def trace_tool_input(inputs: dict[str, Any]) -> dict[str, Any]:
    arguments = dict(inputs.get("arguments") or {})
    arguments.pop("user_id", None)
    return {
        "tool_name": inputs.get("name"),
        "arguments": arguments,
    }


ENGAGEMENT_INPUT_FIELDS = (
    "post_id",
    "comment_id",
    "task_id",
    "comments_disabled",
    "points",
)
ENGAGEMENT_OUTPUT_FIELDS = (
    "id",
    "post_id",
    "comment_id",
    "task_id",
    "commentsDisabled",
    "thumbs_up",
    "thumbs_down",
    "my_reaction",
    "points",
    "points_awarded",
    "points_remaining",
    "total",
)
ENGAGEMENT_LIST_FIELDS = ("comments", "tasks", "history")


def trace_engagement_input(inputs: dict[str, Any]) -> dict[str, Any]:
    """Allowlist IDs and settings: user IDs and user-written text stay out of traces."""
    summary = {
        key: inputs[key]
        for key in ENGAGEMENT_INPUT_FIELDS
        if key in inputs
    }
    if "reaction" in inputs:
        reaction = inputs["reaction"]
        summary["reaction"] = getattr(reaction, "value", reaction)
    if isinstance(inputs.get("content"), str):
        summary["content_length"] = len(inputs["content"])
    return summary


def trace_engagement_output(output: Any) -> dict[str, Any]:
    if not isinstance(output, dict):
        return {"result_type": type(output).__name__}

    summary = {
        key: output[key]
        for key in ENGAGEMENT_OUTPUT_FIELDS
        if key in output
    }
    for key in ENGAGEMENT_LIST_FIELDS:
        if isinstance(output.get(key), list):
            summary[f"{key}_count"] = len(output[key])
    return summary


def engagement_traceable(name: str) -> Callable[[Callable[P, R]], Callable[P, R]]:
    return traceable(
        name=name,
        run_type="chain",
        project_name=settings.LANGSMITH_PROJECT,
        tags=["pythonml", "posts", "post-engagement"],
        metadata={"component": "post-engagement"},
        enabled=settings.LANGSMITH_TRACING,
        process_inputs=trace_engagement_input,
        process_outputs=trace_engagement_output,
    )
