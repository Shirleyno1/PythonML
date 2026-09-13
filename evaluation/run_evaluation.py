from collections import defaultdict

from chatbot.ai_service import classify_message
from evaluation.intent_dataset import TEST_CASES


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
