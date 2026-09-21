from posts.db import User, Post
from posts.repository import PostRepository


class PostService:

    def __init__(self, repository: PostRepository):
        self.repository = repository

    async def get_posts(self, user: User):
        rows = await self.repository.get_posts()

        posts_data = [
            {
                "id": post.id,
                "user_id": str(post.user_id),
                "caption": post.caption,
                "file_name": post.file_name,
                "file_type": post.file_type,
                "created_at": post.created_at,
                "is_owner": post.user_id == user.id,
                "email": post.user.email if post.user else "Unknown",
            }
            for post in rows
        ]

        return {"posts": posts_data}
