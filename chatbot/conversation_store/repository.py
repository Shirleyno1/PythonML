from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from chatbot.conversation_store.models import Conversation, ConversationMessage


class ConversationRepository:

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_conversation(
            self,
            conversation_id: str,
            user_id: UUID,
    ) -> Conversation | None:
        result = await self.session.execute(
            select(Conversation)
            .where(
                Conversation.id == conversation_id,
                Conversation.user_id == user_id,
            )
            .options(
                selectinload(Conversation.messages)
            )
        )

        return result.scalar_one_or_none()

    async def create_conversation(
            self,
            user_id: UUID,
            conversation_id: str
    ) -> Conversation:
        conversation = Conversation(
            user_id=user_id,
            id=conversation_id,
        )

        self.session.add(conversation)
        await self.session.flush()

        return conversation

    async def add_message(
            self,
            conversation_id: str,
            role: str,
            content: str,
    ) -> ConversationMessage:

        message = ConversationMessage(
            conversation_id=conversation_id,
            role=role,
            content=content,
        )

        self.session.add(message)

        await self.session.flush()

        return message
