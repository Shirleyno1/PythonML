# AI Practice Project

A practical AI engineering project built to learn and demonstrate modern **AI application development, RAG, agent orchestration, MCP, LangChain, LangGraph, and FastAPI**.

The project started as a backend/API application and gradually evolved into an AI-enabled application where an LLM can understand user requests, retrieve information, and interact with application functionality through tools.

---

## 1. Project Goals

The main goals of this project are to learn how to build production-style AI applications rather than only experimenting with LLM prompts.

Key areas covered:

* Python
* FastAPI
* Async programming
* SQLAlchemy
* JWT authentication
* REST APIs
* OpenAI API
* Structured LLM output
* RAG
* Embeddings
* Vector databases / FAISS
* LangChain
* LangGraph
* MCP / FastMCP
* AI agents
* Tool calling
* Agent orchestration
* Conversation state and history
* API integration
* Streamlit
* Clean project structure

The project is also used as hands-on preparation for **AI Engineer, AI Software Engineer, AI Automation, and AI Agent Orchestrator** roles.

---

## Start the Chatbot API

From the project root, start the FastAPI application with:

```bash
uvicorn chatbot.main:app --reload --host 0.0.0.0 --port 8080
```

The API will be available on port `8080`.

* `chatbot.main` → `chatbot/main.py`
* `app` → the FastAPI application instance
* `--reload` → automatically reloads when code changes
* `--host 0.0.0.0` → listens on all network interfaces
* `--port 8080` → runs the API on port 8080

# 2. High-Level Architecture

The project contains several layers:

```text
                        ┌──────────────────┐
                        │    Streamlit     │
                        │       UI         │
                        └────────┬─────────┘
                                 │
                                 ▼
                        ┌──────────────────┐
                        │     FastAPI      │
                        │      APIs        │
                        └────────┬─────────┘
                                 │
              ┌──────────────────┼──────────────────┐
              │                  │                  │
              ▼                  ▼                  ▼
        ┌───────────┐      ┌───────────┐      ┌─────────────┐
        │ Database  │      │    RAG    │      │ AI / Agent  │
        │           │      │           │      │ Orchestration│
        └───────────┘      └───────────┘      └──────┬──────┘
                                                     │
                              ┌──────────────────────┼───────────────┐
                              │                      │               │
                              ▼                      ▼               ▼
                        ┌───────────┐        ┌────────────┐   ┌───────────┐
                        │  OpenAI   │        │    MCP     │   │ LangGraph │
                        │    LLM    │        │   Server   │   │           │
                        └───────────┘        └─────┬──────┘   └───────────┘
                                                   │
                                                   ▼
                                             Application Tools
                                           ┌──────────────────┐
                                           │ search_posts     │
                                           │ delete_post      │
                                           └──────────────────┘
```

---

# 3. Project Structure

The project is organised by feature/responsibility rather than putting all functions into one large package.

```text
practice/
│
├── ai/
│   ├── __init__.py
│   ├── nodes.py
│   ├── state.py
│   ├── edges.py
│   └── graph.py
│
├── rag/
│   ├── __init__.py
│   ├── README.md
│   ├── documents.py
│   ├── embeddings.py
│   ├── vector_stores.py
│   ├── retrievers.py
│   └── chain.py
│
├── mcp_server/
│   ├── __init__.py
│   ├── client.py
│   ├── dependencies.py
│   ├── schema_adapter.py
│   └── server.py
│
├── lang_chain/
│   ├── __init__.py
│   ├── models.py
│   ├── messages.py
│   ├── prompts.py
│   ├── parsers.py
│   ├── structured_output.py
│   ├── chains.py
│   ├── runnables.py
│   ├── tools.py
│   ├── agents.py
│   ├── history.py
│   └── rag/
│       ├── __init__.py
│       ├── documents.py
│       ├── embeddings.py
│       ├── vector_stores.py
│       ├── retrievers.py
│       └── chain.py
│
├── chatbot/
│   └── main.py
│
├── data/
│   └── Resturaunt Q&A.pdf
│
├── models/
├── schemas/
├── services/
├── repositories/
├── dependencies/
│
├── tests/
│
├── requirements.txt
└── README.md
```

