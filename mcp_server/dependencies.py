from contextlib import asynccontextmanager

from posts.db import async_session_maker
from posts.repository import PostRepository
from posts.service import PostService


@asynccontextmanager
async def get_post_service():
    async with async_session_maker() as session:
        repository = PostRepository(session)
        service = PostService(repository)

        yield service

