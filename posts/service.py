import uuid

from fastapi import HTTPException

from observability.tracing import engagement_traceable
from posts.db import Comment, CommentReaction, PointTransaction, Post, PostReaction
from posts.repository import PostRepository
from posts.schema import MAX_POINTS_PER_QUESTION, PostType, ReactionType


class PostService:

    def __init__(self, repository: PostRepository):
        self.repository = repository

    async def get_my_posts(self, user_id: uuid.UUID | str):
        user_uuid = uuid.UUID(str(user_id))
        rows = await self.repository.get_posts(user_id=user_uuid)

        return {"posts": await self._serialize_posts(rows, user_uuid)}

    async def search_posts(self, user_id: uuid.UUID, post_type: PostType):
        rows = await self.repository.search_posts(
            post_type=post_type.value,
        )
        return {"posts": await self._serialize_posts(rows, user_id)}

    async def search_public_posts(
        self,
        user_id: uuid.UUID | str,
        post_type: PostType | str | None = None,
    ):
        user_uuid = uuid.UUID(str(user_id))
        type_value = post_type.value if isinstance(post_type, PostType) else post_type
        rows = await self.repository.search_public_posts(post_type=type_value)
        return {"posts": await self._serialize_posts(rows, user_uuid)}

    async def _serialize_posts(self, posts: list[Post], user_id: uuid.UUID):
        post_ids = [post.id for post in posts]
        reactions = await self.repository.get_reaction_summaries(
            PostReaction, PostReaction.post_id, post_ids, user_id
        )
        comment_counts = await self.repository.get_comment_counts(post_ids)
        points_awarded = await self.repository.get_points_awarded(
            PointTransaction.post_id, post_ids
        )
        return [
            self._serialize_post(
                post,
                user_id,
                reactions[post.id],
                comment_counts.get(post.id, 0),
                points_awarded.get(post.id, 0),
            )
            for post in posts
        ]

    @staticmethod
    def _serialize_post(
        post: Post,
        user_id: uuid.UUID,
        reactions: dict,
        comment_count: int,
        points_awarded: int,
    ):
        is_question = post.post_type == PostType.QUESTION.value
        return {
            "id": post.id,
            "user_id": str(post.user_id),
            "caption": post.caption,
            "description": post.description,
            "type": post.post_type,
            "isPrivate": post.is_private,
            "commentsDisabled": post.comments_disabled,
            "comment_count": comment_count,
            **reactions,
            "points_awarded": points_awarded,
            "points_remaining": (
                MAX_POINTS_PER_QUESTION - points_awarded if is_question else None
            ),
            "created_at": post.created_at,
            "is_owner": str(post.user_id) == str(user_id),
            "email": post.user.email if post.user is not None else "Unknown",
            "images": [
                {
                    "id": image.id,
                    "url": image.url,
                    "file_name": image.file_name,
                    "file_type": image.file_type,
                    "position": image.position,
                }
                for image in post.images
            ],
        }

    async def delete_post(self, post_id: str, user_id: uuid.UUID | str):
        await self.repository.delete_post(post_id, uuid.UUID(str(user_id)))

    async def _get_visible_post(self, post_id: str, user_id: uuid.UUID, lock: bool = False):
        """Private posts look like they don't exist to anyone but their owner."""
        post = await self.repository.get_post(post_id, lock=lock)
        if post is None or (post.is_private and post.user_id != user_id):
            raise HTTPException(status_code=404, detail=f"Post {post_id} not found")
        return post

    async def _get_visible_comment(self, comment_id: str, user_id: uuid.UUID):
        comment = await self.repository.get_comment(comment_id)
        if comment is None or (comment.post.is_private and comment.post.user_id != user_id):
            raise HTTPException(status_code=404, detail=f"Comment {comment_id} not found")
        return comment

    @engagement_traceable("Update Post Comment Setting")
    async def update_post(self, post_id: str, user_id: uuid.UUID, comments_disabled: bool):
        post = await self._get_visible_post(post_id, user_id)
        if post.user_id != user_id:
            raise HTTPException(status_code=403, detail="Only the post owner can change this setting")
        await self.repository.set_comments_disabled(post, comments_disabled)
        return {"id": post.id, "commentsDisabled": post.comments_disabled}

    @engagement_traceable("Add Comment")
    async def add_comment(self, post_id: str, user_id: uuid.UUID, content: str):
        post = await self._get_visible_post(post_id, user_id)
        if post.comments_disabled:
            raise HTTPException(status_code=403, detail="Comments are disabled for this post")
        comment = await self.repository.add_comment(post.id, user_id, content)
        return (await self._serialize_comments([comment], user_id))[0]

    @engagement_traceable("Get Comments")
    async def get_comments(self, post_id: str, user_id: uuid.UUID):
        post = await self._get_visible_post(post_id, user_id)
        comments = await self.repository.get_comments(post.id)
        return {"comments": await self._serialize_comments(comments, user_id)}

    async def _serialize_comments(self, comments: list[Comment], user_id: uuid.UUID):
        comment_ids = [comment.id for comment in comments]
        reactions = await self.repository.get_reaction_summaries(
            CommentReaction, CommentReaction.comment_id, comment_ids, user_id
        )
        points_awarded = await self.repository.get_points_awarded(
            PointTransaction.comment_id, comment_ids
        )
        return [
            {
                "id": comment.id,
                "post_id": comment.post_id,
                "user_id": str(comment.user_id),
                "email": comment.user.email if comment.user is not None else "Unknown",
                "content": comment.content,
                "created_at": comment.created_at,
                "is_owner": comment.user_id == user_id,
                **reactions[comment.id],
                "points_awarded": points_awarded.get(comment.id, 0),
            }
            for comment in comments
        ]

    @engagement_traceable("React To Post")
    async def react_to_post(self, post_id: str, user_id: uuid.UUID, reaction: ReactionType | None):
        post = await self._get_visible_post(post_id, user_id)
        return await self._apply_reaction(
            PostReaction, PostReaction.post_id, {"post_id": post.id, "user_id": user_id}, reaction
        )

    @engagement_traceable("React To Comment")
    async def react_to_comment(self, comment_id: str, user_id: uuid.UUID, reaction: ReactionType | None):
        comment = await self._get_visible_comment(comment_id, user_id)
        return await self._apply_reaction(
            CommentReaction,
            CommentReaction.comment_id,
            {"comment_id": comment.id, "user_id": user_id},
            reaction,
        )

    async def _apply_reaction(self, model, key_column, key: dict, reaction: ReactionType | None):
        target_id = key[key_column.key]
        if reaction is None:
            await self.repository.clear_reaction(model, key)
        else:
            await self.repository.set_reaction(model, key, reaction.value)
        summaries = await self.repository.get_reaction_summaries(
            model, key_column, [target_id], key["user_id"]
        )
        return summaries[target_id]

    @engagement_traceable("Award Points")
    async def award_points(self, comment_id: str, user_id: uuid.UUID, points: int):
        comment = await self._get_visible_comment(comment_id, user_id)
        # The row lock makes concurrent awards on one post take turns, so they
        # can't both pass the budget check below.
        post = await self._get_visible_post(comment.post_id, user_id, lock=True)
        if post.post_type != PostType.QUESTION.value:
            raise HTTPException(status_code=400, detail="Points can only be given on question posts")
        if post.user_id != user_id:
            raise HTTPException(status_code=403, detail="Only the question owner can give points")
        if comment.user_id == user_id:
            raise HTTPException(status_code=400, detail="You can't give points to your own comment")

        awarded = await self.repository.get_points_awarded(PointTransaction.post_id, [post.id])
        remaining = MAX_POINTS_PER_QUESTION - awarded.get(post.id, 0)
        if points > remaining:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"A question can give at most {MAX_POINTS_PER_QUESTION} points; "
                    f"{remaining} remaining"
                ),
            )

        await self.repository.award_answer_points(comment, user_id, points)
        return {
            "comment_id": comment.id,
            "user_id": str(comment.user_id),
            "points": points,
            "points_remaining": remaining - points,
        }

    @engagement_traceable("Get My Points")
    async def get_my_points(self, user_id: uuid.UUID):
        history = await self.repository.get_point_history(user_id)
        return {
            "total": await self.repository.get_point_total(user_id),
            "history": [
                {
                    "id": entry.id,
                    "points": entry.points,
                    "source": entry.source,
                    "post_id": entry.post_id,
                    "comment_id": entry.comment_id,
                    "task_id": entry.task_id,
                    "created_at": entry.created_at,
                }
                for entry in history
            ],
        }

    @engagement_traceable("Create Task")
    async def create_task(self, title: str, description: str, points: int):
        task = await self.repository.add_task(title, description, points)
        return self._serialize_task(task, completed=False)

    @engagement_traceable("Get Tasks")
    async def get_tasks(self, user_id: uuid.UUID):
        tasks = await self.repository.get_tasks()
        completed = await self.repository.get_completed_task_ids(user_id)
        return {"tasks": [self._serialize_task(task, task.id in completed) for task in tasks]}

    @engagement_traceable("Complete Task")
    async def complete_task(self, task_id: str, user_id: uuid.UUID):
        task = await self.repository.get_task(task_id)
        if task is None:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
        points = task.points
        if not await self.repository.complete_task(task_id, user_id, points):
            raise HTTPException(status_code=409, detail="You have already completed this task")
        return {
            "task_id": task_id,
            "points": points,
            "total": await self.repository.get_point_total(user_id),
        }

    @staticmethod
    def _serialize_task(task, completed: bool):
        return {
            "id": task.id,
            "title": task.title,
            "description": task.description,
            "points": task.points,
            "completed": completed,
        }
