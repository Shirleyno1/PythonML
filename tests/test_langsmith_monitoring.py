from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

from langsmith.schemas import Example, Run

from observability.tracing import (
    trace_agent_input,
    trace_ai_request_input,
    trace_ai_result,
    trace_model_output,
    trace_tool_input,
)
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
