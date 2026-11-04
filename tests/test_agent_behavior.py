import asyncio
import json
from types import SimpleNamespace

from chatbot.orchestrator import AgentOrchestrator
from mcp_server.schema_adapter import SchemaAdapter


def _function_call(name: str, arguments: dict, call_id: str = "call-1"):
    return SimpleNamespace(
        type="function_call",
        call_id=call_id,
        name=name,
        arguments=json.dumps(arguments),
    )


class FakeMCPClient:
    def __init__(self, tool_result=None):
        self.tool_result = tool_result or []
        self.calls = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return None

    async def list_tools(self):
        return [
            SimpleNamespace(
                name="search_posts",
                description="Search public posts",
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

    async def call_tool(self, name, arguments):
        self.calls.append((name, arguments))
        return self.tool_result


class FakeOpenAIClient:
    def __init__(self, first_response, final_response=None):
        self.first_response = first_response
        self.final_response = final_response
        self.initial_calls = []
        self.followup_calls = []

    async def create_response(self, message, tools):
        self.initial_calls.append({"message": message, "tools": tools})
        return self.first_response

    async def create_response_with_tool_result(self, **kwargs):
        self.followup_calls.append(kwargs)
        return self.final_response


def test_agent_returns_model_answer_without_calling_tools():
    mcp = FakeMCPClient()
    model = FakeOpenAIClient(
        SimpleNamespace(id="response-1", output=[], output_text="Hello!")
    )
    agent = AgentOrchestrator(model, mcp, SchemaAdapter())

    answer = asyncio.run(agent.run_agent("Hello", user_id="user-1"))

    assert answer == "Hello!"
    assert mcp.calls == []
    assert model.followup_calls == []


def test_agent_runs_search_with_trusted_user_id_and_returns_final_answer():
    mcp = FakeMCPClient(tool_result=[{"title": "Python update"}])
    model = FakeOpenAIClient(
        first_response=SimpleNamespace(
            id="response-1",
            output=[
                _function_call(
                    "search_posts",
                    {"post_type": "share", "user_id": "forged-user"},
                )
            ],
        ),
        final_response=SimpleNamespace(
            id="response-2",
            output=[],
            output_text="I found a Python update.",
        ),
    )
    agent = AgentOrchestrator(model, mcp, SchemaAdapter())

    answer = asyncio.run(
        agent.run_agent(
            "Find my Python posts",
            user_id="authenticated-user",
            history=[{"role": "assistant", "content": "Previous answer"}],
        )
    )

    assert answer == "I found a Python update."
    assert mcp.calls == [
        (
            "search_posts",
            {"post_type": "share", "user_id": "authenticated-user"},
        )
    ]
    assert "user_id" not in model.initial_calls[0]["tools"][0]["parameters"]["properties"]
    assert model.followup_calls == [
        {
            "response_id": "response-1",
            "tool_call_id": "call-1",
            "tool_result": "[{'title': 'Python update'}]",
            "tools": model.initial_calls[0]["tools"],
        }
    ]
