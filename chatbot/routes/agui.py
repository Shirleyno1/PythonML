from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from chatbot.agui.models import AgUiRequest
from chatbot.agui.service import stream_agent_events
from chatbot.conversation_store.service import ConversationService
from chatbot.orchestrator import AgentOrchestrator
from posts.db import get_async_session, User
from posts.users import current_active_user

router = APIRouter()
orchestrator: AgentOrchestrator | None = None


def configure_orchestrator(agent_orchestrator: AgentOrchestrator) -> None:
    global orchestrator
    orchestrator = agent_orchestrator


@router.post("/ai/agui")
async def agui(
    request: AgUiRequest,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user),
):
    conversation_service = ConversationService(session)
    await conversation_service.get_or_create_conversation(request.thread_id, user.id)
    history = await conversation_service.get_recent_history(
        request.thread_id,
        user.id,
        limit=19,
    )
    await conversation_service.add_user_message(
        request.thread_id,
        user.id,
        request.message,
    )

    if orchestrator is None:
        raise RuntimeError("The MCP agent has not been configured.")
    return StreamingResponse(
        stream_agent_events(request, user.id, history, orchestrator),
        media_type="text/event-stream",
    )
