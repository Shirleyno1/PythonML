# AI Post Management & RAG Assistant

An AI-powered application combining a **FastAPI backend**, **Streamlit frontend**, **LLM-powered intent classification**, **JWT authentication**, **post management**, **RAG (Retrieval-Augmented Generation)**, and **LLM evaluation/monitoring**.

The project was built as a practical AI Engineering learning project, progressing from a traditional REST API into an AI-enabled application with structured LLM responses, document ingestion, vector search, and RAG.

---

## 🚀 Features

### 1. Post Management

Authenticated users can manage posts through a REST API.

**Capabilities:**

* Create/upload posts
* Search posts
* Retrieve posts
* Delete posts
* List posts
* JWT authentication
* User authentication and authorization
* SQLite persistence
* Async database operations

---

### 2. AI Chatbot

The application provides a chatbot interface through Streamlit.

Instead of sending every user request directly to an LLM, the application first classifies the user's intent.

Supported intents:

```text
search
create
delete
general
```

Example:

```text
User:
"Find posts about Python"

        ↓

LLM Intent Classifier

        ↓

{
    "intent": "search",
    "query": "Python"
}

        ↓

FastAPI

        ↓

Search Posts

        ↓

Return Results
```

For non-database questions, the request can be handled as a general conversation.

---

### 3. Structured LLM Output

The chatbot uses structured responses rather than relying on free-form LLM text.

Example:

```json
{
    "intent": "search",
    "query": "Python"
}
```

This allows the application to reliably determine what operation the user wants.

The structured approach helps reduce problems caused by unpredictable LLM output and makes the LLM easier to integrate with backend APIs.

---

### 4. RAG

The project includes a **Retrieval-Augmented Generation (RAG)** pipeline.

Documents such as PDFs can be loaded, processed, embedded, stored in a vector database, and retrieved when answering questions.

Basic pipeline:

```text
PDF / Document
      ↓
Document Loader
      ↓
Text Extraction
      ↓
Chunking
      ↓
Embeddings
      ↓
Vector Database
      ↓
Similarity Search
      ↓
Top-K Relevant Chunks
      ↓
LLM
      ↓
Answer
```

The goal is to allow the chatbot to answer questions using information contained in external documents instead of relying only on the LLM's training knowledge.

---

### 5. Document Ingestion

The RAG component supports document ingestion.

The ingestion process includes:

* Loading PDF documents
* Extracting document text
* Splitting documents into chunks
* Creating embeddings
* Storing embeddings in a vector database
* Retrieving relevant chunks during queries

The project is currently using **ChromaDB** for vector storage.

---

### 6. Vector Search

ChromaDB is used to store document embeddings and perform similarity-based retrieval.

For example:

```text
Question:
"What vegetarian dishes are available?"

              ↓

Embedding

              ↓

ChromaDB similarity search

              ↓

Top-K relevant chunks

              ↓

LLM

              ↓

Answer
```

`top_k` controls how many of the most relevant chunks are retrieved.

For example:

```text
top_k = 3
```

means the system retrieves the three most relevant chunks.

---

### 7. LLM Evaluation

The chatbot includes an evaluation component for measuring response quality.

Evaluation can be used to check whether:

* The retrieved information is relevant
* The generated answer is accurate
* The answer is supported by the retrieved context
* The system is producing appropriate responses

Evaluation is treated as part of the application rather than something performed manually outside the system.

---

### 8. Monitoring

The project also includes monitoring/observability concepts for the chatbot.

The goal is to monitor:

* LLM requests
* Responses
* Retrieval behaviour
* Errors
* Evaluation results
* AI response quality

This provides a foundation for understanding how an AI system behaves in production.

---

# 🏗️ Architecture

## Overall Architecture

```text
                         ┌─────────────────────┐
                         │      User           │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │    Streamlit UI     │
                         │                     │
                         │  Posts + Chatbot    │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │     FastAPI         │
                         │      Backend        │
                         └──────────┬──────────┘
                                    │
                ┌───────────────────┼───────────────────┐
                │                   │                   │
                ▼                   ▼                   ▼
        ┌───────────────┐   ┌───────────────┐   ┌───────────────┐
        │ Authentication│   │ Post Service  │   │ AI / Chatbot  │
        │     JWT       │   │               │   │               │
        └───────────────┘   └───────┬───────┘   └───────┬───────┘
                                    │                   │
                                    ▼                   ▼
                             ┌──────────────┐    ┌──────────────┐
                             │   SQLite     │    │ LLM / Intent │
                             │  Database    │    │ Classifier   │
                             └──────────────┘    └──────┬───────┘
                                                        │
                                                        ▼
                                                 ┌──────────────┐
                                                 │ RAG Pipeline │
                                                 └──────┬───────┘
                                                        │
                                      ┌─────────────────┼─────────────────┐
                                      │                 │                 │
                                      ▼                 ▼                 ▼
                               ┌────────────┐   ┌────────────┐   ┌────────────┐
                               │ Documents  │   │ Embeddings │   │  ChromaDB  │
                               └────────────┘   └────────────┘   └────────────┘
                                                        │
                                                        ▼
                                                   ┌─────────┐
                                                   │   LLM   │
                                                   └─────────┘
```

