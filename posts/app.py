import os.path
import shutil
import tempfile
import uuid
from typing import Annotated

from posts.dependencies import get_post_service
from posts.idempotency import Idempotency, file_digest, get_idempotency
from posts.service import PostService
from posts.users import current_active_user, current_superuser
from fastapi import HTTPException, UploadFile, File, Form, Depends, APIRouter, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from posts.db import get_async_session, Post, PostImage, User
from posts.images import imagekit
from posts.schema import (
    CommentCreate,
    PointsAward,
    PostReactionType,
    PostType,
    PostUpdate,
    ReactionUpdate,
    TaskCreate,
)


posts_router = APIRouter(prefix="/posts", tags=["posts"])
comments_router = APIRouter(prefix="/comments", tags=["comments"])
points_router = APIRouter(prefix="/points", tags=["points"])
tasks_router = APIRouter(prefix="/tasks", tags=["tasks"])

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
        comments_disabled: bool = Form(
            False,
            alias="commentsDisabled",
            description="If true, nobody can comment on this post.",
        ),
        user: User = Depends(current_active_user),
        session: AsyncSession = Depends(get_async_session),
        idempotency: Idempotency = Depends(get_idempotency),
):
    try:
        if not files:
            raise HTTPException(status_code=422, detail="At least one image file is required.")

        async def create_post():
            post = Post(
                id=str(uuid.uuid4()),
                caption=caption,
                description=description,
                post_type=post_type.value,
                is_private=is_private,
                comments_disabled=comments_disabled,
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
                "commentsDisabled": post.comments_disabled,
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

        return await idempotency.run(
            user.id,
            {
                "caption": caption,
                "description": description,
                "type": post_type.value,
                "isPrivate": is_private,
                "commentsDisabled": comments_disabled,
                "files": [file_digest(file) for file in files],
            },
            create_post,
        )
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


@posts_router.get("/collected", summary="Posts you have collected")
async def get_collected_posts(
        service: Annotated[PostService, Depends(get_post_service)],
        user: User = Depends(current_active_user),
):
    return await service.get_collected_posts(user.id)


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


@posts_router.patch("/{post_id}", summary="Enable or disable comments on your post")
async def update_post(
        post_id: str,
        body: PostUpdate,
        service: Annotated[PostService, Depends(get_post_service)],
        user: User = Depends(current_active_user),
):
    return await service.update_post(post_id, user.id, body.commentsDisabled)


@posts_router.get("/{post_id}/comments")
async def get_comments(
        post_id: str,
        service: Annotated[PostService, Depends(get_post_service)],
        user: User = Depends(current_active_user),
):
    return await service.get_comments(post_id, user.id)


@posts_router.post("/{post_id}/comments", status_code=201)
async def add_comment(
        post_id: str,
        body: CommentCreate,
        service: Annotated[PostService, Depends(get_post_service)],
        idempotency: Annotated[Idempotency, Depends(get_idempotency)],
        user: User = Depends(current_active_user),
):
    return await idempotency.run(
        user.id,
        {"content": body.content},
        lambda: service.add_comment(post_id, user.id, body.content),
    )


@posts_router.put("/{post_id}/reactions/{reaction}", summary="Love or collect a post")
async def add_post_reaction(
        post_id: str,
        reaction: PostReactionType,
        service: Annotated[PostService, Depends(get_post_service)],
        user: User = Depends(current_active_user),
):
    return await service.add_post_reaction(post_id, user.id, reaction)


@posts_router.delete("/{post_id}/reactions/{reaction}", summary="Remove your love or collect")
async def remove_post_reaction(
        post_id: str,
        reaction: PostReactionType,
        service: Annotated[PostService, Depends(get_post_service)],
        user: User = Depends(current_active_user),
):
    return await service.remove_post_reaction(post_id, user.id, reaction)


@comments_router.put("/{comment_id}/reaction", summary="Thumb a comment up or down")
async def react_to_comment(
        comment_id: str,
        body: ReactionUpdate,
        service: Annotated[PostService, Depends(get_post_service)],
        user: User = Depends(current_active_user),
):
    return await service.react_to_comment(comment_id, user.id, body.reaction)


@comments_router.delete("/{comment_id}/reaction", summary="Remove your thumb from a comment")
async def remove_comment_reaction(
        comment_id: str,
        service: Annotated[PostService, Depends(get_post_service)],
        user: User = Depends(current_active_user),
):
    return await service.react_to_comment(comment_id, user.id, None)


@comments_router.post(
    "/{comment_id}/points",
    summary="Give points to a comment on your question",
    description="Only the question owner can give points, up to 5 in total per question.",
)
async def award_points(
        comment_id: str,
        body: PointsAward,
        service: Annotated[PostService, Depends(get_post_service)],
        idempotency: Annotated[Idempotency, Depends(get_idempotency)],
        user: User = Depends(current_active_user),
):
    return await idempotency.run(
        user.id,
        {"points": body.points},
        lambda: service.award_points(comment_id, user.id, body.points),
    )


@points_router.get("/me", summary="Your point total and how you earned it")
async def get_my_points(
        service: Annotated[PostService, Depends(get_post_service)],
        user: User = Depends(current_active_user),
):
    return await service.get_my_points(user.id)


@tasks_router.get("")
async def get_tasks(
        service: Annotated[PostService, Depends(get_post_service)],
        user: User = Depends(current_active_user),
):
    return await service.get_tasks(user.id)


@tasks_router.post("", status_code=201, summary="Create a task (superusers only)")
async def create_task(
        body: TaskCreate,
        service: Annotated[PostService, Depends(get_post_service)],
        idempotency: Annotated[Idempotency, Depends(get_idempotency)],
        user: User = Depends(current_superuser),
):
    return await idempotency.run(
        user.id,
        body.model_dump(),
        lambda: service.create_task(body.title, body.description, body.points),
    )


@tasks_router.post("/{task_id}/complete", summary="Complete a task and earn its points")
async def complete_task(
        task_id: str,
        service: Annotated[PostService, Depends(get_post_service)],
        idempotency: Annotated[Idempotency, Depends(get_idempotency)],
        user: User = Depends(current_active_user),
):
    return await idempotency.run(
        user.id,
        None,
        lambda: service.complete_task(task_id, user.id),
    )
