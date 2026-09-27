from langchain_core.tools import tool

from mcp_server.dependencies import get_post_service


@tool
async def search_posts(user_id: str) -> list:
    """Search posts using a text query"""

    async with get_post_service() as service:
        result = await service.get_posts(user_id)
        return result["posts"]

# @tool
# async def langchain_rag(question: str):
#
