from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from chatbot.conversation_store.models import ConversationMessage, Conversation
from chatbot.conversation_store.repository import ConversationRepository


class ConversationService:

    def __init__(self,session: AsyncSession):
        self.repository = ConversationRepository(session)

    async def get_or_create_conversation(
        self,
        conversation_id: str,
        user_id: UUID,
    ) -> Conversation:
        conversation = await self.repository.get_conversation(conversation_id=conversation_id, user_id=user_id)

        if conversation:
            return conversation

        return await self.repository.create_conversation(conversation_id=conversation_id, user_id=user_id)

    async def add_user_message(
            self,
            conversation_id: str,
            content: str
    ):
        return await self.repository.add_message(
            conversation_id=conversation_id,
            role="user",
            content=content,
        )

    async def add_assistant_message(
            self,
            conversation_id: str,
            content: str
    ):
        return await self.repository.add_message(
            conversation_id=conversation_id,
            role="assistant",
            content=content,
        )