---

# 🧩 Feature Architecture

## Post Management

```text
Streamlit
    │
    ▼
FastAPI
    │
    ├── JWT Authentication
    │
    ├── Create Post
    │
    ├── Search Posts
    │
    ├── Get Posts
    │
    └── Delete Post
            │
            ▼
        SQLite
```

---

## AI Chatbot

```text
User Question
      │
      ▼
 Streamlit
      │
      ▼
 FastAPI
      │
      ▼
 Intent Classifier
      │
      ├───────────────┐
      │               │
      ▼               ▼
 Database Intent    General
      │               │
      ▼               ▼
Post Operation      LLM
```

Supported database intents:

```text
SEARCH
CREATE
DELETE
```

---

## RAG

```text
                DOCUMENT INGESTION

PDF
 │
 ▼
Document Loader
 │
 ▼
Text
 │
 ▼
Chunking
 │
 ▼
Embeddings
 │
 ▼
ChromaDB
 │
 ▼
Vector Store


                QUERY TIME

User Question
 │
 ▼
Embedding
 │
 ▼
ChromaDB
 │
 ▼
Top-K Relevant Chunks
 │
 ▼
Prompt + Context
 │
 ▼
LLM
 │
 ▼
Final Answer
```

---

# 🔐 Authentication

The API uses JWT-based authentication.

Typical flow:

```text
User Login
    │
    ▼
FastAPI
    │
    ▼
Validate Credentials
    │
    ▼
Generate JWT
    │
    ▼
Client
    │
    ▼
Authenticated API Requests
```

Protected operations require a valid JWT token.

---

# 🛠️ Technology Stack

## Backend

* Python
* FastAPI
* REST API
* Pydantic
* Async Python
* `asyncio`
* HTTP APIs
* JWT authentication

## Database

* SQLite
* `aiosqlite`
* SQL/database fundamentals
* CRUD operations

## Frontend

* Streamlit
* Python
* API integration
* Chat UI
* Loading states / spinners

## AI / LLM

* Large Language Models (LLMs)
* OpenAI API
* Prompt engineering
* Structured LLM output
* Intent classification
* JSON-based responses
* Function/tool-oriented AI architecture
* LLM error handling
* Retry/fallback concepts

## RAG

* Retrieval-Augmented Generation
* PDF document loading
* Document ingestion
* Text extraction
* Text chunking
* Embeddings
* Vector search
* Similarity search
* Top-K retrieval
* Context injection
* ChromaDB
* Grounded question answering

## Evaluation & Monitoring

* LLM evaluation
* AI response quality evaluation
* Retrieval evaluation
* Accuracy testing
* Monitoring
* Error tracking
* AI system observability concepts

## Development

* Git
* GitHub
* Virtual environments
* `.venv`
* Python package management
* Logging
* Exception handling
* Debugging
* API testing
* Environment configuration

---

# 📁 Project Structure

A simplified project structure:

```text
practice/
│
├── api/
│   ├── main.py
│   ├── auth.py
│   ├── models.py
│   ├── database.py
│   └── ...
│
├── rag/
│   ├── documents.py
│   ├── service.py
│   ├── ...
│   └── ...
│
├── chatbot/
│   ├── classifier.py
│   ├── ...
│   └── ...
│
├── frontend/
│   └── streamlit_app.py
│
├── tests/
│   ├── ...
│   └── ...
│
├── requirements.txt
└── README.md
```

---

# 🔄 Example End-to-End Flow

A user asks:

```text
"Find posts about Android"
```

The system processes the request:

```text
                    User
                     │
                     ▼
              Streamlit Chat
                     │
                     ▼
                  FastAPI
                     │
                     ▼
             Intent Classifier
                     │
                     ▼
          ┌─────────────────────┐
          │ intent = search     │
          │ query = Android     │
          └──────────┬──────────┘
                     │
                     ▼
                Post Service
                     │
                     ▼
                  SQLite
                     │
                     ▼
               Search Results
                     │
                     ▼
                 Streamlit
                     │
                     ▼
                   User
```

---

# 🤖 RAG Example

A restaurant PDF is uploaded:

```text
Restaurant Q&A.pdf
        │
        ▼
   PDF Loader
        │
        ▼
  Extract Text
        │
        ▼
    Chunk Text
        │
        ▼
Generate Embeddings
        │
        ▼
     ChromaDB
```

