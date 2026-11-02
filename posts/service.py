import uuid

from posts.db import User, Post
from posts.repository import PostRepository
from posts.schema import PostType


class PostService:

    def __init__(self, repository: PostRepository):
        self.repository = repository

    async def get_my_posts(self, user_id: uuid.UUID | str):
        user_uuid = uuid.UUID(str(user_id))
        rows = await self.repository.get_posts(user_id=user_uuid)

        return {"posts": [self._serialize_post(post, user_uuid) for post in rows]}

    async def search_posts(self, user_id: uuid.UUID, post_type: PostType):
        rows = await self.repository.search_posts(
            post_type=post_type.value,
        )
        return {"posts": [self._serialize_post(post, user_id) for post in rows]}

    async def search_public_posts(
        self,
        user_id: uuid.UUID | str,
        post_type: PostType | str | None = None,
    ):
        user_uuid = uuid.UUID(str(user_id))
        type_value = post_type.value if isinstance(post_type, PostType) else post_type
        rows = await self.repository.search_public_posts(post_type=type_value)
        return {"posts": [self._serialize_post(post, user_uuid) for post in rows]}

    @staticmethod
    def _serialize_post(post: Post, user_id: uuid.UUID):
        return {
            "id": post.id,
            "user_id": str(post.user_id),
            "caption": post.caption,
            "description": post.description,
            "type": post.post_type,
            "isPrivate": post.is_private,
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
