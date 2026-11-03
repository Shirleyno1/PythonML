from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from chatbot.conversation_store.service import ConversationService
from chatbot.orchestrator import AgentOrchestrator
from chatbot.schemas import ChatRequest
from posts.db import User, get_async_session
from posts.users import current_active_user

router = APIRouter()
orchestrator: AgentOrchestrator | None = None


def configure_orchestrator(agent_orchestrator: AgentOrchestrator) -> None:
    global orchestrator
    orchestrator = agent_orchestrator


@router.post("/ai/mcp")
async def ai_mcp(
    request: ChatRequest,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user),
):
    conversation_service = ConversationService(session)
    conversation_id = request.conversation_id
    await conversation_service.get_or_create_conversation(conversation_id, user.id)
    history = await conversation_service.get_recent_history(
        conversation_id,
        user.id,
        limit=19,
    )
    await conversation_service.add_user_message(
        conversation_id,
        user.id,
        request.message,
    )

    if orchestrator is None:
        raise RuntimeError("The MCP agent has not been configured.")
    result = await orchestrator.run_agent(
        message=request.message,
        user_id=str(user.id),
        history=history,
    )
    await conversation_service.add_assistant_message(
        conversation_id,
        user.id,
        result,
    )
    return result
