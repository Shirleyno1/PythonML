from fastmcp import FastMCP

from mcp_server.dependencies import get_post_service

mcp = FastMCP("My first MCP Server")

@mcp.tool
async def search_posts(user_id: str)-> list[dict]:
    """Search Posts"""

    async with get_post_service() as service:
        result = await service.get_posts(user_id)
        return result["posts"]

@mcp.tool
async def delete_post(post_id: str, user_id: int):
    async with get_post_service() as service:
        await service.delete_post(post_id, user_id)



if __name__ == "__main__":
    mcp.run(
        transport="http",
        host="0.0.0.0",
        port=8001,
    )