> The exact application-level folders may evolve as the project grows. The important principle is separating API, AI, RAG, MCP, and infrastructure responsibilities.

---

# 4. Core Application

The original application provides functionality around posts.

A post can contain information such as:

* Caption
* Description
* Price
* Image/video URL
* File name
* File type
* Owner

Images/videos can be uploaded through ImageKit.

The backend uses:

```text
FastAPI
   ↓
SQLAlchemy Async
   ↓
Database
```

Authentication is handled using JWT.

---

# 5. FastAPI

FastAPI is used as the main backend framework.

Example application startup:

```bash
uvicorn chatbot.main:app --reload --host 0.0.0.0 --port 8080
```

The application can therefore be accessed through the FastAPI server while developing locally.

FastAPI provides:

* REST endpoints
* Dependency injection
* Request validation
* Response models
* Async endpoint support
* Automatic OpenAPI documentation

---

# 6. Async Python

The project uses asynchronous Python for backend operations.

For example:

```python
async def get_posts(
    session: AsyncSession = Depends(get_async_session),
):
    ...
```

Async programming is particularly useful for I/O-bound operations such as:

* Database queries
* HTTP requests
* LLM API calls
* MCP requests

Not every operation needs to be async.

For example, local PDF loading and some CPU-bound operations can remain synchronous.

---

# 7. Authentication

The application uses JWT-based authentication.

The general flow is:

```text
User
 ↓
Login
 ↓
JWT
 ↓
Authorization header
 ↓
FastAPI dependency
 ↓
Current authenticated user
```

Authenticated users can perform operations according to application rules.

For example, deleting a post must only be allowed when the authenticated user owns that post.

---

# 8. OpenAI Integration

OpenAI models are used for AI functionality.

The project uses an LLM to understand natural-language requests.

For example:

```text
User:
"Find me some cheap Italian restaurants"

        ↓

LLM

        ↓

Intent / structured result

        ↓

search_posts tool

        ↓

Application database
```

The model is not responsible for directly manipulating the database.

Instead, application functionality is exposed through controlled tools.

This provides a separation between:

```text
LLM reasoning
      ↓
Tool selection
      ↓
Application logic
      ↓
Database
```

---

# 9. Intent Classification

One of the early AI components is an intent classifier.

Supported intents include:

```text
search
create
delete
update
general
```

The LLM receives the user's message and produces structured information.

For example:

```text
"Find posts about Italian food"

        ↓

{
    "intent": "search",
    "query": "Italian food"
}
```

For deletion:

```text
"Delete post 123"

        ↓

{
    "intent": "delete",
    "query": "123"
}
```

Structured output is useful because application code should not depend on parsing arbitrary natural-language responses.

---

# 10. AI Agent / Orchestration

The project explores AI orchestration rather than treating the LLM as a simple chatbot.

The high-level flow is:

```text
User Message
      ↓
Intent / Agent
      ↓
Determine required action
      ↓
Select tool
      ↓
Execute tool
      ↓
Return result
      ↓
LLM generates response
```

The project uses an `AgentOrchestrator` to coordinate:

* OpenAI
* MCP client
* Application tools
* Schema adaptation
* User context

The goal is to separate **decision making** from **tool execution**.

---

# 11. MCP

MCP stands for **Model Context Protocol**.

MCP is used in this project to expose application functionality as tools that an AI system can use.

The current MCP tools include:

```text
search_posts
delete_post
```

The architecture is:

```text
                    OpenAI / Agent
                          │
                          ▼
                      MCP Client
                          │
                          ▼
                      MCP Server
                          │
                ┌─────────┴─────────┐
                ▼                   ▼
          search_posts         delete_post
                │                   │
                └─────────┬─────────┘
                          ▼
                      Application
                          │
                          ▼
                       Database
```

---

# 12. FastMCP

FastMCP is used to build the MCP server.

The MCP server exposes tools that can be discovered by an MCP client.

The client can list available tools:

```text
search_posts
delete_post
```

The model does not need to know the internal implementation of these functions.

It only needs to understand:

```text
Tool name
Tool description
Tool input schema
Tool result
```

This demonstrates an important AI engineering pattern:

