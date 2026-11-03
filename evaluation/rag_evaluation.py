import os
import re
from pathlib import Path
from typing import Any
from uuid import uuid4

from evaluation.rag_dataset import RAG_TEST_CASES
from langchain.rag.chain import format_documents, rag_chain
from langchain.rag.retrievers import RagRetriever
from langsmith.evaluation import evaluate
from langsmith.schemas import Example, Run

RAG_DOCUMENT_PATH = (
    Path(__file__).resolve().parents[1] / "data" / "Resturaunt Q&A.pdf"
)


def _normalize_fact(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", text.casefold())


def rag_reference_fact_coverage(
    run: Run,
    example: Example,
) -> dict[str, str | float]:
    answer = str((run.outputs or {}).get("answer", ""))
    facts = (example.outputs or {}).get("facts", [])
    normalized_answer = _normalize_fact(answer)
    score = (
        sum(_normalize_fact(fact) in normalized_answer for fact in facts) / len(facts)
        if facts
        else 0.0
    )
    return {"key": "reference_fact_coverage", "score": score}


def rag_groundedness(run: Run, example: Example) -> dict[str, str | float]:
    outputs = run.outputs or {}
    context = _normalize_fact(str(outputs.get("context", "")))
    answer = _normalize_fact(str(outputs.get("answer", "")))
    facts = (example.outputs or {}).get("facts", [])
    score = (
        sum(
            _normalize_fact(fact) in context and _normalize_fact(fact) in answer
            for fact in facts
        )
        / len(facts)
        if facts
        else 0.0
    )
    return {"key": "groundedness", "score": score}


def _make_rag_predictor():
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is required for RAG evaluation.")
    if not RAG_DOCUMENT_PATH.is_file():
        raise FileNotFoundError(f"RAG evaluation document not found: {RAG_DOCUMENT_PATH}")

    retriever = RagRetriever(file_path=str(RAG_DOCUMENT_PATH)).get_retriever()

    def predict(inputs: dict[str, Any]) -> dict[str, str]:
        question = inputs["question"]
        documents = retriever.invoke(question)
        answer = rag_chain.invoke(
            {
                "context": format_documents(documents),
                "question": question,
            }
        )
        return {
            "answer": str(answer.content),
            "context": format_documents(documents),
        }

    return predict


def run_rag_evaluation():
    if not os.getenv("LANGSMITH_API_KEY"):
        raise RuntimeError("LANGSMITH_API_KEY is required for LangSmith evaluation.")

    dataset = [
        Example(
            id=uuid4(),
            inputs={"question": case["question"]},
            outputs={"facts": case["facts"]},
        )
        for case in RAG_TEST_CASES
    ]
    return evaluate(
        _make_rag_predictor(),
        data=dataset,
        evaluators=[rag_reference_fact_coverage, rag_groundedness],
        experiment_prefix="langchain-rag",
        description=(
            "Restaurant FAQ RAG reference-fact coverage and groundedness."
        ),
        metadata={"component": "langchain-rag"},
    )
