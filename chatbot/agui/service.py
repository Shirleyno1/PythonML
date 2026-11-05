import asyncio
import logging
import uuid
from dataclasses import dataclass
from uuid import UUID

from chatbot.agui.events import (
    CustomEvent,
    ErrorEvent,
    RunFinishedEvent,
    RunStartedEvent,
    TextMessageContentEvent,
    TextMessageEndEvent,
    TextMessageStartEvent,
    ToolCallArgsEvent,
    ToolCallEndEvent,
    ToolCallResultEvent,
    ToolCallStartEvent,
)
from chatbot.agui.models import AgUiRequest
from chatbot.conversation_store.service import ConversationService
from chatbot.orchestrator import AgentOrchestrator
from posts.db import async_session_maker

logger = logging.getLogger(__name__)


@dataclass
class AgentStreamState:
    answer: str = ""
    succeeded: bool = True


def _format_tool_event(event: dict[str, str]) -> str | None:
    event_type = event["type"]
    if event_type == "start":
        return ToolCallStartEvent(
            tool_call_id=event["tool_call_id"],
            tool_call_name=event["tool_name"],
        ).to_sse()
    if event_type == "args":
        return ToolCallArgsEvent(
            tool_call_id=event["tool_call_id"],
            delta=event["arguments"],
        ).to_sse()
    if event_type == "end":
        return ToolCallEndEvent(tool_call_id=event["tool_call_id"]).to_sse()
    if event_type == "result":
        return ToolCallResultEvent(
            message_id=None,
            tool_call_id=event["tool_call_id"],
            content=event["content"],
        ).to_sse()
    if event_type == "delete_confirmation":
        return CustomEvent(
            name="delete_post_confirmation",
            value={"postId": event["post_id"], "title": event["title"]},
        ).to_sse()
    return None


async def _run_agent(
    orchestrator: AgentOrchestrator,
    request: AgUiRequest,
    user_id: UUID,
    history: list[dict[str, str]],
    event_queue: asyncio.Queue[dict[str, str] | None],
) -> None:
    async def publish_tool_event(event: dict[str, str]) -> None:
        await event_queue.put(event)

    try:
        answer = await orchestrator.run_agent(
            message=request.message,
            user_id=str(user_id),
            history=history,
            on_tool_event=publish_tool_event,
        )
        await event_queue.put({"type": "answer", "content": answer})
    except Exception:
        logger.exception("AG-UI MCP agent request failed")
        await event_queue.put({"type": "error"})
    finally:
        await event_queue.put(None)


async def stream_agent_events(
    request: AgUiRequest,
    user_id: UUID,
    history: list[dict[str, str]],
    orchestrator: AgentOrchestrator,
):
    thread_id = str(request.thread_id)
    run_id = request.run_id
    message_id = str(uuid.uuid4())
    event_queue: asyncio.Queue[dict[str, str] | None] = asyncio.Queue()
    agent_task = asyncio.create_task(
        _run_agent(orchestrator, request, user_id, history, event_queue)
    )

    state = AgentStreamState()
    try:
        yield RunStartedEvent(thread_id=thread_id, run_id=run_id).to_sse()
        yield TextMessageStartEvent(message_id=message_id).to_sse()

        async for chunk in _stream_agent_events(
            event_queue,
            message_id,
            state,
        ):
            yield chunk

        await agent_task
        if state.succeeded:
            await _persist_assistant_message(
                request.thread_id,
                user_id,
                state.answer,
            )

        yield TextMessageEndEvent(message_id=message_id).to_sse()
        yield RunFinishedEvent(thread_id=thread_id, run_id=run_id).to_sse()
    finally:
        if not agent_task.done():
            agent_task.cancel()
            await asyncio.gather(agent_task, return_exceptions=True)


async def _stream_agent_events(
    event_queue: asyncio.Queue[dict[str, str] | None],
    message_id: str,
    state: AgentStreamState,
):
    while True:
        event = await event_queue.get()
        if event is None:
            return
        if event["type"] == "answer":
            state.answer = event["content"]
            if state.answer:
                yield TextMessageContentEvent(
                    message_id=message_id,
                    delta=state.answer,
                ).to_sse()
        elif event["type"] == "error":
            state.succeeded = False
            yield ErrorEvent(
                message="The assistant could not complete this request.",
                code="AGENT_ERROR",
            ).to_sse()
        else:
            formatted_event = _format_tool_event(event)
            if formatted_event:
                yield formatted_event


async def _persist_assistant_message(
    conversation_id: UUID,
    user_id: UUID,
    answer: str,
) -> None:
    async with async_session_maker() as message_session:
        await ConversationService(message_session).add_assistant_message(
            conversation_id,
            user_id,
            answer,
        )
