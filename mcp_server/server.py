import asyncio
from typing import Annotated

from fastmcp import FastMCP
from pydantic import Field

from mcp_server.dependencies import get_post_service
from posts.db import create_db_tables
from posts.schema import PostType
from rag.service import get_rag_service

# Chroma's local storage isn't safe to share between processes, and locally this
# server and the API run side by side.
RAG_CHROMA_PATH = "./chroma_db_mcp"

mcp = FastMCP("My first MCP Server")

@mcp.tool
async def search_posts(
    user_id: str,
    post_type: Annotated[PostType | None, Field(description="Optional post type filter: share or question.")] = None,
) -> list[dict]:
    """Search public posts from all users, optionally filtered by type."""

    async with get_post_service() as service:
        result = await service.search_public_posts(user_id, post_type)
        return result["posts"]

@mcp.tool
async def delete_post(post_id: str, user_id: str):
    """Delete one of the authenticated user's own posts."""
    async with get_post_service() as service:
        await service.delete_post(post_id, user_id)


@mcp.tool
async def search_documents(
    query: str,
    top_k: Annotated[int, Field(ge=1, le=5, description="How many passages to return.")] = 3,
) -> list[dict]:
    """Search the reference documents for passages relevant to the query."""

    # Loading the index and embedding the query both block.
    service = await asyncio.to_thread(get_rag_service, RAG_CHROMA_PATH)
    return await asyncio.to_thread(service.search, query, top_k)


if __name__ == "__main__":
    asyncio.run(create_db_tables())
    mcp.run(transport="http", host="0.0.0.0", port=8001)
