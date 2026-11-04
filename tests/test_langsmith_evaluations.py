from datetime import datetime, timezone
import sys
from types import ModuleType
from uuid import uuid4

import pytest
from langsmith.schemas import Example, Run

from evaluation.agui_evaluation import (
    ReadOnlyEvaluationMCPClient,
    agui_answer_present,
    agui_tool_selection_accuracy,
)
from evaluation import agui_evaluation
from evaluation.rag_evaluation import (
    _make_rag_predictor,
    rag_groundedness,
    rag_reference_fact_coverage,
    run_rag_evaluation,
)


def make_run(outputs: dict) -> Run:
    return Run(
        id=uuid4(),
        trace_id=uuid4(),
        name="evaluation-target",
        start_time=datetime.now(timezone.utc),
        run_type="chain",
        outputs=outputs,
    )


def make_example(outputs: dict) -> Example:
    return Example(id=uuid4(), outputs=outputs)


def test_agui_tool_evaluator_checks_exact_expected_tool_calls():
    example = make_example({"expected_tools": ["search_posts"]})

    assert agui_tool_selection_accuracy(
        make_run({"tool_calls": ["search_posts"]}),
        example,
    ) == {"key": "tool_selection_accuracy", "score": True}
    assert agui_tool_selection_accuracy(
        make_run({"tool_calls": ["delete_post"]}),
        example,
    ) == {"key": "tool_selection_accuracy", "score": False}


def test_agui_answer_evaluator_rejects_empty_response():
    example = make_example({})

    assert agui_answer_present(make_run({"answer": "Here is an answer."}), example) == {
        "key": "answer_present",
        "score": True,
    }
    assert agui_answer_present(make_run({"answer": "  "}), example) == {
        "key": "answer_present",
        "score": False,
    }


def test_agui_evaluation_mcp_cannot_call_mutating_tools():
    import asyncio

    client = ReadOnlyEvaluationMCPClient()

    with pytest.raises(ValueError, match="does not allow"):
        asyncio.run(client.call_tool("delete_post", {"post_id": "1"}))


def test_rag_evaluators_score_reference_facts_and_groundedness():
    example = make_example({"facts": ["11:00 AM", "10:00 PM"]})
    run = make_run({
        "answer": "Open 11:00 AM to 10:00 PM on weekdays.",
        "context": "Weekday hours are 11:00 AM until 10:00 PM.",
    })

    assert rag_reference_fact_coverage(run, example) == {
        "key": "reference_fact_coverage",
        "score": 1.0,
    }
    assert rag_groundedness(run, example) == {
        "key": "groundedness",
        "score": 1.0,
    }


def test_rag_groundedness_does_not_score_facts_missing_from_context():
    example = make_example({"facts": ["complimentary", "parking"]})
    run = make_run({
        "answer": "Parking is complimentary.",
        "context": "Parking is available next to the restaurant.",
    })

    assert rag_reference_fact_coverage(run, example)["score"] == 1.0
    assert rag_groundedness(run, example)["score"] == 0.5


def test_rag_predictor_retrieves_context_and_passes_it_to_generation(monkeypatch):
    retrieved_documents = [
        type("DocumentStub", (), {"page_content": "Open 11:00 AM to 10:00 PM."})()
    ]
    seen = {}

    class FakeRetriever:
        def invoke(self, question):
            seen["question"] = question
            return retrieved_documents

    def fake_generate(inputs):
        seen["model_input"] = inputs
        return type("ResponseStub", (), {"content": "Open 11:00 AM to 10:00 PM."})()

    class FakeRagRetriever:
        def __init__(self, file_path):
            seen["file_path"] = file_path

        def get_retriever(self):
            return FakeRetriever()

    chain_module = ModuleType("langchain.rag.chain")
    chain_module.format_documents = lambda docs: "\n\n".join(
        doc.page_content for doc in docs
    )
    chain_module.rag_chain = type(
        "FakeRagChain",
        (),
        {"invoke": staticmethod(fake_generate)},
    )()

    retriever_module = ModuleType("langchain.rag.retrievers")
    retriever_module.RagRetriever = FakeRagRetriever
    monkeypatch.setitem(sys.modules, "langchain.rag.chain", chain_module)
    monkeypatch.setitem(sys.modules, "langchain.rag.retrievers", retriever_module)

    predictor = _make_rag_predictor()
    output = predictor({"question": "When are you open?"})

    assert seen["file_path"].endswith("Resturaunt Q&A.pdf")
    assert seen["question"] == "When are you open?"
    assert seen["model_input"] == {
        "context": "Open 11:00 AM to 10:00 PM.",
        "question": "When are you open?",
    }
    assert output == {
        "answer": "Open 11:00 AM to 10:00 PM.",
        "context": "Open 11:00 AM to 10:00 PM.",
    }


@pytest.mark.parametrize(
    ("evaluate_path", "predictor_path", "runner", "prefix", "component"),
    [
        (
            "evaluation.agui_evaluation.evaluate",
            "evaluation.agui_evaluation._make_agui_predictor",
            agui_evaluation.run_agui_evaluation,
            "agui-agent",
            "agui-agent",
        ),
        (
            "evaluation.rag_evaluation.evaluate",
            "evaluation.rag_evaluation._make_rag_predictor",
            run_rag_evaluation,
            "langchain-rag",
            "langchain-rag",
        ),
    ],
)
def test_evaluation_runners_publish_expected_evaluators(
    evaluate_path,
    predictor_path,
    runner,
    prefix,
    component,
    monkeypatch,
):
    captured = {}

    def fake_evaluate(target, **kwargs):
        captured["target"] = target
        captured.update(kwargs)
        return "completed"

    monkeypatch.setenv("LANGSMITH_API_KEY", "test-key")
    monkeypatch.setattr(evaluate_path, fake_evaluate)
    monkeypatch.setattr(predictor_path, lambda: lambda _: {})

    assert runner() == "completed"
    assert captured["experiment_prefix"] == prefix
    assert captured["metadata"] == {"component": component}
    assert captured["evaluators"]
    assert captured["data"]
