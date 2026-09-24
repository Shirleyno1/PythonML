# MCP Server

This package contains the **Model Context Protocol (MCP)** integration for the AI application.

The MCP layer provides a standard interface for exposing application capabilities as tools that can be discovered and called by an AI agent.

In this project, the MCP server exposes backend functionality such as:

```text
search_posts
create_post
update_post
delete_post
```

The AI agent does not need to know how these operations are implemented internally. It interacts with them through MCP.

---

# Architecture

The MCP architecture consists of an MCP client and MCP server.

```text
                    AI Agent
                       │
                       ▼
                 MCP Client
                  client.py
                       │
                       │ MCP protocol
                       ▼
                 MCP Server
                  server.py
                       │
              ┌────────┴────────┐
              ▼                 ▼
        dependencies.py     MCP Tools
              │
              ▼
        Application Services
```

In the current application, the overall architecture is:

```text
User
 │
 ▼
FastAPI
 │
 ▼
AI Service / LangGraph
 │
 ▼
MCP Client
 │
 ▼
FastMCP Server
 │
 ▼
Backend Tools
 │
 ├── search_posts
 ├── create_post
 ├── update_post
 └── delete_post
```

---

# Files

## `server.py`

Defines and starts the MCP server.

The server is responsible for:

* creating the FastMCP application
* registering MCP tools
* exposing the MCP endpoint
* connecting MCP tools to application functionality

Conceptually:

```text
FastMCP Server
      │
      ├── search_posts
      ├── create_post
      ├── update_post
      └── delete_post
```

The MCP server is a separate process/service from the FastAPI application.

For the local development environment:

```text
FastAPI
http://localhost:8080

MCP Server
http://localhost:8001/mcp
```

The two services must use different ports.

---

# `client.py`

Contains the MCP client used by the AI application to communicate with the MCP server.

The client is responsible for:

* connecting to the MCP server
* discovering available tools
* calling MCP tools
* managing the MCP client connection

Conceptually:

```text
Agent
  │
  ▼
MCPClient
  │
  ├── list_tools()
  │
  └── call_tool()
          │
          ▼
      MCP Server
```

A simplified client interface:

```python
class MCPClient:

    async def list_tools(self):
        ...

    async def call_tool(
        self,
        name: str,
        arguments: dict
    ):
        ...
```

The MCP client must establish a connection before calling MCP operations.

For example:

```python
async with self.mcp_client:
    tools = await self.mcp_client.list_tools()
```

This ensures the MCP client is connected while the operations are performed.

---

# `schema_adapter.py`

Responsible for adapting MCP tool definitions into the format required by the LLM provider.

This is important because:

```text
MCP Tool Schema
       ↓
Schema Adapter
       ↓
LLM Tool / Function Schema
```

For example, MCP may expose a tool with an input schema:

```text
search_posts
    ├── query: string
    └── limit: integer
```

The AI model needs this information in the tool format supported by its API.

The adapter converts between the two representations.

Conceptually:

```text
FastMCP
   │
   │ input_schema
   ▼
SchemaAdapter
   │
   ▼
OpenAI function tool
```

This keeps the MCP implementation independent from the specific LLM provider.

---

# `dependencies.py`

Contains dependencies required by MCP tools.

Depending on the application, this can include:

* database sessions
* authentication information
* application services
* repositories
* configuration
* shared dependencies

The goal is to keep dependency construction separate from the actual MCP tool definitions.

Conceptually:

```text
MCP Tool
   │
   ├── Database dependency
   ├── Service dependency
   └── Configuration
```

This makes MCP tools easier to test and keeps infrastructure concerns out of the tool logic.

---

# MCP Tool Flow

When the AI agent wants to use a tool, the flow is:

```text
1. User asks a question
          ↓
2. AI agent decides a tool is required
          ↓
3. MCP client calls the MCP server
          ↓
4. MCP server identifies the requested tool
          ↓
5. Tool executes backend operation
          ↓
6. Tool result is returned to MCP client
          ↓
7. Result is provided back to the LLM
          ↓
8. LLM generates final response
```

For example:

```text
User:
"Find my restaurant posts"

        ↓

     AI Agent

        ↓

  call search_posts

        ↓

    MCP Client

        ↓

    MCP Server

        ↓

  search_posts()

        ↓

   Database

        ↓

    Tool Result

        ↓

     AI Agent

        ↓

   Final Answer
```

---

# MCP Tool Discovery

One important feature of MCP is **tool discovery**.

The agent can ask the MCP server which tools are available:

```python
tools = await mcp_client.list_tools()
```

The result can then be converted into LLM-compatible tool definitions.

Conceptually:

```text
MCP Server
     │
     │ list_tools()
     ▼
Available Tools
     │
     ▼
Schema Adapter
     │
     ▼
LLM Tool Definitions
     │
     ▼
LLM
```

This means the AI agent does not have to hard-code every tool definition.

---

# Tool Calling

When the LLM decides to call a tool, it returns a tool/function call.

Conceptually:

```text
LLM
 │
 │ function_call
 ▼
Agent
 │
 │ tool name + arguments
 ▼
MCP Client
 │
 ▼
MCP Server
 │
 ▼
Tool
```

For example:

```python
{
    "name": "search_posts",
    "arguments": {
        "query": "restaurant"
    }
}
```

The orchestrator extracts the tool name and arguments:

```python
tool_name = tool_call["name"]

arguments = json.loads(
    tool_call["arguments"]
)

tool_call_id = tool_call["call_id"]
```

The MCP client then executes:

```python
result = await mcp_client.call_tool(
    tool_name,
    arguments
)
```

The result is sent back to the LLM as a tool result.

---

# MCP and LangGraph

