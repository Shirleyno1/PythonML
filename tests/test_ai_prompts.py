import asyncio
from types import SimpleNamespace

import pytest
from langsmith.utils import LangSmithNotFoundError
from langchain_core.load import dumpd
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from ai_prompts import catalog, get_prompt, registry
from chatbot.openai_client import OpenAIClient
from mcp_server.schema_adapter import SchemaAdapter
from settings.config import settings


class FakeLangSmith:
    def __init__(self, manifests=None, error=None):
        self.manifests = manifests or {}
        self.error = error
        self.pulled = []

    def pull_prompt_commit(self, identifier, include_model=False):
        self.pulled.append(identifier)
        if self.error:
            raise self.error
        if identifier not in self.manifests:
            raise LangSmithNotFoundError(f"Prompt {identifier} not found")
        return SimpleNamespace(manifest=self.manifests[identifier])


def _manifest(messages, model=None):
    prompt = ChatPromptTemplate.from_messages(messages)
    if model is None:
        return dumpd(prompt)
    return dumpd(prompt | model)


@pytest.fixture
def langsmith(monkeypatch):
    def use(client, tag=None):
        monkeypatch.setattr(settings, "LANGSMITH_PROMPTS_ENABLED", True)
        monkeypatch.setattr(settings, "LANGSMITH_PROMPT_TAG", tag)
        monkeypatch.setattr(registry, "_client", lambda: client)
        return client

    monkeypatch.setattr(registry, "_retry_after", {})
    monkeypatch.setattr(settings, "OPENAI_MODEL", "local-model")
    return use


def test_local_prompt_is_used_when_langsmith_prompts_are_off(monkeypatch):
    monkeypatch.setattr(settings, "LANGSMITH_PROMPTS_ENABLED", False)
    monkeypatch.setattr(registry, "_client", pytest.fail)

    prompt = get_prompt(catalog.RAG_ANSWER)

    assert prompt.source == "local"
    assert prompt.model == settings.OPENAI_MODEL
    messages = prompt.to_messages(context="Open at 11.", question="When?")
    assert [message["role"] for message in messages] == ["system", "user"]
    assert "Open at 11." in messages[1]["content"]


def test_langsmith_prompt_and_its_openai_model_replace_the_local_ones(langsmith):
    langsmith(FakeLangSmith({
        "pythonml-rag-answer": _manifest(
            [("system", "Be brief."), ("human", "{context} / {question}")],
            ChatOpenAI(model="gpt-from-langsmith", api_key="unused"),
        ),
    }))

    prompt = get_prompt(catalog.RAG_ANSWER)

    assert prompt.source == "langsmith"
    assert prompt.model == "gpt-from-langsmith"
    assert prompt.to_messages(context="C", question="Q", unused="x") == [
        {"role": "system", "content": "Be brief."},
        {"role": "user", "content": "C / Q"},
    ]


def test_model_saved_with_settings_is_found_inside_its_binding(langsmith):
    model = ChatOpenAI(model="gpt-bound", api_key="unused").bind(stop=["END"])
    langsmith(FakeLangSmith({
        "pythonml-chat-assistant": _manifest([("human", "{message}")], model),
    }))

    assert get_prompt(catalog.CHAT_ASSISTANT).model == "gpt-bound"


def test_prompt_saved_without_a_model_keeps_the_configured_model(langsmith):
    langsmith(FakeLangSmith({
        "pythonml-chat-assistant": _manifest([("system", "Hi"), ("human", "{message}")]),
    }))

    prompt = get_prompt(catalog.CHAT_ASSISTANT)

    assert prompt.source == "langsmith"
    assert prompt.model == "local-model"


def test_non_openai_model_is_ignored(langsmith):
    manifest = _manifest([("human", "{message}")])
    manifest = {
        "lc": 1,
        "type": "constructor",
        "id": ["langchain", "schema", "runnable", "RunnableSequence"],
        "kwargs": {
            "first": manifest,
            "last": {"id": ["langchain", "chat_models", "anthropic", "ChatAnthropic"],
                     "kwargs": {"model": "some-other-model"}},
        },
    }
    langsmith(FakeLangSmith({"pythonml-chat-assistant": manifest}))

    prompt = get_prompt(catalog.CHAT_ASSISTANT)

    assert prompt.source == "langsmith"
    assert prompt.model == "local-model"


