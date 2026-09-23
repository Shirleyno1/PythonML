import asyncio

from fastmcp import Client


client = Client("http://localhost:8080/mcp")

async def main():
    async with client:
        tools = await client.list_tools()

        for tool in tools:
            print(tool.name)

        result = await client.call_tool(
            "search_posts",
            {
                "user_id": "8ab40467-7cee-4f87-8cf6-b8852462c826"
            }
        )

        print(result)


if __name__ == "__main__":
    asyncio.run(main())
