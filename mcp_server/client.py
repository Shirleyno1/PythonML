from fastmcp import Client


class MCPClient:

    def __init__(self, server_url: str):
        self.client = Client(server_url)

    async def __aenter__(self):
        await self.client.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return await self.client.__aexit__(exc_type, exc, tb)

    async def list_tools(self):
        """ List all the available tools
        Use list_tools_mcp if tools number is too large and use pagination"""

        tools = await self.client.list_tools()
        return tools

    async def call_tool(self, name: str, arguments: dict):
        return await self.client.call_tool(name, arguments)

# client = Client("http://localhost:8080/mcp")


