from posts.db import User, Post
from posts.repository import PostRepository


class PostService:

    def __init__(self, repository: PostRepository):
        self.repository = repository

    async def get_posts(self, user_id: str):
        rows = await self.repository.get_posts()

        posts_data = [
            {
                "id": post.id,
                "user_id": str(post.user_id),
                "caption": post.caption,
                "description": post.description,
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
            for post in rows
        ]

        return {"posts": posts_data}

    async def delete_post(self, post_id: str, user_id: int):
        await self.repository.delete_post(post_id, user_id)
