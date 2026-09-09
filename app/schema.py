import uuid

from fastapi_users import schemas
from pydantic import BaseModel


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

