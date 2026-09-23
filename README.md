# AI Practice Project

An AI-powered backend application built with **Python, FastAPI, OpenAI, RAG, and Model Context Protocol (MCP)**.

The project is used to explore practical AI engineering concepts including LLM applications, tool calling, RAG, evaluation, authentication, asynchronous backend development, and MCP-based tool integration.

## Architecture

```text
                    ┌──────────────────┐
                    │   Streamlit UI   │
                    └────────┬─────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │     FastAPI      │
                    │    Backend       │
                    └────────┬─────────┘
                             │
              ┌──────────────┴──────────────┐
              │                             │
              ▼                             ▼
        ┌───────────┐                 ┌─────────────┐
        │ AI / RAG  │                 │ Posts API   │
        └───────────┘                 └──────┬──────┘
              │                              │
              ▼                              ▼
        ┌───────────┐                 ┌─────────────┐
        │  OpenAI   │                 │ PostService │
        └───────────┘                 └──────┬──────┘
                                             │
                                      ┌──────▼──────┐
                                      │ Repository  │
                                      └──────┬──────┘
                                             │
                                             ▼
                                         Database

MCP integration:

        ┌─────────────────┐
        │   MCP Client    │
        │   FastMCP       │
        └────────┬────────┘
                 │ HTTP
                 ▼
        ┌─────────────────┐
        │   MCP Server    │
        │   FastMCP       │
        └────────┬────────┘
                 │
          ┌──────┴──────┐
          ▼             ▼
    search_posts    delete_post
          │             │
          └──────┬──────┘
                 ▼
            PostService
                 │
            PostRepository
                 │
              Database
```

## Features

### Backend

* Python
* FastAPI
* Async SQLAlchemy
* SQLite / aiosqlite
* JWT authentication
* Dependency injection
* Repository / Service architecture
* Async database operations
* File upload
* Post creation, retrieval, search and deletion
* User ownership checks
* Structured API responses
* Logging
* Error handling and retries

### AI / LLM

* OpenAI API
* LLM-based chatbot
* Tool/function calling
* Intent classification
* Query extraction
* Guardrails for ambiguous requests
* Structured outputs
* Streaming responses
* Retry handling

Current intents include:

```text
search
create
delete
general
```

### RAG

Implemented a Retrieval-Augmented Generation pipeline:

```text
PDF / Documents
      ↓
Document Loading
      ↓
Chunking
      ↓
Embeddings
      ↓
Vector Store
      ↓
Retriever
      ↓
Prompt
      ↓
LLM
      ↓
Answer
```

RAG components are separated into dedicated modules such as:

```text
chunking.py
documents.py
embeddings.py
generation.py
retrival.py
service.py
vector_store.py
```

The project supports retrieving information from local documents and using the retrieved context to generate answers.

### Evaluation & Monitoring

Implemented evaluation and monitoring for the AI application, including:

* Classification accuracy
* Evaluation datasets
* Model output evaluation
* Accuracy monitoring
* Logging of AI operations
* Error tracking

### MCP

Implemented an MCP server using **FastMCP**.

The MCP server exposes application functionality as MCP tools.

Current tools:

```text
search_posts
delete_post
```

Example MCP tool:

```python
@mcp.tool
async def search_posts(user_id: str) -> list[dict]:
    """Search Posts"""

    async with get_post_service() as service:
        result = await service.get_posts(user_id)
        return result["posts"]
```

The MCP server uses the existing application service and repository layers rather than duplicating business logic.

```text
MCP Tool
   ↓
PostService
   ↓
PostRepository
   ↓
Database
```

### MCP Client

A FastMCP client connects to the MCP server over HTTP.

The client can discover the available tools:

```python
tools = await client.list_tools()

for tool in tools:
    print(tool.name)
```

Current output:

```text
search_posts
delete_post
```

The client can also invoke a tool through MCP:

```python
result = await client.call_tool(
    "search_posts",
    {
        "user_id": "..."
    }
)
```

This verifies the complete MCP communication flow:

```text
MCP Client
    ↓
HTTP
    ↓
MCP Server
    ↓
MCP Tool
    ↓
Application Service
    ↓
Repository
    ↓
Database
```

## Project Structure

```text
practice/
│
├── posts/
│   ├── __init__.py
│   ├── db.py
│   ├── models.py
│   ├── repository.py
│   └── service.py
│
├── mcp_server/
│   ├── __init__.py
│   ├── server.py
│   ├── client.py
│   └── dependencies.py
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
├── chatbot/
│   └── ...
│
├── users/
│   └── ...
│
└── README.md
```

## Architecture Principles

The project uses separation between:

```text
Transport Layer
      ↓
Service Layer
      ↓
Repository Layer
      ↓
Database
```

FastAPI and MCP are treated as different interfaces to the same application logic.

```text
FastAPI ────────→ PostService ─────→ PostRepository
                                      ↓
MCP ────────────→ PostService ─────→ Database
```

This avoids duplicating business logic between HTTP endpoints and MCP tools.

FastAPI uses its dependency injection system for request-scoped dependencies, while the MCP layer manages its own service/database context.

## Running the Application

### Start FastAPI

```bash
uvicorn <your_app>:app --reload
```

### Start MCP Server

From the project root:

```bash
python -m mcp_server.server
```

The MCP server is configured to use HTTP transport.

### Start MCP Client

In another terminal:

```bash
python -m mcp_server.client
```

The client connects to the MCP server and can discover and invoke MCP tools.

## Current MCP Flow

The current implementation supports:

```text
Client
  │
  │ list_tools()
  ▼
MCP Server
  │
  ├── search_posts
  └── delete_post

Client
  │
  │ call_tool()
  ▼
MCP Server
  │
  ▼
PostService
  │
  ▼
PostRepository
  │
  ▼
Database
```

## Next Step

The next stage is to connect the MCP client/tool discovery with an OpenAI model.

The target architecture is:

```text
User
  ↓
Chatbot
  ↓
OpenAI Model
  ↓
Model decides whether a tool is required
  ↓
MCP Client
  ↓
MCP Server
  ↓
MCP Tool
  ↓
PostService
  ↓
Database
  ↓
Tool Result
  ↓
OpenAI Model
  ↓
Final Answer
```

For example:

```text
User:
"Search my posts"

        ↓

OpenAI Model

        ↓

search_posts(user_id)

        ↓

MCP Client

        ↓

MCP Server

        ↓

PostService

        ↓

Database

        ↓

Posts returned to the model

        ↓

"Here are your posts..."
```

## Learning Topics Covered

This project has been used to practice:

* Python
* Async Python
* FastAPI
* REST APIs
* SQLAlchemy
* aiosqlite
* JWT authentication
* Dependency Injection
* Service / Repository architecture
* OpenAI API
* LLM applications
* Tool calling
* Intent classification
* Guardrails
* Structured outputs
* Streaming
* RAG
* Embeddings
* Vector stores
* Evaluation
* Monitoring
* MCP
* FastMCP
* MCP clients and servers
* MCP tool discovery
* MCP tool invocation

## Future Improvements

Planned areas include:

* OpenAI + MCP integration
* LLM-driven MCP tool selection
* Improved authentication/context propagation
* LangChain
* LangGraph
* Docker
* AWS/cloud deployment
* Observability
* LLMOps
* Production-oriented AI agent architecture
