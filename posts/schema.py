import uuid
from enum import Enum
from typing import Annotated

from fastapi_users import schemas
from pydantic import BaseModel, Field, StringConstraints

MAX_POINTS_PER_QUESTION = 5


class PostType(str, Enum):
    SHARE = "share"
    QUESTION = "question"


class ReactionType(str, Enum):
    UP = "up"
    DOWN = "down"


class PointSource(str, Enum):
    ANSWER = "answer"
    TASK = "task"


class PostUpdate(BaseModel):
    commentsDisabled: bool


class CommentCreate(BaseModel):
    content: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=5000)
    ]


class ReactionUpdate(BaseModel):
    reaction: ReactionType


class PointsAward(BaseModel):
    points: int = Field(ge=1, le=MAX_POINTS_PER_QUESTION)


class TaskCreate(BaseModel):
    title: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)
    ]
    description: str = ""
    points: int = Field(ge=1, le=1000)


class PostCreate(BaseModel):
    title: str
    content: str

class PostReponse(BaseModel):
    title: str
    content: str

class UserRead(schemas.BaseUser[uuid.UUID]):
    pass

class UserCreate(schemas.BaseUserCreate):
    pass

class UserUpdate(schemas.BaseUserUpdate):
    pass
