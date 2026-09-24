# RAG

This package contains the Retrieval-Augmented Generation (RAG) implementation for the AI application.

RAG allows the application to answer questions using information retrieved from a knowledge base rather than relying only on the language model's internal knowledge.

## RAG Overview

The RAG pipeline consists of two main phases:

### 1. Indexing

Documents are loaded, split into chunks, converted into embeddings, and stored in a vector store.

```text
Documents
    ↓
documents.py
    ↓
Load / extract text
    ↓
chunking.py
    ↓
Split into chunks
    ↓
embeddings.py
    ↓
Generate embeddings
    ↓
vector_store.py
    ↓
Store vectors
```

### 2. Querying

When the user asks a question, the question is converted into an embedding, relevant chunks are retrieved, and the retrieved information is provided to the LLM to generate the final answer.

```text
User Question
      ↓
embeddings.py
      ↓
Query Embedding
      ↓
retrieval.py
      ↓
Relevant Chunks
      ↓
generation.py
      ↓
LLM
      ↓
Final Answer
```

The complete flow is:

```text
                    INDEXING
                       │
                       ▼
                 Documents
                       │
                       ▼
                 Load / Parse
                       │
                       ▼
                    Chunks
                       │
                       ▼
                  Embeddings
                       │
                       ▼
                 Vector Store
                       │
                       │
                       │
                       ▼
                    QUERY
                       │
                       ▼
                 User Question
                       │
                       ▼
                  Embedding
                       │
                       ▼
                  Retrieval
                       │
                       ▼
              Relevant Documents
                       │
                       ▼
                  Generation
                       │
                       ▼
                  Final Answer
```

---

# Files

## `documents.py`

Responsible for loading and processing source documents.

For example, a PDF knowledge base can be loaded and its text extracted.

Conceptually:

```text
PDF
 ↓
Document Loader
 ↓
Document objects
```

The document layer should focus on obtaining the source content.

It should not be responsible for generating embeddings or calling the LLM.

---

## `chunking.py`

Responsible for splitting documents into smaller pieces called **chunks**.

Large documents are usually split because:

* LLM context windows are limited.
* Smaller chunks improve retrieval precision.
* Embeddings work better when each vector represents a focused piece of information.

Conceptually:

```text
Large Document
       ↓
 ┌─────┬─────┬─────┬─────┐
 ↓     ↓     ↓     ↓     ↓
Chunk Chunk Chunk Chunk Chunk
```

A chunk may contain metadata such as:

```python
{
    "text": "...",
    "source": "restaurant.pdf",
    "page": 3
}
```

Chunking strategy has a significant effect on retrieval quality.

---

## `embeddings.py`

Responsible for converting text into numerical vectors called **embeddings**.

Conceptually:

```text
Text
 ↓
Embedding Model
 ↓
Vector
```

For example:

```text
"Where is the restaurant located?"
             ↓
      Embedding Model
             ↓
[0.12, -0.34, 0.87, ...]
```

Both documents and user queries need to be embedded using a compatible embedding model.

The vectors allow semantically similar content to be compared.

---

## `vector_store.py`

Responsible for storing and searching embedding vectors.

Conceptually:

```text
Chunk
  ↓
Embedding
  ↓
Vector Store
```

During retrieval:

```text
User Query
    ↓
Query Embedding
    ↓
Vector Store
    ↓
Similarity Search
    ↓
Top-K Chunks
```

The vector store is responsible for vector persistence/search rather than generating the final answer.

---

## `retrieval.py`

Responsible for finding the most relevant information from the vector store.

Typical flow:

```text
User Question
      ↓
Query Embedding
      ↓
Vector Search
      ↓
Top-K Results
```

For example:

```python
results = await retriever.retrieve(
    query="What time does the restaurant open?"
)
```

The retrieval layer should focus on:

> **Which pieces of the knowledge base are relevant to this question?**

It should not be responsible for generating the final natural-language answer.

---

## `generation.py`

Responsible for generating the final answer using the retrieved context.

Conceptually:

```text
User Question
      +
Retrieved Context
      ↓
     LLM
      ↓
Final Answer
```

A simplified prompt might look like:

```text
Answer the question using the provided context.

Context:
{retrieved_documents}

Question:
{question}
```

The generation layer is responsible for the LLM response rather than document loading or vector search.

---

## `service.py`

Acts as the main **RAG orchestration/service layer**.

It coordinates the individual components.

Conceptually:

```text
                  RAGService
                      │
          ┌───────────┼───────────┐
          ↓           ↓           ↓
     Retrieval    Generation   Other RAG
          │           │        components
          ↓           ↓
     Vector Store    LLM
```

A typical query flow is:

```python
async def ask(question: str):

    documents = await retrieval.retrieve(question)

    answer = await generation.generate(
        question=question,
        documents=documents
    )

    return answer
```

