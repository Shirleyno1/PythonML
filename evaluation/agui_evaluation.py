import asyncio
import os
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

from chatbot.openai_client import OpenAIClient
from chatbot.orchestrator import AgentOrchestrator
from evaluation.agui_dataset import AGUI_TEST_CASES
from langsmith.evaluation import evaluate
from langsmith.schemas import Example, Run
from mcp_server.schema_adapter import SchemaAdapter


class ReadOnlyEvaluationMCPClient:
    """Provide deterministic search results without reaching the real MCP server."""

    def __init__(self) -> None:
        self.tool_calls: list[str] = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return None

    async def list_tools(self):
        return [
            SimpleNamespace(
                name="search_posts",
                description="Search public posts.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "user_id": {"type": "string"},
                        "post_type": {"type": "string"},
                    },
                    "required": ["user_id"],
                },
            )
        ]

    async def call_tool(self, name: str, arguments: dict[str, Any]):
        if name != "search_posts":
            raise ValueError(f"Evaluation MCP does not allow {name!r}.")
        self.tool_calls.append(name)
        return [
            {
                "title": "Community garden update",
                "description": "Volunteers planted herbs this weekend.",
            }
        ]


def _make_agui_predictor():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is required for AG-UI evaluation.")

    mcp_client = ReadOnlyEvaluationMCPClient()
    orchestrator = AgentOrchestrator(
        openai_client=OpenAIClient(api_key=api_key),
        mcp_client=mcp_client,
        schema_adapter=SchemaAdapter(),
    )

    def predict(inputs: dict[str, Any]) -> dict[str, Any]:
        mcp_client.tool_calls.clear()
        answer = asyncio.run(
            orchestrator.run_agent(
                message=inputs["message"],
                user_id="langsmith-evaluation",
            )
        )
        return {
            "answer": answer,
            "tool_calls": list(mcp_client.tool_calls),
        }

    return predict


def agui_tool_selection_accuracy(
    run: Run,
    example: Example,
) -> dict[str, str | bool]:
    actual = (run.outputs or {}).get("tool_calls", [])
    expected = (example.outputs or {}).get("expected_tools", [])
    return {
        "key": "tool_selection_accuracy",
        "score": actual == expected,
    }


def agui_answer_present(run: Run, _example: Example) -> dict[str, str | bool]:
    answer = (run.outputs or {}).get("answer")
    return {
        "key": "answer_present",
        "score": isinstance(answer, str) and bool(answer.strip()),
    }


def run_agui_evaluation():
    if not os.getenv("LANGSMITH_API_KEY"):
        raise RuntimeError("LANGSMITH_API_KEY is required for LangSmith evaluation.")

    dataset = [
        Example(
            id=uuid4(),
            inputs={"message": case["message"]},
            outputs={"expected_tools": case["expected_tools"]},
        )
        for case in AGUI_TEST_CASES
    ]
    return evaluate(
        _make_agui_predictor(),
        data=dataset,
        evaluators=[agui_tool_selection_accuracy, agui_answer_present],
        experiment_prefix="agui-agent",
        description=(
            "AG-UI agent tool selection and response checks using a read-only "
            "synthetic MCP tool."
        ),
        metadata={"component": "agui-agent"},
    )