> Give an AI controlled access to capabilities instead of giving it direct access to application internals.

---

# 13. MCP Schema Adaptation

The project also contains a `schema_adapter.py`.

Its purpose is to handle differences between MCP tool schemas and the schema expected by the AI/orchestration layer.

Conceptually:

```text
MCP Tool Schema
      ↓
Schema Adapter
      ↓
Agent / OpenAI Tool Schema
```

This keeps protocol-specific details out of the core orchestration logic.

---

# 14. RAG

RAG means **Retrieval-Augmented Generation**.

The project uses a local PDF as the knowledge source:

```text
data/
└── Resturaunt Q&A.pdf
```

The RAG pipeline is:

```text
PDF
 ↓
Document Loader
 ↓
Documents
 ↓
Text Splitter
 ↓
Chunks
 ↓
Embeddings
 ↓
FAISS
 ↓
Retriever
 ↓
Relevant Chunks
 ↓
Prompt
 ↓
LLM
 ↓
Answer
```

---

# 15. Documents and Chunks

The document loader loads the PDF into LangChain `Document` objects.

A document contains:

```python
document.page_content
document.metadata
```

A PDF may initially produce one document per page.

These documents are then split into smaller chunks.

For example:

```python
documents = load_pdf("./data/Resturaunt Q&A.pdf")

chunks = split_documents(documents)
```

The distinction is:

```text
documents
    ↓
original loaded content

chunks
    ↓
smaller pieces designed for retrieval
```

The chunks must actually be passed into the vector store.

```python
vector_store = FAISS.from_documents(
    documents=chunks,
    embedding=embeddings,
)
```

Using `documents` instead of `chunks` would bypass the chunking step.

---

# 16. Embeddings

Embeddings convert text into numerical vectors.

Conceptually:

```text
"Japanese restaurant in Sydney"
             ↓
       Embedding Model
             ↓
[0.021, -0.182, 0.442, ...]
```

Texts with similar semantic meaning tend to have vectors that are close together in vector space.

This allows semantic retrieval.

---

# 17. FAISS

FAISS is used as the vector store.

The basic indexing flow is:

```python
documents = load_pdf("./data/Resturaunt Q&A.pdf")

chunks = split_documents(documents)

embeddings = create_embeddings()

vector_store = FAISS.from_documents(
    documents=chunks,
    embedding=embeddings,
)
```

FAISS stores the embeddings and allows similar vectors to be retrieved.

Important distinction:

```text
FAISS
    ↓
Actual vector similarity/search library

langchain_community.vectorstores.FAISS
    ↓
LangChain integration/wrapper around FAISS
```

---

# 18. Retriever

The vector store can be converted into a retriever.

Conceptually:

```text
Question
   ↓
Embedding
   ↓
Vector similarity search
   ↓
Relevant chunks
```

For example:

```python
documents = await retriever.ainvoke(question)
```

The returned documents are the pieces of information that are relevant to the user's question.

---

# 19. RAG Generation

After retrieving relevant chunks, those chunks are supplied to the LLM.

Conceptually:

```text
Question
+
Retrieved Context
        ↓
       Prompt
        ↓
       LLM
        ↓
     Answer
```

This helps the LLM answer using information from the application's knowledge source instead of relying only on its pretrained knowledge.

---

# 20. LangChain

LangChain is being used to learn common building blocks for LLM applications.

The learning area covers:

```text
Models
Messages
Prompts
Output Parsers
Structured Output
Chains
Runnables
LCEL
Tools
Agents
History
RAG
```

---

# 21. LangChain Models

Models provide the interface to an LLM.

Conceptually:

```python
model = ...
response = model.invoke(...)
```

For asynchronous applications:

```python
response = await model.ainvoke(...)
```

The async version is particularly relevant to the FastAPI application.

---

# 22. Prompts

Prompts define how information is presented to the model.

A prompt can contain:

```text
System instructions
User question
Retrieved context
Conversation history
```

For RAG:

```text
System:
Answer using the provided context.

Context:
{context}

Question:
{question}
```

---

# 23. LCEL

LCEL means **LangChain Expression Language**.

The `|` operator is used for composition.

For example:

```python
chain = prompt | model | parser
```

