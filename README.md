# AI Practice Project

A FastAPI-based AI application that combines post management, authentication, RAG, and an MCP-based agent architecture.

The project uses **FastAPI + OpenAI + FastMCP + MCP Client** to allow the AI agent to dynamically discover and execute backend tools.

---

## Architecture

The current AI/MCP architecture is:

```text
                         User
                          │
                          ▼
                    FastAPI /ai/mcp
                          │
                          ▼
                 AgentOrchestrator
                    │           │
                    │           │
                    ▼           ▼
              OpenAIClient   MCPClient
                    │           │
                    │           │ MCP
                    │           ▼
                    │      FastMCP Server
                    │           │
                    │           ▼
                    │      Backend Tools
                    │
                    ▼
                 OpenAI
```

The complete tool-calling flow is:

```text
User message
     │
     ▼
AgentOrchestrator
     │
     ├── Discover MCP tools
     │       │
     │       ▼
     │   FastMCP Server
     │
     ├── Convert MCP tool schemas
     │   to OpenAI function schemas
     │
     ▼
OpenAI
     │
     │ function_call
     ▼
AgentOrchestrator
     │
     ▼
MCPClient.call_tool()
     │
     ▼
FastMCP Server
     │
     ▼
Backend tool execution
     │
     ▼
Tool result
     │
     ▼
OpenAI
     │
     ▼
Final response
```

---

# MCP Integration

The project uses **FastMCP** to expose backend functionality as MCP tools.

Current MCP tools include:

```text
search_posts
create_post
delete_post
update_post
```

The chatbot does not need to hard-code these tools individually.

Instead, the agent:

1. Connects to the MCP server.
2. Calls `list_tools()`.
3. Dynamically discovers the available MCP tools.
4. Converts their schemas into OpenAI function-tool schemas.
5. Provides those tools to the OpenAI model.
6. Executes the tool selected by the model through MCP.
7. Sends the tool result back to the model.
8. Returns the final response to the user.

This means that adding another MCP tool can automatically make it available to the agent without adding another hard-coded tool definition to the orchestrator.

---

# MCP Server

The MCP server runs separately from the main FastAPI application.

For local development:

```text
FastAPI application
http://localhost:8080

MCP server
http://localhost:8001/mcp
```

The two applications must use different ports.

For example:

```text
Terminal 1
──────────
MCP Server
localhost:8001


Terminal 2
──────────
FastAPI
localhost:8080
```

The MCP client connects to:

```python
server_url = "http://localhost:8001/mcp"
```

`0.0.0.0` is used for server binding/listening, while the client normally connects using `localhost`.

---

# MCP Client

The project contains an MCP client wrapper:

```text
mcp_server/
└── client.py
```

The client uses the FastMCP `Client` and manages its connection using an asynchronous context manager.

```python
from typing import Any
from fastmcp import Client


class MCPClient:

    def __init__(self, server_url: str):
        self.client = Client(server_url)

    async def __aenter__(self):
        await self.client.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return await self.client.__aexit__(
            exc_type,
            exc,
            tb,
        )

    async def list_tools(self):
        return await self.client.list_tools()

    async def call_tool(
        self,
        name: str,
        arguments: dict[str, Any],
    ):
        return await self.client.call_tool(
            name,
            arguments,
        )
```

The MCP client must be connected before calling `list_tools()` or `call_tool()`:

```python
async with self.mcp_client:
    tools = await self.mcp_client.list_tools()
```

Without the context manager, the FastMCP client raises:

```text
RuntimeError:
Client is not connected.
Use the 'async with client:' context manager first.
```

---

# Schema Adapter

MCP tools use MCP tool schemas, while the OpenAI model expects function-tool schemas.

The project uses a `SchemaAdapter` to bridge these two representations.

```text
mcp_server/
└── schema_adapter.py
```

Example:

```python
class SchemaAdapter:

    @staticmethod
    def mcp_to_openai(mcp_tools):

        openai_tools = []

        for tool in mcp_tools:
            openai_tools.append({
                "type": "function",
                "name": tool.name,
                "description": tool.description or "",
                "parameters": tool.input_schema,
            })

        return openai_tools
```

The important part is that the MCP schema is obtained dynamically:

```python
tool.input_schema
```

rather than manually defining the parameters for every tool.

---

# OpenAI Client

The project wraps the OpenAI SDK in its own `OpenAIClient`.

```text
chatbot/
└── openai_client.py
```

The FastAPI application is asynchronous, so the wrapper uses `AsyncOpenAI`.

```python
from openai import AsyncOpenAI


class OpenAIClient:

    def __init__(self, api_key: str):
        self.client = AsyncOpenAI(
            api_key=api_key
        )

    async def create_response(
        self,
        message: str,
        tools: list,
    ):
        return await self.client.responses.create(
            model="gpt-5-mini",
            input=message,
            tools=tools,
        )

    async def create_response_with_tool_result(
        self,
        response_id: str,
        tool_call_id: str,
        tool_result: str,
        tools: list,
    ):
        return await self.client.responses.create(
            model="gpt-5-mini",
            previous_response_id=response_id,
            input=[
                {
```
