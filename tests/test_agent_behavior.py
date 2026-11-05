import asyncio
import json
from types import SimpleNamespace

from chatbot.agui.service import _format_tool_event
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


def _delete_agent(post_lookup, arguments=None):
    mcp = FakeMCPClient()
    model = FakeOpenAIClient(
        first_response=SimpleNamespace(
            id="response-1",
            output=[_function_call("delete_post", arguments or {"post_id": "post-1"})],
        ),
        final_response=SimpleNamespace(
            id="response-2",
            output=[],
            output_text="Please check the confirmation prompt.",
        ),
    )
    return AgentOrchestrator(model, mcp, SchemaAdapter(), post_lookup=post_lookup), mcp, model


def _run_delete(agent, *, with_events=True):
    events = []

    async def record(event):
        events.append(event)

    answer = asyncio.run(
        agent.run_agent(
            "Delete my post",
            user_id="authenticated-user",
            on_tool_event=record if with_events else None,
        )
    )
    return answer, events


def test_agent_delete_asks_for_confirmation_without_deleting():
    lookups = []

    async def lookup(post_id, user_id):
        lookups.append((post_id, user_id))
        return {"id": post_id, "title": "My fern"}

    agent, mcp, model = _delete_agent(
        lookup, {"post_id": "post-1", "user_id": "forged-user"}
    )

    answer, events = _run_delete(agent)

    assert answer == "Please check the confirmation prompt."
    assert mcp.calls == []
    assert lookups == [("post-1", "authenticated-user")]
    assert {
        "type": "delete_confirmation",
        "tool_call_id": "call-1",
        "post_id": "post-1",
        "title": "My fern",
    } in events
    assert "NOT been deleted" in model.followup_calls[0]["tool_result"]


def test_agent_delete_of_a_post_the_user_does_not_own_shows_no_prompt():
    async def lookup(post_id, user_id):
        return None

    agent, mcp, model = _delete_agent(lookup)

    _, events = _run_delete(agent)

    assert mcp.calls == []
    assert "delete_confirmation" not in {event["type"] for event in events}
    assert "Nothing was deleted" in model.followup_calls[0]["tool_result"]


def test_agent_delete_without_an_event_stream_does_not_claim_a_prompt_was_shown():
    async def lookup(post_id, user_id):
        return {"id": post_id, "title": "My fern"}

    agent, mcp, model = _delete_agent(lookup)

    _run_delete(agent, with_events=False)

    assert mcp.calls == []
    assert "posts screen" in model.followup_calls[0]["tool_result"]


def test_delete_confirmation_is_streamed_as_a_custom_event():
    sse = _format_tool_event(
        {
            "type": "delete_confirmation",
            "tool_call_id": "call-1",
            "post_id": "post-1",
            "title": "My fern",
        }
    )

    assert json.loads(sse.removeprefix("data: ")) == {
        "type": "CUSTOM",
        "name": "delete_post_confirmation",
        "value": {"postId": "post-1", "title": "My fern"},
    }
