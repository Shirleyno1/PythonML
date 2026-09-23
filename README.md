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
                    "type": "function_call_output",
                    "call_id": tool_call_id,
                    "output": tool_result,
                }
            ],
            tools=tools,
        )
```

The wrapper keeps OpenAI-specific code separate from the agent orchestration logic.

---

# Agent Orchestrator

The `AgentOrchestrator` coordinates the complete AI workflow.

```text
chatbot/
├── main.py
├── orchestrator.py
├── openai_client.py
└── ...
```

Its responsibilities are:

```text
AgentOrchestrator
│
├── Discover MCP tools
│
├── Convert MCP schemas
│   → OpenAI tool schemas
│
├── Send user message + tools to OpenAI
│
├── Detect function calls
│
├── Extract:
│   ├── name
│   ├── arguments
│   └── call_id
│
├── Execute MCP tool
│
├── Send tool result back to OpenAI
│
└── Return final answer
```

The Responses API function-call identifier is:

```python
tool_call["call_id"]
```

This `call_id` must be used when returning the corresponding `function_call_output`.

Example:

```python
tool_name = tool_call["name"]

arguments = json.loads(
    tool_call["arguments"]
)

tool_call_id = tool_call["call_id"]
```

Then:

```python
result = await self.mcp_client.call_tool(
    name=tool_name,
    arguments=arguments,
)
```

The result is sent back to OpenAI using the same call ID.

---

# Agent Tool-Calling Loop

The core agent behavior is:

```python
response = await self.openai_client.create_response(
    message=message,
    tools=openai_tools,
)
```

The orchestrator checks whether the model requested a tool.

```text
                    OpenAI
                       │
                       ▼
                 Response
                       │
             ┌─────────┴─────────┐
             │                   │
        No function call    Function call
             │                   │
             ▼                   ▼
       Final answer         Extract tool
                                  │
                                  ▼
                            MCPClient
                                  │
                                  ▼
                            MCP Server
                                  │
                                  ▼
                             Tool result
                                  │
                                  ▼
                                OpenAI
                                  │
                                  ▼
                            Final answer
```

This creates an agent loop where the model can decide which available backend capability it needs.

---

# Example

User:

```text
Find my restaurant posts
```

The model may decide to call:

```text
search_posts
```

with arguments such as:

```json
{
  "query": "restaurant"
}
```

The orchestrator executes:

```python
await self.mcp_client.call_tool(
    name="search_posts",
    arguments={
        "query": "restaurant"
    },
)
```

The MCP server executes the actual backend operation.

The result is then returned to OpenAI so that the model can produce the final natural-language response.

---

# FastAPI Endpoint

The chatbot is exposed through:

```text
POST /ai/mcp
```

The endpoint authenticates the user and passes the message to the orchestrator:

```python
@app.post("/ai/mcp")
async def ai_mcp(
    request: ChatRequest,
    session: AsyncSession = Depends(
        get_async_session
    ),
    user: User = Depends(current_active_user),
):
    result = await orchestrator.run_agent(
        message=request.message
    )

    return result
```

The router itself does not contain the agent logic.

Instead:

```text
FastAPI Router
      │
      ▼
AgentOrchestrator
```

This keeps API-layer responsibilities separate from AI orchestration.

---

# Configuration

The MCP server URL should be configuration rather than hard-coded throughout the application.

Example `.env`:

```env
OPENAI_API_KEY=your-openai-api-key
MCP_SERVER_URL=http://localhost:8001/mcp
JWT_SECRET=your-long-random-secret
```

The `.env` file should not be committed:

```gitignore
.env
```

The application can then inject the configuration into the MCP client:

```python
mcp_client = MCPClient(
    server_url=settings.mcp_server_url
)
```

---

# Running the Application

## 1. Start the MCP server

Start the FastMCP server using the project's MCP server entry point.

The MCP endpoint should be available at:

```text
http://localhost:8001/mcp
```

## 2. Start FastAPI

```bash
uvicorn chatbot.main:app \
    --reload \
    --port 8080 \
    --host 0.0.0.0