The data flows from left to right:

```text
prompt
   ↓
model
   ↓
parser
```

The output of one component becomes the input of the next component.

This is one of the key LangChain concepts.

---

# 24. Output Parsers

An output parser converts an LLM response into the format required by application code.

For example:

```text
LLM output
    ↓
StrOutputParser
    ↓
Python string
```

Structured output can instead produce a typed object.

For example:

```python
class Intent(BaseModel):
    intent: str
    query: str
```

This is particularly useful for AI systems where the result needs to drive application logic.

---

# 25. LangGraph

LangGraph is used to understand graph-based AI orchestration.

A graph can be represented as:

```text
START
  ↓
Classify
  ↓
Conditional Routing
  ├── Search
  ├── Delete
  ├── Create
  └── General
  ↓
END
```

The project studies the main LangGraph concepts:

```text
State
Nodes
Edges
Conditional Edges
Graph
```

### State

State contains information that flows through the graph.

### Nodes

Nodes perform work.

For example:

```text
classify_node
search_node
delete_node
response_node
```

### Edges

Edges define how execution moves between nodes.

### Conditional Edges

Conditional edges allow routing based on state.

For example:

```text
intent == "search"
       ↓
search_node

intent == "delete"
       ↓
delete_node
```

This makes the orchestration explicit rather than putting all decision logic inside one large function.

---

# 26. Conversation History

An AI application often needs more than a single request.

For example:

```text
User:
Find Italian restaurants.

Assistant:
Here are some restaurants...

User:
Only show cheap ones.

Assistant:
...
```

The second request depends on previous context.

Conversation history can therefore become part of the AI state:

```text
State
 ├── messages
 ├── user information
 ├── current request
 ├── retrieved documents
 └── tool results
```

This concept is important for both LangChain and LangGraph.

---

# 27. RAG vs Traditional Search

Traditional keyword search may focus on exact terms.

For example:

```text
Query:
"cheap Italian food"
```

Keyword search may look for:

```text
cheap
Italian
food
```

Vector search uses embeddings to retrieve semantically similar content.

The project also explores **BM25** as a traditional lexical retrieval approach.

A modern RAG system can combine approaches:

```text
                Query
                  │
        ┌─────────┴─────────┐
        ▼                   ▼
   BM25 Search        Vector Search
        │                   │
        └─────────┬─────────┘
                  ▼
              Combined
              Retrieval
                  ↓
                 LLM
```

This is the basic idea behind hybrid retrieval.

---

# 28. Async RAG

The RAG pipeline does not need to make every operation asynchronous.

A practical approach is:

### Offline indexing

```text
PDF
 ↓
Load
 ↓
Split
 ↓
Embed
 ↓
FAISS
```

This can remain synchronous.

### Online query

```text
User Question
 ↓
Retriever
 ↓
LLM
 ↓
Response
```

Use async operations where supported:

```python
documents = await retriever.ainvoke(question)

response = await chain.ainvoke(...)
```

FAISS itself is a local vector search library, so wrapping a FAISS call in an async function does not automatically make the underlying CPU work non-blocking.

---

# 29. Streamlit

Streamlit is used as a lightweight UI for interacting with the backend/AI functionality.

The conceptual architecture is:

```text
Streamlit
    ↓
FastAPI
    ↓
AI / Application Services
    ↓
Database / RAG / MCP
```

This keeps the UI separate from the backend logic.

---

# 30. Security and Application Boundaries

AI systems should not allow the LLM to directly perform unrestricted database operations.

For example:

```text
LLM
 ↓
Tool
 ↓
Authorization
 ↓
Application Service
 ↓
Database
```

For destructive operations such as deletion:

```text
User request
 ↓
LLM identifies delete intent
 ↓
delete_post tool
 ↓
Verify authenticated user
 ↓
Verify post ownership
 ↓
Delete
```

The LLM determines **what the user is asking for**, but application code remains responsible for authorization and data integrity.

---

# 31. Important AI Engineering Concepts Learned

The project covers the following progression:

