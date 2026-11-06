import asyncio
import json
from types import SimpleNamespace

from fastmcp import Client, FastMCP

from chatbot.agui.service import _format_tool_event, _with_shown_posts
from chatbot.orchestrator import MAX_POST_CARDS, POST_CARDS_SHOWN_NOTE, AgentOrchestrator
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
        return {"id": post_id, "title": "My fern", "post": {"id": post_id, "caption": "My fern"}}

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
        "post": {"id": "post-1", "caption": "My fern"},
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
        return {"id": post_id, "title": "My fern", "post": {"id": post_id, "caption": "My fern"}}

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
            "post": {"id": "post-1", "caption": "My fern"},
        }
    )

    assert json.loads(sse.removeprefix("data: ")) == {
        "type": "CUSTOM",
        "name": "delete_post_confirmation",
        "value": {
            "postId": "post-1",
            "title": "My fern",
            "post": {"id": "post-1", "caption": "My fern"},
        },
    }


class ScriptedOpenAIClient:
    """Returns each response in turn, so a run can make several rounds of tool calls."""

    def __init__(self, *responses):
        self.responses = list(responses)
        self.tool_results = []

    async def create_response(self, message, tools):
        return self.responses.pop(0)

    async def create_response_with_tool_result(self, **kwargs):
        self.tool_results.append(kwargs["tool_result"])
        return self.responses.pop(0)


def _tool_response(name: str, arguments: dict | None = None):
    return SimpleNamespace(id="response", output=[_function_call(name, arguments or {})])


def _final_response(text: str = "Here are some posts."):
    return SimpleNamespace(id="final", output=[], output_text=text)


def _run_recording_events(agent, on_tool_event=True):
    events = []

    async def record(event):
        events.append(event)

    answer = asyncio.run(
        agent.run_agent("show me posts", "user-1", on_tool_event=record if on_tool_event else None)
    )
    return answer, events


def _post_results(events):
    return [event for event in events if event["type"] == "post_results"]


def test_search_results_are_shown_as_cards_and_the_model_is_told_not_to_list_them():
    posts = [{"id": "post-1", "caption": "My fern"}]
    model = ScriptedOpenAIClient(_tool_response("search_posts"), _final_response())
    agent = AgentOrchestrator(model, FakeMCPClient(tool_result=posts), SchemaAdapter())

    answer, events = _run_recording_events(agent)

    assert answer == "Here are some posts."
    assert _post_results(events) == [{"type": "post_results", "posts": posts, "total": 1}]
    assert POST_CARDS_SHOWN_NOTE in model.tool_results[0]
    assert "post-1" in model.tool_results[0]


def test_search_results_are_read_from_a_real_mcp_result():
    server = FastMCP("test")

    @server.tool
    async def search_posts() -> list[dict]:
        return [{"id": "post-1", "created_at": "2026-11-06T00:00:00", "images": []}]

    class InMemoryMCPClient(FakeMCPClient):
        async def call_tool(self, name, arguments):
            async with Client(server) as client:
                return await client.call_tool(name)

    model = ScriptedOpenAIClient(_tool_response("search_posts"), _final_response())
    agent = AgentOrchestrator(model, InMemoryMCPClient(), SchemaAdapter())

    _, events = _run_recording_events(agent)

    assert _post_results(events)[0]["posts"] == [
        {"id": "post-1", "created_at": "2026-11-06T00:00:00", "images": []}
    ]
    # The whole payload has to survive the trip onto the SSE stream.
    sse = _format_tool_event(_post_results(events)[0])
    assert json.loads(sse.removeprefix("data: "))["value"]["total"] == 1


def test_large_search_results_are_capped_but_report_the_real_total():
    posts = [{"id": f"post-{index}"} for index in range(MAX_POST_CARDS + 5)]
    model = ScriptedOpenAIClient(_tool_response("search_posts"), _final_response())
    agent = AgentOrchestrator(model, FakeMCPClient(tool_result=posts), SchemaAdapter())

    _, events = _run_recording_events(agent)

    assert len(_post_results(events)[0]["posts"]) == MAX_POST_CARDS
    assert _post_results(events)[0]["total"] == MAX_POST_CARDS + 5


def test_empty_search_shows_no_cards_and_leaves_the_model_to_answer():
    model = ScriptedOpenAIClient(_tool_response("search_posts"), _final_response("Nothing found."))
    agent = AgentOrchestrator(model, FakeMCPClient(tool_result=[]), SchemaAdapter())

    _, events = _run_recording_events(agent)

    assert _post_results(events) == []
    assert POST_CARDS_SHOWN_NOTE not in model.tool_results[0]


def test_searching_to_find_a_post_to_delete_shows_no_cards():
    async def lookup(post_id, user_id):
        return {"id": post_id, "title": "My fern", "post": {"id": post_id, "caption": "My fern"}}

    model = ScriptedOpenAIClient(
        _tool_response("search_posts"),
        _tool_response("delete_post", {"post_id": "post-1"}),
        _final_response("Please check the prompt."),
    )
    agent = AgentOrchestrator(
        model,
        FakeMCPClient(tool_result=[{"id": "post-1"}]),
        SchemaAdapter(),
        post_lookup=lookup,
    )

    _, events = _run_recording_events(agent)

    assert _post_results(events) == []
    assert [event["type"] for event in events].count("delete_confirmation") == 1


def test_clients_without_an_event_stream_still_get_the_posts_as_text():
    posts = [{"id": "post-1"}]
    model = ScriptedOpenAIClient(_tool_response("search_posts"), _final_response())
    agent = AgentOrchestrator(model, FakeMCPClient(tool_result=posts), SchemaAdapter())

    _run_recording_events(agent, on_tool_event=False)

    assert POST_CARDS_SHOWN_NOTE not in model.tool_results[0]


def test_post_results_are_streamed_as_a_custom_event():
    posts = [{"id": "post-1", "caption": "My fern"}]

    sse = _format_tool_event({"type": "post_results", "posts": posts, "total": 3})

    assert json.loads(sse.removeprefix("data: ")) == {
        "type": "CUSTOM",
        "name": "post_search_results",
        "value": {"posts": posts, "total": 3},
    }


def test_stored_reply_records_shown_posts_so_the_next_turn_can_refer_to_them():
    stored = _with_shown_posts(
        "Here you go.",
        [{"id": "post-1", "caption": "My fern"}, {"id": "post-2", "caption": None}],
    )

    assert stored.startswith("Here you go.")
    assert 'id=post-1 "My fern"' in stored
    assert '2. id=post-2 ""' in stored
    assert _with_shown_posts("Nothing found.", []) == "Nothing found."
