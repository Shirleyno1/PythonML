from collections import defaultdict
import argparse
import os
from typing import Any
from uuid import uuid4

from chatbot.ai_service import classify_message
from evaluation.intent_dataset import TEST_CASES
from langsmith.evaluation import evaluate
from langsmith.schemas import Example, Run


def _predict_intent(inputs: dict[str, Any]) -> dict[str, str]:
    result = classify_message(inputs["message"])
    return {"intent": result.intent}


def intent_accuracy(run: Run, example: Example) -> dict[str, str | bool]:
    predicted = (run.outputs or {}).get("intent")
    expected = (example.outputs or {}).get("intent")
    return {
        "key": "intent_accuracy",
        "score": predicted == expected,
    }


def run_langsmith_evaluation():
    if not os.getenv("LANGSMITH_API_KEY"):
        raise RuntimeError(
            "LANGSMITH_API_KEY is required to run a LangSmith evaluation."
        )

    dataset: list[Example] = [
        Example(
            id=uuid4(),
            inputs={"message": test_case["message"]},
            outputs={"intent": test_case["expected_intent"]},
        )
        for test_case in TEST_CASES
    ]
    return evaluate(
        _predict_intent,
        data=dataset,
        evaluators=[intent_accuracy],
        experiment_prefix="ai-intent-classifier",
        description="Intent classification accuracy on the local intent dataset.",
        metadata={"component": "ai-intent-classification"},
    )


def run_evaluation():
    results = []

    for test_case in TEST_CASES:

        result = classify_message(
            test_case["message"],
        )

        passed = (
            result.intent == test_case["expected_intent"]
        )

        results.append({
            "message": test_case["message"],
            "expected": test_case["expected_intent"],
            "actual": result.intent,
            "passed": passed,
        })

    return results

def calculate_accuracy(results):
    correct = sum(
        result["passed"]
        for result in results
    )
    total = len(results)

    return correct / total

def evaluate_by_intent(results):

    stats = defaultdict(
        lambda: {
            "correct": 0,
            "total": 0
        }
    )

    for result in results:
        intent = result["expected"]
        stats[intent]["total"] += 1
        if result["passed"]:
            stats[intent]["correct"] += 1

    for intent, data in stats.items():

        accuracy = (data["correct"] / data["total"])

        print(
            f"{intent}: "
            f"{accuracy:.2%}"
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    evaluation_group = parser.add_mutually_exclusive_group()
    evaluation_group.add_argument(
        "--langsmith",
        action="store_true",
        help="Run intent-classifier evaluation in LangSmith.",
    )
    evaluation_group.add_argument(
        "--agui",
        action="store_true",
        help="Evaluate AG-UI tool selection and answer presence in LangSmith.",
    )
    evaluation_group.add_argument(
        "--rag",
        action="store_true",
        help="Evaluate LangChain RAG fact coverage and groundedness in LangSmith.",
    )
    args = parser.parse_args()

    if args.langsmith:
        run_langsmith_evaluation()
        print("Intent-classifier LangSmith evaluation completed.")
    elif args.agui:
        from evaluation.agui_evaluation import run_agui_evaluation

        run_agui_evaluation()
        print("AG-UI LangSmith evaluation completed.")
    elif args.rag:
        from evaluation.rag_evaluation import run_rag_evaluation

        run_rag_evaluation()
        print("LangChain RAG LangSmith evaluation completed.")
    else:
        results = run_evaluation()

        for result in results:
            print({
                f"{'PASS' if result['passed'] else 'FAIL'}"
                f"| expected={result['expected']}"
                f"| actual={result['actual']} "
                f" {result['message']}"
            })

        accuracy = calculate_accuracy(results)

        print(f"Accuracy: {accuracy:.2%}")

        evaluate_by_intent(results)
