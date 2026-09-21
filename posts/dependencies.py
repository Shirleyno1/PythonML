from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from posts.db import get_async_session
from posts.repository import PostRepository
from posts.service import PostService


async def get_post_repository(
        session: Annotated[AsyncSession, Depends(get_async_session)],
) -> PostRepository:
    return PostRepository(session)

async def get_post_service(
        repository: Annotated[PostRepository, Depends(get_post_repository)]
) -> PostService:
    return PostService(repository)
