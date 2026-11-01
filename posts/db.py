from datetime import datetime
import uuid
from collections.abc import AsyncGenerator

from dotenv import load_dotenv
from fastapi_users.db import SQLAlchemyUserDatabase, SQLAlchemyBaseUserTableUUID
from fastapi import Depends
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, inspect, text
from sqlalchemy.dialects.postgresql.base import UUID
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase, relationship
import os

from posts.schema import PostType

DEFAULT_URL = "sqlite+aiosqlite:///test1.db"
load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
     DEFAULT_URL,
)

class Base(DeclarativeBase):
    pass

class User(SQLAlchemyBaseUserTableUUID, Base):
    posts = relationship("Post", back_populates="user")


class Post(Base):
    __tablename__ = "posts"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(UUID(as_uuid=True), ForeignKey("user.id"), nullable=False)
    caption = Column(Text)
    description = Column(Text)
    post_type = Column(
        "type",
        String,
        nullable=False,
        default=PostType.SHARE.value,
        server_default=PostType.SHARE.value,
    )
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="posts")
    images = relationship(
        "PostImage",
        back_populates="post",
        cascade="all, delete-orphan",
        order_by="PostImage.position",
    )


class PostImage(Base):
    __tablename__ = "post_images"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    post_id = Column(String, ForeignKey("posts.id", ondelete="CASCADE"), nullable=False, index=True)
    url = Column(Text, nullable=False)
    file_name = Column(String, nullable=False)
    file_type = Column(String, nullable=False)
    position = Column(Integer, nullable=False, default=0)

    post = relationship("Post", back_populates="images")


def _as_uuid(value):
    if isinstance(value, uuid.UUID):
        return value
    text_value = str(value)
    if len(text_value) == 32:
        text_value = (
            f"{text_value[0:8]}-{text_value[8:12]}-{text_value[12:16]}-"
            f"{text_value[16:20]}-{text_value[20:32]}"
        )
    return uuid.UUID(text_value)


def _as_datetime(value):
    if value is None or isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value))


def migrate_legacy_posts(connection):
    """Move one-image posts into a post with an image list.

    Older rows stored the file on the post and repeated the caption for every
    image. The caption now belongs to the post, and each file is a PostImage.
    """
    inspector = inspect(connection)
    tables = set(inspector.get_table_names())
    if "posts" not in tables:
        return

    columns = {column["name"] for column in inspector.get_columns("posts")}
    if "url" not in columns:
        return

    rows = connection.execute(
        text(
            "SELECT id, user_id, caption, url, file_name, file_type, created_at "
            "FROM posts"
        )
    ).mappings().all()

    if "post_images" in tables:
        connection.execute(text("DROP TABLE post_images"))
    connection.execute(text("DROP TABLE posts"))
    Post.__table__.create(connection)
    PostImage.__table__.create(connection)

    for row in rows:
        post_id = str(row["id"])
        connection.execute(
            Post.__table__.insert(),
            {
                "id": post_id,
                "user_id": _as_uuid(row["user_id"]),
                "caption": row["caption"],
                "created_at": _as_datetime(row["created_at"]),
            },
        )
        connection.execute(
            PostImage.__table__.insert(),
            {
                "id": str(uuid.uuid4()),
                "post_id": post_id,
                "url": row["url"],
                "file_name": row["file_name"],
                "file_type": row["file_type"],
                "position": 0,
            },
        )


engine = create_async_engine(DATABASE_URL)
async_session_maker = async_sessionmaker(engine, expire_on_commit=False)


async def create_db_tables():
    async with engine.begin() as conn:
        await conn.run_sync(migrate_legacy_posts)
        await conn.run_sync(_ensure_post_metadata_columns)
        await conn.run_sync(Base.metadata.create_all)


def _ensure_post_metadata_columns(connection):
    inspector = inspect(connection)
    if "posts" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("posts")}
    if "description" not in columns:
        connection.execute(text("ALTER TABLE posts ADD COLUMN description TEXT"))
    if "type" not in columns:
        connection.execute(
            text("ALTER TABLE posts ADD COLUMN type VARCHAR NOT NULL DEFAULT 'share'")
        )


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session

async def get_user_db(session: AsyncSession = Depends(get_async_session)):
    yield SQLAlchemyUserDatabase(session, User)
