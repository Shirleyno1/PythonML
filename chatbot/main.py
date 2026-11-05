import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI

from chatbot.openai_client import OpenAIClient
from chatbot.orchestrator import AgentOrchestrator
from chatbot.routes import agui, ai, chat, mcp, rag
from common.logging_config import setup_logging
from mcp_server.client import MCPClient
from mcp_server.schema_adapter import SchemaAdapter
from posts.app import comments_router, points_router, posts_router, tasks_router
from posts.db import create_db_tables
from posts.schema import UserCreate, UserRead, UserUpdate
from posts.users import auth_backend, fastapi_users

load_dotenv()
setup_logging()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    await create_db_tables()
    yield


def _include_auth_routers(application: FastAPI) -> None:
    application.include_router(
        fastapi_users.get_auth_router(auth_backend),
        prefix="/auth/jwt",
        tags=["auth"],
    )
    application.include_router(
        fastapi_users.get_register_router(UserRead, UserCreate),
        prefix="/auth",
        tags=["auth"],
    )
    application.include_router(
        fastapi_users.get_reset_password_router(),
        prefix="/auth",
        tags=["auth"],
    )
    application.include_router(
        fastapi_users.get_verify_router(UserRead),
        prefix="/auth",
        tags=["auth"],
    )
    application.include_router(
        fastapi_users.get_users_router(UserRead, UserUpdate),
        prefix="/users",
        tags=["users"],
    )


def configure_agent() -> None:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY must be configured to use AI features.")
    agent = AgentOrchestrator(
        openai_client=OpenAIClient(api_key=api_key),
        mcp_client=MCPClient(
            server_url=os.getenv("MCP_SERVER_URL", "http://localhost:8001/mcp")
        ),
        schema_adapter=SchemaAdapter(),
    )
    mcp.configure_orchestrator(agent)
    agui.configure_orchestrator(agent)


def create_app() -> FastAPI:
    configure_agent()
    application = FastAPI(lifespan=lifespan)
    application.include_router(posts_router)
    application.include_router(comments_router)
    application.include_router(points_router)
    application.include_router(tasks_router)
    application.include_router(chat.router)
    application.include_router(ai.router)
    application.include_router(mcp.router)
    application.include_router(agui.router)
    application.include_router(rag.router)
    _include_auth_routers(application)
    return application


app = create_app()
