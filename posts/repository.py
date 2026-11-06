from fastapi import HTTPException
from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from posts.db import (
    Comment,
    CommentReaction,
    Post,
    PointTransaction,
    PostReaction,
    Task,
    User,
)
from posts.schema import PointSource, PostReactionType, ReactionType


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

        # Removed explicitly so this behaves the same on SQLite, which doesn't
        # enforce foreign keys by default. Earned points are kept.
        comment_ids = select(Comment.id).where(Comment.post_id == post_id)
        await self.session.execute(
            update(PointTransaction)
            .where(PointTransaction.post_id == post_id)
            .values(post_id=None, comment_id=None)
        )
        await self.session.execute(
            delete(CommentReaction).where(CommentReaction.comment_id.in_(comment_ids))
        )
        await self.session.execute(delete(Comment).where(Comment.post_id == post_id))
        await self.session.execute(delete(PostReaction).where(PostReaction.post_id == post_id))
        await self.session.delete(post)
        await self.session.commit()

    async def get_post(self, post_id: str, lock: bool = False):
        query = select(Post).where(Post.id == post_id)
        if lock:
            query = query.with_for_update()
        result = await self.session.execute(query)
        return result.scalars().first()

    async def get_post_with_details(self, post_id: str):
        result = await self.session.execute(
            select(Post)
            .options(selectinload(Post.user), selectinload(Post.images))
            .where(Post.id == post_id)
        )
        return result.scalars().first()

    async def set_comments_disabled(self, post: Post, comments_disabled: bool):
        post.comments_disabled = comments_disabled
        await self.session.commit()

    async def add_comment(self, post_id: str, user_id, content: str):
        comment = Comment(post_id=post_id, user_id=user_id, content=content)
        self.session.add(comment)
        await self.session.commit()
        return await self.get_comment(comment.id)

    async def get_comment(self, comment_id: str):
        result = await self.session.execute(
            select(Comment)
            .options(selectinload(Comment.user), selectinload(Comment.post))
            .where(Comment.id == comment_id)
        )
        return result.scalars().first()

    async def get_comments(self, post_id: str):
        result = await self.session.execute(
            select(Comment)
            .options(selectinload(Comment.user))
            .where(Comment.post_id == post_id)
            .order_by(Comment.created_at)
        )
        return result.scalars().all()

    async def get_comment_counts(self, post_ids: list[str]):
        result = await self.session.execute(
            select(Comment.post_id, func.count())
            .where(Comment.post_id.in_(post_ids))
            .group_by(Comment.post_id)
        )
        return dict(result.all())

    async def set_reaction(self, model, key: dict, reaction: str):
        existing = await self.session.get(model, key)
        if existing is None:
            self.session.add(model(**key, reaction=reaction))
            try:
                await self.session.commit()
                return
            except IntegrityError:
                # A concurrent request from this user inserted the row first.
                await self.session.rollback()
                existing = await self.session.get(model, key)
                if existing is None:
                    raise
        existing.reaction = reaction
        await self.session.commit()

    async def clear_reaction(self, model, key: dict):
        await self.session.execute(delete(model).filter_by(**key))
        await self.session.commit()

    async def get_reaction_summaries(self, model, key_column, ids: list[str], user_id):
        summaries = {
            target_id: {"thumbs_up": 0, "thumbs_down": 0, "my_reaction": None}
            for target_id in ids
        }
        counts = await self.session.execute(
            select(key_column, model.reaction, func.count())
            .where(key_column.in_(ids))
            .group_by(key_column, model.reaction)
        )
        for target_id, reaction, count in counts.all():
            field = "thumbs_up" if reaction == ReactionType.UP.value else "thumbs_down"
            summaries[target_id][field] = count

        mine = await self.session.execute(
            select(key_column, model.reaction)
            .where(key_column.in_(ids), model.user_id == user_id)
        )
        for target_id, reaction in mine.all():
            summaries[target_id]["my_reaction"] = reaction
        return summaries

    async def add_post_reaction(self, post_id: str, user_id, reaction: str):
        key = {"post_id": post_id, "user_id": user_id, "reaction": reaction}
        if await self.session.get(PostReaction, key) is not None:
            return
        self.session.add(PostReaction(**key))
        try:
            await self.session.commit()
        except IntegrityError:
            # A concurrent request from this user inserted the row first.
            await self.session.rollback()
            if await self.session.get(PostReaction, key) is None:
                raise

    async def get_post_reaction_summaries(self, post_ids: list[str], user_id):
        summaries = {
            post_id: {"love_count": 0, "collect_count": 0, "loved": False, "collected": False}
            for post_id in post_ids
        }
        counts = await self.session.execute(
            select(PostReaction.post_id, PostReaction.reaction, func.count())
            .where(PostReaction.post_id.in_(post_ids))
            .group_by(PostReaction.post_id, PostReaction.reaction)
        )
        for post_id, reaction, count in counts.all():
            summaries[post_id][f"{reaction}_count"] = count

        mine = await self.session.execute(
            select(PostReaction.post_id, PostReaction.reaction)
            .where(PostReaction.post_id.in_(post_ids), PostReaction.user_id == user_id)
        )
        for post_id, reaction in mine.all():
            field = "loved" if reaction == PostReactionType.LOVE.value else "collected"
            summaries[post_id][field] = True
        return summaries

    async def get_collected_posts(self, user_id):
        result = await self.session.execute(
            select(Post)
            .options(selectinload(Post.user), selectinload(Post.images))
            .join(PostReaction, PostReaction.post_id == Post.id)
            .where(
                PostReaction.user_id == user_id,
                PostReaction.reaction == PostReactionType.COLLECT.value,
                or_(Post.is_private.is_(False), Post.user_id == user_id),
            )
            .order_by(Post.created_at.desc())
        )
        return result.scalars().all()

    async def get_points_awarded(self, key_column, ids: list[str]):
        result = await self.session.execute(
            select(key_column, func.sum(PointTransaction.points))
            .where(
                key_column.in_(ids),
                PointTransaction.source == PointSource.ANSWER.value,
            )
            .group_by(key_column)
        )
        return dict(result.all())

    async def award_answer_points(self, comment: Comment, awarded_by, points: int):
        self.session.add(
            PointTransaction(
                user_id=comment.user_id,
                points=points,
                source=PointSource.ANSWER.value,
                post_id=comment.post_id,
                comment_id=comment.id,
                awarded_by=awarded_by,
            )
        )
        await self.session.commit()

    async def get_point_total(self, user_id):
        result = await self.session.execute(
            select(func.coalesce(func.sum(PointTransaction.points), 0))
            .where(PointTransaction.user_id == user_id)
        )
        return result.scalar_one()

    async def get_point_history(self, user_id):
        result = await self.session.execute(
            select(PointTransaction)
            .where(PointTransaction.user_id == user_id)
            .order_by(PointTransaction.created_at.desc())
        )
        return result.scalars().all()

    async def add_task(self, title: str, description: str, points: int):
        task = Task(title=title, description=description, points=points)
        self.session.add(task)
        await self.session.commit()
        return task

    async def get_task(self, task_id: str):
        return await self.session.get(Task, task_id)

    async def get_tasks(self):
        result = await self.session.execute(select(Task).order_by(Task.created_at))
        return result.scalars().all()

    async def get_completed_task_ids(self, user_id):
        result = await self.session.execute(
            select(PointTransaction.task_id)
            .where(
                PointTransaction.user_id == user_id,
                PointTransaction.task_id.is_not(None),
            )
        )
        return set(result.scalars().all())

    async def complete_task(self, task_id: str, user_id, points: int) -> bool:
        """Record the points; returns False if the user already completed the task."""
        self.session.add(
            PointTransaction(
                user_id=user_id,
                points=points,
                source=PointSource.TASK.value,
                task_id=task_id,
            )
        )
        try:
            await self.session.commit()
        except IntegrityError:
            await self.session.rollback()
            return False
        return True