```text
Python
  ↓
FastAPI
  ↓
Async APIs
  ↓
Database
  ↓
Authentication
  ↓
OpenAI API
  ↓
Structured Output
  ↓
RAG
  ↓
Embeddings
  ↓
Vector Search
  ↓
LangChain
  ↓
LangGraph
  ↓
MCP
  ↓
Tool Calling
  ↓
Agent Orchestration
```

These concepts build on each other.

---

# 32. What I Learned From Building the Project

### LLMs are not application logic

An LLM can interpret a request, but deterministic application code should handle:

* Authorization
* Database operations
* Validation
* Business rules
* Data integrity

### RAG is more than embeddings

A complete RAG system includes:

```text
Loading
→ Chunking
→ Embedding
→ Indexing
→ Retrieval
→ Prompt construction
→ Generation
```

### Agents need controlled tools

An agent becomes useful when it can interact with external capabilities.

```text
LLM
 ↓
Tool selection
 ↓
Tool execution
 ↓
Result
 ↓
LLM
```

### Orchestration matters

As AI applications become more complex, explicit orchestration helps manage:

* State
* Routing
* Tools
* Retrieval
* Multiple steps
* Error handling
* Conversation history

---

# 33. Example End-to-End AI Request

A user might ask:

```text
"Find me Japanese restaurants and show only the cheap ones."
```

The application can process it approximately as:

```text
User
 ↓
FastAPI
 ↓
AI / Agent
 ↓
Understand request
 ↓
Search tool
 ↓
MCP Client
 ↓
MCP Server
 ↓
search_posts
 ↓
Database
 ↓
Search results
 ↓
Agent / LLM
 ↓
Natural-language response
 ↓
User
```

For a knowledge question:

```text
User Question
 ↓
FastAPI
 ↓
RAG
 ↓
Retriever
 ↓
FAISS
 ↓
Relevant chunks
 ↓
Prompt
 ↓
LLM
 ↓
Answer
```

---

# 34. Development Commands

Start the FastAPI application:

```bash
uvicorn chatbot.main:app --reload --host 0.0.0.0 --port 8080
```

Run the MCP client during development:

```bash
python -m mcp_server.client
```

The exact command can depend on which component is being tested.

---

# 35. Environment

The project uses a Python virtual environment.

Activate it before running the application:

```bash
source .venv/bin/activate
```

Verify Python:

```bash
python --version
```

The current development environment uses Python 3.11.

---

# 36. Key Architecture Principles

This project follows several principles:

### Separation of concerns

```text
API
 ↓
Service
 ↓
Repository / Database
```

AI components are similarly separated:

```text
Agent
 ↓
Tool
 ↓
Application Service
 ↓
Database
```

### Explicit boundaries

MCP, RAG, LangChain, LangGraph, and application logic have separate responsibilities.

### Async where it provides value

Use async primarily for I/O-bound operations rather than making every function asynchronous.

### Structured data between components

Prefer structured objects/schemas over parsing free-form LLM responses.

### LLM does not bypass security

The model can request an operation, but authorization remains an application responsibility.

---

# 37. Current Learning Status

Completed / studied:

* Python fundamentals
* FastAPI
* Async Python
* REST APIs
* SQLAlchemy
* JWT authentication
* OpenAI API
* Prompting
* Structured LLM output
* RAG fundamentals
* Embeddings
* Vector search
* FAISS
* MCP
* FastMCP
* MCP client/server communication
* Tool calling
* LangGraph fundamentals
* LangChain fundamentals

Currently being strengthened:

* LangChain hands-on implementation
* Agent patterns
* Conversation history
* RAG implementation
* Agent orchestration
* Strands

Future areas:

* Production deployment
* Cloud
* AWS
* Observability
* LLM evaluation
* Production AI architecture

---

# 38. Purpose of This Project

This project is primarily a **learning and engineering practice project**.

The objective is not to build a production-scale commercial application. Instead, it provides a single project in which different AI engineering concepts can be connected together and understood through implementation.

The most important progression is:

```text
Traditional Software Engineering
              ↓
        AI-enabled APIs
              ↓
             RAG
              ↓
         Tool Calling
              ↓
             MCP
              ↓
      Agent Orchestration
              ↓
     Stateful AI Workflows
```

This provides hands-on experience with the architecture patterns used to build modern AI-enabled software systems.