MCP and LangGraph have different responsibilities.

### LangGraph

Handles:

* agent workflow
* state
* nodes
* edges
* routing
* loops
* retries
* human-in-the-loop
* multi-agent orchestration

### MCP

Handles:

* tool discovery
* tool schemas
* tool invocation
* interoperability between AI clients and tools

The relationship is:

```text
                   LangGraph
                       │
                       ▼
                 Agent decides
                 which tool
                 to use
                       │
                       ▼
                  MCP Client
                       │
                       ▼
                  MCP Server
                       │
                       ▼
                     Tool
```

A useful interview explanation is:

> **"LangGraph manages the agent workflow, while MCP provides a standardized protocol for discovering and invoking external tools."**

---

# MCP and FastAPI

The MCP server and FastAPI application are separate services.

```text
                    ┌─────────────────┐
                    │     FastAPI     │
                    │   Port 8080     │
                    └────────┬────────┘
                             │
                             ▼
                         AI Agent
                             │
                             ▼
                       MCP Client
                             │
                             ▼
                    ┌─────────────────┐
                    │   MCP Server    │
                    │   Port 8001     │
                    └────────┬────────┘
                             │
                             ▼
                         MCP Tools
```

Therefore:

```text
FastAPI → localhost:8080
MCP     → localhost:8001/mcp
```

Do not run both services on the same port.

---

# Local Development

Start the MCP server separately from FastAPI.

Example:

```bash
uvicorn mcp_server.server:app \
    --host 0.0.0.0 \
    --port 8001
```

The MCP client connects to:

```text
http://localhost:8001/mcp
```

The FastAPI application can continue running on:

```text
http://localhost:8080
```

`0.0.0.0` is normally used as the server's bind address. A local client should generally connect using `localhost` or `127.0.0.1`.

---

# Connection Lifecycle

The MCP client needs to be connected before operations such as:

```python
await client.list_tools()
```

or:

```python
await client.call_tool(...)
```

A safe pattern is:

```python
async with client:
    tools = await client.list_tools()

    result = await client.call_tool(
        "search_posts",
        {
            "query": "restaurant"
        }
    )
```

For a learning project, opening a connection around a request is acceptable.

In a production application, connection lifecycle management can be handled at application startup/shutdown or through an appropriate reusable client strategy.

---

# MCP Error Handling

Common problems include:

### Port already in use

```text
[Errno 48] Address already in use
```

Check that FastAPI and MCP are running on different ports.

```text
FastAPI → 8080
MCP     → 8001
```

---

### MCP 404 Not Found

Example:

```text
POST http://localhost:8080/mcp
404 Not Found
```

This usually means the MCP client is connecting to the FastAPI server instead of the MCP server.

Check:

```text
MCP_SERVER_URL=http://localhost:8001/mcp
```

---

### Client is not connected

Example:

```text
RuntimeError:
Client is not connected.
```

Make sure MCP operations are performed inside the client's connection context:

```python
async with client:
    await client.list_tools()
```

---

### Deprecated `inputSchema`

If using the newer FastMCP API, use:

```python
tool.input_schema
```

rather than the deprecated:

```python
tool.inputSchema
```

The schema adapter should therefore use the current MCP/FastMCP property exposed by the installed SDK version.

---

# Environment Configuration

The MCP server URL should be configurable rather than hard-coded.

Example:

```env
MCP_SERVER_URL=http://localhost:8001/mcp
```

Then load it through application configuration:

```python
class Settings(BaseSettings):

    mcp_server_url: str
```

and:

```python
MCPClient(
    server_url=settings.mcp_server_url
)
```

This allows different URLs to be used for local development, testing, and production.

---

# Security Considerations

MCP tools can perform real actions, not just return information.

For example:

```text
search_posts      → read
create_post       → write
update_post       → write
delete_post       → destructive
```

For production systems, tool authorization should be considered carefully.

Potential controls include:

* authentication
* authorization
* user identity propagation
* input validation
* permission checks
* audit logging
* rate limiting
* human approval for destructive actions

For example:

```text
User
 ↓
AI Agent
 ↓
delete_post
 ↓
Authorization
 ↓
Human Approval
 ↓
Delete
```

The LLM should not be treated as the security boundary.

---

# MCP vs Direct Function Calls

Without MCP:

```text
Agent
  ↓
Python function
  ↓
Database/API
```

With MCP:

```text
Agent
  ↓
MCP Client
  ↓
MCP Protocol
  ↓
MCP Server
  ↓
Tool
  ↓
Database/API
```

The additional protocol layer provides a standardized way for AI applications to discover and interact with tools.

This becomes particularly useful when tools are provided by separate services or need to be shared across different AI clients.

---

# Mental Model

The easiest way to remember the four files:

```text
client.py
    ↓
"How do I communicate with the MCP server?"

server.py
    ↓
"How do I expose my tools through MCP?"

schema_adapter.py
    ↓
"How do I translate MCP tool definitions
 into the format my LLM expects?"

dependencies.py
    ↓
"What application resources do my MCP tools need?"
```

Overall:

```text
                  MCP Layer

       ┌───────────────────────────┐
       │                           │
       │        client.py          │
       │             │             │
       │             ▼             │
       │    schema_adapter.py      │
       │             │             │
       │             ▼             │
       │        server.py          │
       │             │             │
       │             ▼             │
       │      dependencies.py      │
       │             │             │
       │             ▼             │
       │          Tools             │
       │                           │
       └───────────────────────────┘
```

The key architecture is:

```text
LLM / LangGraph
       ↓
   MCP Client
       ↓
   MCP Server
       ↓
      Tools
       ↓
Application / Database
```

MCP therefore acts as the **standardized tool integration layer** between the AI agent and external capabilities.