```

The FastAPI application will be available on:

```text
http://localhost:8080
```

## 3. Authenticate

Use the existing authentication endpoint:

```text
POST /auth/jwt/login
```

## 4. Call the MCP-enabled chatbot

```text
POST /ai/mcp
```

Example request:

```json
{
  "message": "Find my restaurant posts"
}
```

---

# Project Structure

Current relevant structure:

```text
practice/
│
├── chatbot/
│   ├── main.py
│   ├── orchestrator.py
│   ├── openai_client.py
│   └── ...
│
├── mcp_server/
│   ├── client.py
│   ├── schema_adapter.py
│   └── ...
│
├── rag/
│   ├── chunking.py
│   ├── documents.py
│   ├── embeddings.py
│   ├── generation.py
│   ├── retrival.py
│   ├── service.py
│   └── vector_store.py
│
├── .env
└── README.md
```

---

# Key Design Concepts Learned

## MCP

Model Context Protocol provides a standard way for an AI application to discover and interact with external tools and capabilities.

In this project:

```text
Agent
  ↓
MCP Client
  ↓
MCP Server
  ↓
Backend functionality
```

## Tool Discovery

The agent does not need to know every backend tool in advance.

It discovers them through:

```python
await mcp_client.list_tools()
```

## Schema Adaptation

The MCP tool definition is converted into a schema that the OpenAI model can understand:

```text
MCP Tool Schema
      ↓
SchemaAdapter
      ↓
OpenAI Function Tool Schema
```

## Orchestration

The `AgentOrchestrator` coordinates:

```text
LLM
 ↓
Tool selection
 ↓
MCP execution
 ↓
Tool result
 ↓
LLM
 ↓
Final response
```

This is the central component connecting the model with external capabilities.

---

# Troubleshooting

### Address already in use

If you see:

```text
[Errno 48] Address already in use
```

make sure the MCP server and FastAPI application are not using the same port.

Recommended:

```text
MCP Server → 8001
FastAPI    → 8080
```

### MCP 404 Not Found

If you see:

```text
POST http://localhost:8080/mcp
404 Not Found
```

the MCP client is connecting to the FastAPI server instead of the MCP server.

Check:

```env
MCP_SERVER_URL=http://localhost:8001/mcp
```

### MCP Client is not connected

If you see:

```text
RuntimeError:
Client is not connected.
```

the FastMCP client needs to be used inside its async context:

```python
async with self.mcp_client:
    tools = await self.mcp_client.list_tools()
```

### OpenAI `create_response` does not exist

If you see:

```text
AttributeError:
'OpenAI' object has no attribute 'create_response'
```

the orchestrator expects the project's `OpenAIClient` wrapper, not the raw OpenAI SDK client.

Use:

```python
openai_client = OpenAIClient(
    api_key=api_key
)
```

### `object Response can't be used in 'await' expression`

Make sure the async wrapper uses:

```python
from openai import AsyncOpenAI
```

and:

```python
self.client = AsyncOpenAI(
    api_key=api_key
)
```

### `tool_call_id` KeyError

For Responses API function calls, use:

```python
tool_call["call_id"]
```

rather than:

```python
tool_call["tool_call_id"]
```

---

# Current AI Architecture

The project has now evolved from a traditional chatbot into an AI application with tool orchestration:

```text
                         ┌───────────────────┐
                         │       User        │
                         └─────────┬─────────┘
                                   │
                                   ▼
                         ┌───────────────────┐
                         │     FastAPI       │
                         │    /ai/mcp        │
                         └─────────┬─────────┘
                                   │
                                   ▼
                     ┌──────────────────────────┐
                     │    AgentOrchestrator     │
                     │                          │
                     │ Tool discovery           │
                     │ Tool selection           │
                     │ Tool execution           │
                     │ Result handling          │
                     └──────┬───────────┬───────┘
                            │           │
                    OpenAI  │           │ MCP
                            │           │
                            ▼           ▼
                    ┌───────────┐  ┌───────────┐
                    │  OpenAI   │  │  FastMCP  │
                    │   Model   │  │   Server  │
                    └───────────┘  └─────┬─────┘
                                         │
                                         ▼
                                  Backend Tools
```

This architecture separates:

* **API layer** — FastAPI
* **AI orchestration** — AgentOrchestrator
* **LLM integration** — OpenAIClient
* **Tool communication** — MCPClient
* **Tool schema conversion** — SchemaAdapter
* **Backend capabilities** — FastMCP tools

The MCP server is now successfully connected to the chatbot, completing the core **LLM → Agent Orchestrator → MCP → Tool → LLM** integration.
