import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import httpx
from langsmith import traceable, tracing_context
from langsmith.schemas import Example, Run
from openai import AsyncOpenAI

from observability.tracing import (
    trace_agent_input,
    trace_ai_request_input,
    trace_ai_result,
    trace_model_output,
    trace_tool_input,
    traced_openai,
)
from settings.config import settings
from evaluation import intent_dataset
from evaluation.run_evaluation import intent_accuracy, run_langsmith_evaluation


def test_ai_request_trace_keeps_only_the_message():
    request = SimpleNamespace(message="find a post")

    assert trace_ai_request_input(
        {"request": request, "user": object(), "session": object()}
    ) == {"message": "find a post"}


def test_agent_trace_excludes_user_id_and_keeps_context():
    history = [{"role": "user", "content": "previous question"}]

    assert trace_agent_input(
        {
            "message": "current question",
            "user_id": "private-user-id",
            "history": history,
        }
    ) == {"message": "current question", "history": history}


def test_tool_trace_excludes_internal_user_id():
    assert trace_tool_input(
        {
            "name": "search_posts",
            "arguments": {"query": "python", "user_id": "private-user-id"},
        }
    ) == {
        "tool_name": "search_posts",
        "arguments": {"query": "python"},
    }


def test_ai_result_trace_summarizes_search_results():
    assert trace_ai_result(
        {
            "intent": "search",
            "query": "private query",
            "results": [{"content": "private post"}],
        }
    ) == {"intent": "search", "result_count": 1}


def test_model_trace_records_tool_decisions_and_text():
    response = SimpleNamespace(
        output=[
            SimpleNamespace(
                type="function_call",
                name="search_posts",
                arguments='{"query":"python"}',
            )
        ],
        output_text="Here are the posts.",
    )

    assert trace_model_output(response) == {
        "output_text": "Here are the posts.",
        "tool_calls": [
            {"name": "search_posts", "arguments": '{"query":"python"}'}
        ],
    }


def test_intent_evaluator_compares_prediction_to_reference():
    run = Run(
        id=uuid4(),
        trace_id=uuid4(),
        name="intent-classifier",
        start_time=datetime.now(timezone.utc),
        run_type="llm",
        outputs={"intent": "search"},
    )
    example = Example(id=uuid4(), outputs={"intent": "search"})

    assert intent_accuracy(run, example) == {
        "key": "intent_accuracy",
        "score": True,
    }


def test_langsmith_evaluation_uses_local_intent_dataset(monkeypatch):
    captured = {}

    def fake_evaluate(target, **kwargs):
        captured["target"] = target
        captured.update(kwargs)
        return "completed"

    monkeypatch.setenv("LANGSMITH_API_KEY", "test-key")
    monkeypatch.setattr("evaluation.run_evaluation.evaluate", fake_evaluate)

    assert run_langsmith_evaluation() == "completed"
    assert len(captured["data"]) == len(intent_dataset.TEST_CASES)
    assert captured["evaluators"] == [intent_accuracy]
    assert captured["metadata"] == {"component": "ai-intent-classification"}


OPENAI_RESPONSE = {
    "id": "resp_1",
    "object": "response",
    "created_at": 0,
    "status": "completed",
    "model": "gpt-5-mini-2025-08-07",
    "output": [{
        "type": "message",
        "id": "msg_1",
        "status": "completed",
        "role": "assistant",
        "content": [{"type": "output_text", "text": "Hi", "annotations": []}],
    }],
    "parallel_tool_calls": True,
    "tool_choice": "auto",
    "tools": [],
    "usage": {
        "input_tokens": 12,
        "output_tokens": 5,
        "total_tokens": 17,
        "input_tokens_details": {"cached_tokens": 2},
        "output_tokens_details": {"reasoning_tokens": 3},
    },
}


def test_openai_calls_are_traced_with_model_and_token_usage(monkeypatch):
    monkeypatch.setattr(settings, "LANGSMITH_TRACING", True)
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json=OPENAI_RESPONSE))
    client = traced_openai(
        AsyncOpenAI(api_key="unused", http_client=httpx.AsyncClient(transport=transport))
    )
    finished = {}

    @traceable(run_type="chain")
    async def parent():
        return await client.responses.create(model="gpt-5-mini", input="hi")

    async def run():
        with tracing_context(enabled=True, client=MagicMock()):
            await parent(langsmith_extra={"on_end": lambda run_tree: finished.update(run=run_tree)})

    asyncio.run(run())

    [model_run] = finished["run"].child_runs
    assert model_run.run_type == "llm"
    assert model_run.extra["metadata"]["ls_provider"] == "openai"
    assert model_run.extra["metadata"]["ls_model_name"] == "gpt-5-mini"
    assert model_run.outputs["usage_metadata"] == {
        "input_tokens": 12,
        "output_tokens": 5,
        "total_tokens": 17,
        "input_token_details": {"cache_read": 2},
        "output_token_details": {"reasoning": 3},
    }


def test_openai_client_is_left_alone_when_tracing_is_off(monkeypatch):
    monkeypatch.setattr(settings, "LANGSMITH_TRACING", False)
    client = AsyncOpenAI(api_key="unused")

    assert traced_openai(client) is client