The user asks:

```text
"Which vegetarian dishes are available?"
```

The system:

```text
Question
   │
   ▼
Embedding
   │
   ▼
ChromaDB
   │
   ▼
Top-K Documents
   │
   ▼
Relevant Context
   │
   ▼
LLM
   │
   ▼
Grounded Answer
```

---

# 🎯 Engineering Concepts Demonstrated

This project demonstrates the transition from traditional software engineering to AI Engineering.

### Traditional Software Engineering

```text
Client
  ↓
REST API
  ↓
Business Logic
  ↓
Database
```

### AI-Enabled Software Engineering

```text
Client
  ↓
REST API
  ↓
LLM
  ↓
Intent / Structured Output
  ↓
Business Logic
  ↓
Database
```

### RAG-Based AI System

```text
User
 ↓
LLM
 ↓
Retriever
 ↓
Vector Database
 ↓
Relevant Context
 ↓
LLM
 ↓
Answer
```

This demonstrates how an LLM can be integrated into a conventional backend rather than treating the LLM as a standalone chatbot.

---

# 📚 Skills Demonstrated

## Python

* Python fundamentals
* Object-oriented programming
* Classes
* Modules
* Package management
* Virtual environments
* Exception handling
* File handling
* Async programming
* `asyncio`
* Logging

## API Development

* FastAPI
* RESTful API design
* HTTP methods
* Request/response models
* Pydantic
* HTTP status codes
* API validation
* Error handling
* Authentication
* JWT
* CRUD APIs
* Async APIs

## Database

* SQLite
* `aiosqlite`
* SQL
* CRUD
* Database persistence
* Database abstraction
* Working with multiple data operations

## Frontend

* Streamlit
* API integration
* Chat interfaces
* User input handling
* Loading states
* Error presentation

## LLM Engineering

* OpenAI API
* LLM integration
* Prompt engineering
* Intent classification
* Structured outputs
* JSON responses
* LLM reliability
* Retry strategies
* Fallback strategies
* Tool/function-oriented architecture
* Context management

## RAG Engineering

* RAG architecture
* Document ingestion
* PDF processing
* Text extraction
* Chunking
* Embeddings
* Vector databases
* ChromaDB
* Semantic search
* Similarity search
* Top-K retrieval
* Context retrieval
* Grounded generation

## AI Evaluation

* LLM evaluation
* Retrieval evaluation
* Accuracy evaluation
* Response quality
* Test cases
* Evaluation metrics
* Regression testing concepts

## AI Observability

* LLM monitoring
* Request/response tracking
* Error monitoring
* Retrieval monitoring
* Evaluation monitoring
* AI system quality monitoring

## Software Engineering

* Modular architecture
* Separation of concerns
* Backend/frontend separation
* Service-layer architecture
* Error handling
* Logging
* Testing
* Debugging
* Git/GitHub
* Environment management

---

# 🧠 What I Learned

The project evolved through several stages:

```text
1. Python
      ↓
2. REST API
      ↓
3. FastAPI
      ↓
4. Database
      ↓
5. Authentication
      ↓
6. Streamlit Frontend
      ↓
7. LLM Integration
      ↓
8. Intent Classification
      ↓
9. Structured LLM Responses
      ↓
10. Evaluation
      ↓
11. Monitoring
      ↓
12. RAG
      ↓
13. Vector Database
      ↓
14. Document Ingestion
```

The project demonstrates that AI Engineering is not only about calling an LLM API. A production-oriented AI application also requires:

```text
LLM
+
Backend
+
Database
+
Authentication
+
Retrieval
+
Evaluation
+
Monitoring
+
Error Handling
```

---

# 🚧 Future Improvements

Planned areas for further development:

* [ ] LangChain
* [ ] LangGraph
* [ ] Agent workflows
* [ ] Tool/function calling
* [ ] MCP
* [ ] PostgreSQL
* [ ] MongoDB
* [ ] Docker
* [ ] Cloud deployment
* [ ] Production observability
* [ ] Advanced RAG evaluation
* [ ] RAG optimization
* [ ] Hybrid search
* [ ] Reranking
* [ ] Multi-agent workflows
* [ ] CI/CD
* [ ] Automated testing pipeline
* [ ] LLMOps

---

# 💡 Project Goal

The goal of this project is to build a practical end-to-end AI application while developing the skills required for an **AI Engineer / Software Engineer working with AI systems**.

Rather than building a simple chatbot, the project focuses on integrating AI into a real backend system with:

**APIs → Authentication → Database → LLM → RAG → Evaluation → Monitoring**

This provides a foundation for building production-oriented AI applications.
