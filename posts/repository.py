from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from posts.db import Post, User


class PostRepository:

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_posts(self):
        result = await self.session.execute(
            select(Post)
            .options(selectinload(Post.user))
            .order_by(Post.created_at.desc())
        )

        return result.scalars().all()