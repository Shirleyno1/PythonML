import os.path
import shutil
import tempfile
import uuid

from posts.users import current_active_user
from fastapi import HTTPException, UploadFile, File, Form, Depends, APIRouter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from posts.db import get_async_session, Post, User
from posts.images import imagekit


posts_router = APIRouter(prefix="/posts", tags=["posts"])

@posts_router.post("/upload")
async def upload_file(
        file: UploadFile = File(...),
        caption: str = Form(""),
        user: User = Depends(current_active_user),
        session: AsyncSession = Depends(get_async_session),
):
    temp_file_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as temp_file:
            temp_file_path = temp_file.name
            shutil.copyfileobj(file.file, temp_file)

        upload_result = imagekit.files.upload(
            file = open(temp_file_path, "rb"),
            file_name = file.filename,
        )

        if upload_result.url:
        # if True:
            post = Post(
                caption=caption,
                user_id=user.id,
                url = upload_result.url,
                file_type="video" if file.content_type.startswith("video") else "image",
                file_name=upload_result.name,
            )
            session.add(post)
            await  session.commit()
            await session.refresh(post)
            return post

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            os.unlink(temp_file_path)
        file.file.close()


@posts_router.get("/")
async def get_posts(
        session: AsyncSession = Depends(get_async_session),
        user: User = Depends(current_active_user),
):
    result = await session.execute(select(Post).order_by(Post.created_at.desc()))
    posts = [row[0] for row in result.all()]
    posts_data = []

    result = await session.execute(select(User))
    users = [row[0] for row in result.all()]
    user_dict = {u.id: u.email for u in users}
    for post in posts:
        posts_data.append(
            {
                "id": post.id,
                "user_id": str(post.user_id),
                "caption": post.caption,
                "url": post.url,
                "file_name": post.file_name,
                "file_type": post.file_type,
                "created_at": post.created_at,
                "is_owner": post.user_id == user.id,
                "email": user_dict.get(post.user_id, "Unknown"),
            }
        )
    return {"posts": posts_data}

@posts_router.delete("/{post_id}")
async def delete_post(
        post_id: str,
        session: AsyncSession = Depends(get_async_session),
        user: User = Depends(current_active_user),
):
    try:
        uuid.UUID(post_id)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid post_id format: {post_id}")

    result = await session.execute(select(Post).where(Post.id == post_id))
    post = result.scalars().first()

    if not post:
        raise HTTPException(status_code=404, detail=f"Post {post_id} not found")

    if post.user_id != user.id:
        raise HTTPException(status_code=403, detail="You don't have permission to delete this post")

    await session.delete(post)
    await session.commit()
    return {"message": "Post deleted successfully"}
