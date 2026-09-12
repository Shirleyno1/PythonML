import uuid
from typing import Optional

import fastapi_users
from fastapi import Depends, FastAPI, Request, Response, status
from fastapi_users import UUIDIDMixin, BaseUserManager, models, FastAPIUsers
from fastapi_users.authentication import BearerTransport, JWTStrategy, AuthenticationBackend
from fastapi_users_db_sqlalchemy import SQLAlchemyUserDatabase

from posts.db import User, get_user_db

SECRET = ""


class UserManager(UUIDIDMixin, BaseUserManager[User, uuid.UUID]):
    reset_password_token_secret = SECRET
    verification_token_secret = SECRET

    async def on_after_register(self, user: User, request: Optional[Request] = None) -> None:
        print(f'User {user} has registered')

    async def on_after_forgot_password(self, user: User, request: Optional[Request] = None) -> None:
        print(f'User {user} has forgot their password')

    # async def on_after_login(self, user: User, request: Optional[Request] = None) -> None:
    #     print(f'User {user} has logged in')

    async def on_logout(self, user: User, request: Optional[Request] = None) -> None:
        print(f'User {user} has logged out')

    async def on_after_request_verify(self, user: models.UP, token: str, request: Optional[Request] = None) -> None:
        print(f'User {user} has logged in')

async def get_user_manager(user_db: SQLAlchemyUserDatabase = Depends(get_user_db)):
    yield UserManager(user_db)

bear_transport = BearerTransport(tokenUrl="auth/jwt/login")

def get_jwt_strategy():
    return JWTStrategy(secret=SECRET, lifetime_seconds=3600)

auth_backend = AuthenticationBackend(
    name="jwt",
    transport=bear_transport,
    get_strategy=get_jwt_strategy,
)

fastapi_users = FastAPIUsers[User, uuid.UUID](get_user_manager, [auth_backend])

current_active_user = fastapi_users.current_user(active=True)