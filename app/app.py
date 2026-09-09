import os.path
import shutil
import tempfile
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import create_db_tables, get_async_session, Post
from app.images import imagekit


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_db_tables()
    yield
app = FastAPI(lifespan=lifespan)

@app.post("/upload")
async def upload_file(
        file: UploadFile = File(...),
        caption: str = Form(),
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

        if upload_result.metadata.status.code == 200:
        # if True:
            post = Post(
                caption=caption,
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


@app.get("/feed")
async def get_feed(
        session: AsyncSession = Depends(get_async_session),
):
    result = await session.execute(select(Post).order_by(Post.created_at.desc()))
    posts = [row[0] for row in result.all()]
    posts_data = []
    for post in posts:
        posts_data.append(
            {
                "id": post,
                "caption": post.caption,
                "url": post.url,
                "file_name": post.file_name,
                "file_type": post.file_type,
                "created_at": post.created_at,
            }
        )
    return {"posts": posts_data}