def test_prompt_needing_variables_the_app_lacks_falls_back_to_local(langsmith):
    langsmith(FakeLangSmith({
        "pythonml-chat-assistant": _manifest([("human", "{message} in {language}")]),
    }))

    assert get_prompt(catalog.CHAT_ASSISTANT).source == "local"


def test_failed_pull_falls_back_and_is_not_retried_straight_away(langsmith):
    client = langsmith(FakeLangSmith(error=ConnectionError("LangSmith is down")))

    first = get_prompt(catalog.INTENT_CLASSIFIER)
    second = get_prompt(catalog.INTENT_CLASSIFIER)

    assert first.source == second.source == "local"
    assert client.pulled == ["pythonml-intent-classifier"]


def test_tag_selects_the_tagged_commit(langsmith):
    client = langsmith(
        FakeLangSmith({"pythonml-chat-assistant:production": _manifest([("human", "{message}")])}),
        tag="production",
    )

    assert get_prompt(catalog.CHAT_ASSISTANT).source == "langsmith"
    assert client.pulled == ["pythonml-chat-assistant:production"]


def test_tool_descriptions_come_from_langsmith(langsmith):
    langsmith(FakeLangSmith({
        "pythonml-tool-search-posts": _manifest([("system", "Find posts.")]),
    }))
    tools = [
        SimpleNamespace(name="search_posts", description="server text", inputSchema={"properties": {}}),
        SimpleNamespace(name="other_tool", description="server text", inputSchema={"properties": {}}),
    ]

    descriptions = {
        tool["name"]: tool["description"]
        for tool in SchemaAdapter.mcp_tools_to_openai_tools(tools)
    }

    assert descriptions == {"search_posts": "Find posts.", "other_tool": "server text"}


def test_agent_sends_langsmith_instructions_before_the_conversation(langsmith):
    langsmith(FakeLangSmith({
        "pythonml-agui-agent": _manifest(
            [("system", "You help plant lovers.")],
            ChatOpenAI(model="gpt-agent", api_key="unused"),
        ),
    }))
    calls = []

    async def create(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(id="resp_1")

    client = OpenAIClient(api_key="unused")
    client.client = SimpleNamespace(responses=SimpleNamespace(create=create))
    history = [{"role": "user", "content": "hi"}, {"role": "assistant", "content": "hello"}]

    asyncio.run(client.create_response(message=[*history, {"role": "user", "content": "search posts"}], tools=[]))
    asyncio.run(client.create_response_with_tool_result(
        response_id="resp_1", tool_call_id="call_1", tool_result="[]", tools=[],
    ))

    assert calls[0]["model"] == "gpt-agent"
    assert calls[0]["input"] == [
        {"role": "system", "content": "You help plant lovers."},
        *history,
        {"role": "user", "content": "search posts"},
    ]
    assert calls[1]["model"] == "gpt-agent"
    assert "instructions" not in calls[1]


def test_agent_sends_only_the_conversation_without_a_langsmith_prompt(langsmith):
    langsmith(FakeLangSmith())
    calls = []

    async def create(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(id="resp_1")

    client = OpenAIClient(api_key="unused")
    client.client = SimpleNamespace(responses=SimpleNamespace(create=create))

    asyncio.run(client.create_response(message="hi", tools=[]))

    assert calls[0]["model"] == "local-model"
    assert calls[0]["input"] == [{"role": "user", "content": "hi"}]


def test_every_prompt_has_a_unique_langsmith_name():
    names = [spec.name for spec in catalog.ALL_PROMPTS]
    assert len(names) == len(set(names))


def test_missing_optional_prompt_is_quiet_but_missing_required_one_warns(langsmith, caplog):
    langsmith(FakeLangSmith(), tag="v1")

    with caplog.at_level("INFO", logger="ai_prompts.registry"):
        get_prompt(catalog.AGUI_AGENT)
        get_prompt(catalog.CHAT_ASSISTANT)

    assert [(record.levelname, record.getMessage()) for record in caplog.records] == [
        ("WARNING", "Using the local pythonml-chat-assistant prompt: LangSmith has no pythonml-chat-assistant:v1"),
    ]
