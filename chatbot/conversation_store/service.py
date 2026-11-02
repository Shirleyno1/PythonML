from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from chatbot.conversation_store.models import ConversationMessage, Conversation
from chatbot.conversation_store.repository import ConversationRepository

MAX_HISTORY_MESSAGES = 20
MAX_HISTORY_MESSAGE_CHARS = 4_000


class ConversationService:

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repository = ConversationRepository(session)

    async def get_or_create_conversation(
        self,
        conversation_id: UUID,
        user_id: UUID,
    ) -> Conversation:
        conversation = await self.repository.get_conversation(conversation_id)
        if conversation:
            return self._require_owner(conversation, user_id)

        try:
            conversation = await self.repository.create_conversation(
                conversation_id=conversation_id,
                user_id=user_id,
            )
            await self.session.commit()
            return conversation
        except IntegrityError:
            await self.session.rollback()
            conversation = await self.repository.get_conversation(conversation_id)
            if conversation is not None:
                return self._require_owner(conversation, user_id)
            raise

    async def get_recent_history(
        self,
        conversation_id: UUID,
        user_id: UUID,
        limit: int = MAX_HISTORY_MESSAGES,
    ) -> list[dict[str, str]]:
        await self._get_owned_conversation(conversation_id, user_id)
        messages = await self.repository.get_recent_messages(
            conversation_id,
            limit=max(1, min(limit, MAX_HISTORY_MESSAGES)),
        )
        return [
            {"role": message.role, "content": message.content[:MAX_HISTORY_MESSAGE_CHARS]}
            for message in messages
            if message.role in {"user", "assistant"}
        ]

    async def add_user_message(
        self,
        conversation_id: UUID,
        user_id: UUID,
        content: str,
    ):
        return await self._add_message(
            conversation_id,
            user_id,
            role="user",
            content=content,
        )

    async def add_assistant_message(
        self,
        conversation_id: UUID,
        user_id: UUID,
        content: str,
    ):
        return await self._add_message(
            conversation_id,
            user_id,
            role="assistant",
            content=content,
        )

    async def _add_message(
        self,
        conversation_id: UUID,
        user_id: UUID,
        role: str,
        content: str,
    ) -> ConversationMessage:
        await self._get_owned_conversation(conversation_id, user_id)
        message = await self.repository.add_message(
            conversation_id=conversation_id,
            role=role,
            content=content,
        )
        await self.session.commit()
        return message

    async def _get_owned_conversation(
        self,
        conversation_id: UUID,
        user_id: UUID,
    ) -> Conversation:
        conversation = await self.repository.get_conversation(conversation_id)
        if conversation is None:
            raise HTTPException(status_code=404, detail="Conversation not found")
        return self._require_owner(conversation, user_id)

    @staticmethod
    def _require_owner(conversation: Conversation, user_id: UUID) -> Conversation:
        if conversation.user_id != user_id:
            raise HTTPException(status_code=404, detail="Conversation not found")
        return conversation
