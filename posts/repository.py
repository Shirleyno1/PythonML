from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from posts.db import Post, User


class PostRepository:

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_posts(self, user_id):
        result = await self.session.execute(
            select(Post)
            .options(selectinload(Post.user), selectinload(Post.images))
            .where(Post.user_id == user_id)
            .order_by(Post.created_at.desc())
        )

        return result.scalars().all()

    async def search_posts(self, post_type: str):
        result = await self.session.execute(
            select(Post)
            .options(selectinload(Post.user), selectinload(Post.images))
            .where(
                Post.post_type == post_type,
                Post.is_private.is_(False),
            )
            .order_by(Post.created_at.desc())
        )

        return result.scalars().all()

    async def search_public_posts(self, post_type: str | None = None):
        query = (
            select(Post)
            .options(selectinload(Post.user), selectinload(Post.images))
            .where(Post.is_private.is_(False))
            .order_by(Post.created_at.desc())
        )
        if post_type is not None:
            query = query.where(Post.post_type == post_type)

        result = await self.session.execute(query)
        return result.scalars().all()

    async def delete_post(self, post_id: str, user_id):
        result = await self.session.execute(
            select(Post)
            .options(selectinload(Post.images))
            .where(Post.id == post_id)
        )

        post = result.scalars().first()

        if not post:
            raise HTTPException(status_code=404, detail=f"Post {post_id} not found")

        if post.user_id != user_id:
            raise HTTPException(status_code=403, detail="You don't have permission to delete this post")

        await self.session.delete(post)
        await self.session.commit()
