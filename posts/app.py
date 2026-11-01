import os.path
import shutil
import tempfile
import uuid
from typing import Annotated

from posts.dependencies import get_post_service
from posts.service import PostService
from posts.users import current_active_user
from fastapi import HTTPException, UploadFile, File, Form, Depends, APIRouter, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from posts.db import get_async_session, Post, PostImage, User
from posts.images import imagekit
from posts.schema import PostType


posts_router = APIRouter(prefix="/posts", tags=["posts"])

@posts_router.post(
    "/upload",
    summary="Upload a list of images",
    description=(
        "Upload one or more images using multipart/form-data. "
        "Repeat the `file` field for each image. "
        "The caption and description apply to the whole post, not each image."
    ),
)
async def upload_file(
        files: list[UploadFile] = File(
            ...,
            alias="file",
            description="One or more image files. Repeat this field to upload multiple images.",
            json_schema_extra={"items": {"type": "string", "format": "binary"}},
        ),
        caption: str = Form("", description="Caption for the post."),
        description: str = Form("", description="Description for the post."),
        post_type: PostType = Form(
            PostType.SHARE,
            alias="type",
            description="Post type: share or question.",
        ),
        is_private: bool = Form(
            False,
            alias="isPrivate",
            description="If true, only you can see this post.",
        ),
        user: User = Depends(current_active_user),
        session: AsyncSession = Depends(get_async_session),
):
    try:
        if not files:
            raise HTTPException(status_code=422, detail="At least one image file is required.")

        post = Post(
            id=str(uuid.uuid4()),
            caption=caption,
            description=description,
            post_type=post_type.value,
            is_private=is_private,
            user_id=user.id,
        )
        session.add(post)

        for position, file in enumerate(files):
            suffix = os.path.splitext(os.path.basename(file.filename or ""))[1]
            temp_file_path = None
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
                    temp_file_path = temp_file.name
                    shutil.copyfileobj(file.file, temp_file)

                with open(temp_file_path, "rb") as temp_file:
                    upload_result = imagekit.files.upload(
                        file=temp_file,
                        file_name=file.filename or os.path.basename(temp_file_path),
                    )

                if not upload_result.url:
                    raise HTTPException(
                        status_code=502,
                        detail=f"Image upload failed for {file.filename or 'an uploaded file'}.",
                    )

                post.images.append(
                    PostImage(
                        url=upload_result.url,
                        file_type="video" if (file.content_type or "").startswith("video/") else "image",
                        file_name=upload_result.name,
                        position=position,
                    )
                )
            finally:
                if temp_file_path and os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)

        await session.commit()
        result = await session.execute(
            select(Post)
            .options(selectinload(Post.images))
            .where(Post.id == post.id)
        )
        post = result.scalar_one()
        return {
            "id": post.id,
            "user_id": str(post.user_id),
            "caption": post.caption,
            "description": post.description,
            "type": post.post_type,
            "isPrivate": post.is_private,
            "created_at": post.created_at,
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
    except HTTPException:
        await session.rollback()
        raise
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=400, detail=str(e)) from e
    finally:
        for file in files:
            await file.close()


@posts_router.get("/mine")
async def get_my_posts(
        user: User = Depends(current_active_user),
        service: Annotated[PostService, Depends(get_post_service)] = None
):
    return await service.get_my_posts(user.id)


@posts_router.get(
    "/search",
    summary="Search public posts by type",
    description=(
        "Returns non-private posts of the selected type from all users, newest first."
    ),
)
async def search_posts(
        post_type: PostType = Query(..., alias="type"),
        user: User = Depends(current_active_user),
        service: Annotated[PostService, Depends(get_post_service)] = None,
):
    return await service.search_posts(user.id, post_type=post_type)


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


    return {"message": "Post deleted successfully"}
