import asyncio
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from chatbot.conversation_store.service import (
    MAX_HISTORY_MESSAGES,
    ConversationService,
)
from chatbot.orchestrator import AgentOrchestrator
from mcp_server.schema_adapter import SchemaAdapter


class InMemoryConversationRepository:
    def __init__(self, owner_id, messages=None):
        self.owner_id = owner_id
        self.messages = messages or []
        self.conversation_id = None

    async def get_conversation(self, conversation_id):
        if self.conversation_id != conversation_id:
            return None
        return SimpleNamespace(id=conversation_id, user_id=self.owner_id)

    async def create_conversation(self, user_id, conversation_id):
        self.conversation_id = conversation_id
        self.owner_id = user_id
        return SimpleNamespace(id=conversation_id, user_id=user_id)

    async def add_message(self, conversation_id, role, content):
        message = SimpleNamespace(role=role, content=content)
        self.messages.append(message)
        return message

    async def get_recent_messages(self, conversation_id, limit):
        return self.messages[-limit:]


class InMemorySession:
    async def commit(self):
        pass

    async def rollback(self):
        pass


def test_conversation_history_persists_and_is_bounded():
    async def run():
        owner_id = uuid4()
        conversation_id = uuid4()
        repository = InMemoryConversationRepository(owner_id)
        service = ConversationService(InMemorySession())
        service.repository = repository

        await service.get_or_create_conversation(conversation_id, owner_id)
        await service.add_user_message(conversation_id, owner_id, "first question")
        await service.add_assistant_message(conversation_id, owner_id, "first answer")

        for index in range(MAX_HISTORY_MESSAGES + 2):
            await service.add_user_message(
                conversation_id,
                owner_id,
                f"message {index}",
            )

        history = await service.get_recent_history(
            conversation_id,
            owner_id,
            limit=MAX_HISTORY_MESSAGES + 100,
        )
        assert len(history) == MAX_HISTORY_MESSAGES
        assert history[0]["content"] == "message 2"
        assert history[-1]["content"] == f"message {MAX_HISTORY_MESSAGES + 1}"

    asyncio.run(run())


def test_conversation_ids_cannot_be_used_by_another_user():
    async def run():
        owner_id = uuid4()
        other_user_id = uuid4()
        conversation_id = uuid4()
        repository = InMemoryConversationRepository(owner_id)
        repository.conversation_id = conversation_id
        service = ConversationService(InMemorySession())
        service.repository = repository

        with pytest.raises(HTTPException) as error:
            await service.get_or_create_conversation(conversation_id, other_user_id)
        assert error.value.status_code == 404

        with pytest.raises(HTTPException) as error:
            await service.add_user_message(
                conversation_id,
                other_user_id,
                "should not be stored",
            )
        assert error.value.status_code == 404
        assert repository.messages == []

    asyncio.run(run())


def test_history_ignores_non_chat_roles_and_limits_each_message():
    async def run():
        owner_id = uuid4()
        conversation_id = uuid4()
        repository = InMemoryConversationRepository(
            owner_id,
            messages=[
                SimpleNamespace(role="system", content="untrusted system role"),
                SimpleNamespace(role="assistant", content="x" * 5_000),
            ],
        )
        repository.conversation_id = conversation_id
        service = ConversationService(InMemorySession())
        service.repository = repository

        history = await service.get_recent_history(conversation_id, owner_id)
        assert [message["role"] for message in history] == ["assistant"]
        assert len(history[0]["content"]) == 4_000

    asyncio.run(run())


def test_mcp_agent_receives_recent_history_and_trusted_user_id():
    async def run():
        user_id = str(uuid4())
        call = SimpleNamespace(
            type="function_call",
            call_id="call-1",
            name="search_posts",
            arguments='{"user_id":"not-the-authenticated-user"}',
        )

        class MCPClient:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                return None

            async def list_tools(self):
                return [
                    SimpleNamespace(
                        name="search_posts",
                        description="Search public posts",
                        inputSchema={
                            "type": "object",
                            "properties": {"user_id": {"type": "string"}},
                            "required": ["user_id"],
                        },
                    )
                ]

            async def call_tool(self, name, arguments):
                assert name == "search_posts"
                assert arguments == {"user_id": user_id}
                return []

        class OpenAIClient:
            async def create_response(self, message, tools):
                assert message == [
                    {"role": "assistant", "content": "previous answer"},
                    {"role": "user", "content": "find my posts"},
                ]
                assert "user_id" not in tools[0]["parameters"]["properties"]
                return SimpleNamespace(id="response-1", output=[call])

            async def create_response_with_tool_result(self, **kwargs):
                return SimpleNamespace(
                    id="response-2",
                    output=[],
                    output_text="Here are your posts",
                )

        orchestrator = AgentOrchestrator(
            OpenAIClient(),
            MCPClient(),
            SchemaAdapter(),
        )
        result = await orchestrator.run_agent(
            "find my posts",
            user_id,
            history=[{"role": "assistant", "content": "previous answer"}],
        )
        assert result == "Here are your posts"

    asyncio.run(run())