The service layer prevents the API layer from needing to know the internal details of the RAG pipeline.

---

# Responsibilities Summary

| File              | Responsibility                    |
| ----------------- | --------------------------------- |
| `documents.py`    | Load and extract source documents |
| `chunking.py`     | Split documents into chunks       |
| `embeddings.py`   | Convert text into vectors         |
| `vector_store.py` | Store and search vectors          |
| `retrieval.py`    | Retrieve relevant chunks          |
| `generation.py`   | Generate the final LLM answer     |
| `service.py`      | Orchestrate the RAG pipeline      |

A useful mental model is:

```text
documents
    ↓
chunking
    ↓
embeddings
    ↓
vector_store
    ↓
retrieval
    ↓
generation
```

`service.py` coordinates the process.

---

# Why RAG Is Needed

An LLM by itself answers based primarily on its model knowledge and the context supplied in the request.

RAG adds an external knowledge source:

```text
                Without RAG

User Question
      ↓
     LLM
      ↓
    Answer
```

With RAG:

```text
                With RAG

User Question
      │
      ├──────────────→ LLM
      │
      ↓
   Retrieval
      ↓
Relevant Context
      │
      └──────────────→ LLM
                         ↓
                       Answer
```

This allows the application to answer questions about private or application-specific information.

Examples include:

* internal company documentation
* PDFs
* product documentation
* knowledge bases
* policies
* FAQs
* application data

---

# RAG vs Fine-Tuning

RAG and fine-tuning solve different problems.

### RAG

Use RAG when the model needs access to external or changing information.

```text
Knowledge
   ↓
Vector Store
   ↓
Retrieve
   ↓
LLM
```

### Fine-tuning

Fine-tuning changes the model's learned behavior.

It can be useful when you want the model to consistently follow a particular style, format, or behavior.

A useful interview distinction:

> **RAG provides the model with relevant information at inference time, while fine-tuning changes the model itself through additional training.**

---

# Important RAG Concepts

## Chunking

How should documents be divided?

Important considerations include:

* chunk size
* chunk overlap
* document structure
* semantic boundaries
* metadata

Poor chunking can reduce retrieval quality even when the embedding model is good.

---

## Embeddings

Embeddings represent the semantic meaning of text as vectors.

Similar meanings should produce vectors that are relatively close in embedding space.

```text
"Where is the restaurant?"
             ↕
"What's the restaurant's location?"
```

These questions can have similar embeddings even though the wording is different.

---

## Similarity Search

Retrieval commonly compares the query vector with document vectors.

Conceptually:

```text
Query Vector
     │
     ├── similarity → Chunk A
     ├── similarity → Chunk B
     ├── similarity → Chunk C
     └── similarity → Chunk D
```

The system selects the most relevant chunks.

---

## Top-K Retrieval

Instead of returning every document, retrieval usually returns the top K results.

For example:

```text
Query
 ↓
Vector Search
 ↓
Top 5 relevant chunks
 ↓
LLM
```

The value of K affects both retrieval quality and the amount of context provided to the model.

---

## Context Injection

Retrieved documents are supplied to the LLM as context.

```text
Question
   +
Retrieved Context
   ↓
Prompt
   ↓
LLM
```

The model then generates an answer based on that context.

---

# RAG in the Current AI Architecture

RAG can become another capability of the LangGraph agent.

For example:

```text
                         LangGraph
                            │
                 ┌──────────┼──────────┐
                 ↓          ↓          ↓
               LLM        RAG        MCP
                │           │          │
                │           ↓          ↓
                │      Vector Store   Tools
                │
                └──────────┬───────────┘
                           ↓
                     Final Answer
```

The agent could decide:

```text
User:
"What does our restaurant policy say?"

             ↓

           LLM
             ↓
       Need knowledge?
             ↓
            RAG
             ↓
      Retrieve documents
             ↓
            LLM
             ↓
        Final answer
```

While an operational request could use MCP:

```text
User:
"Delete my restaurant post"

        ↓
      LLM
        ↓
      MCP
        ↓
 delete_post
```

This gives the overall system three important capabilities:

```text
LLM       → reasoning / generation
RAG       → knowledge retrieval
MCP       → external tools/actions
```

---

# Interview Mental Model

When asked to explain RAG, describe it as:

> "RAG is a two-stage architecture. During indexing, documents are loaded, chunked, embedded and stored in a vector store. During query time, the user's question is embedded and used to retrieve relevant chunks. Those chunks are then provided to the LLM as context so it can generate a grounded response."

Then explain the responsibilities:

```text
Load       → documents.py
Split      → chunking.py
Embed      → embeddings.py
Store      → vector_store.py
Retrieve   → retrieval.py
Generate   → generation.py
Orchestrate → service.py
```

This separation keeps the RAG implementation modular and makes it easier to replace an individual component, such as the embedding model or vector store.
