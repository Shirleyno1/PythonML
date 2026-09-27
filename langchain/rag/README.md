# RAG

This package contains the **LangChain-based Retrieval-Augmented Generation (RAG)** implementation.

The RAG pipeline loads documents, splits them into chunks, converts the chunks into embeddings, stores them in a vector store, retrieves relevant documents, and passes the retrieved context to an LLM to generate an answer.

## Folder Structure

```text
rag/
├── __init__.py
├── documents.py
├── embeddings.py
├── vector_stores.py
├── retrievers.py
└── chain.py
```

## RAG Pipeline

```text
PDF / Documents
       ↓
documents.py
       ↓
Document chunks
       ↓
embeddings.py
       ↓
Embeddings
       ↓
vector_stores.py
       ↓
FAISS Vector Store
       ↓
retrievers.py
       ↓
Relevant Documents
       ↓
chain.py
       ↓
LLM
       ↓
Answer
```

## Responsibilities

### `documents.py`

Responsible for loading source documents.

For example, loading a PDF using `PyPDFLoader`:

```python
from langchain_community.document_loaders import PyPDFLoader


def load_pdf(path: str):
    loader = PyPDFLoader(path)
    return loader.load()
```

The loader returns LangChain `Document` objects containing:

* `page_content` — the document text
* `metadata` — information such as the source and page number

Document loading is normally **synchronous** because local file loading is not an external network operation.

---

### `embeddings.py`

Responsible for converting text into vectors.

Example:

```python
from langchain_openai import OpenAIEmbeddings


def create_embeddings():
    return OpenAIEmbeddings(
        model="text-embedding-3-small"
    )
```

Embeddings allow semantic similarity searches rather than relying only on exact keyword matching.

For online/request-time operations, embedding APIs can use asynchronous methods where supported:

```python
embeddings = create_embeddings()

vectors = await embeddings.aembed_documents(texts)
```

---

### `vector_stores.py`

Responsible for creating and loading the vector store.

Example using FAISS:

```python
from langchain_community.vectorstores import FAISS


def create_vector_store(documents, embeddings):
    return FAISS.from_documents(
        documents,
        embeddings
    )
```

The vector store contains the document embeddings and allows similarity searches.

For this learning project, **FAISS** is used as the local vector store.

---

### `retrievers.py`

Responsible for retrieving documents relevant to a user's question.

Example:

```python
def create_retriever(vector_store):
    return vector_store.as_retriever(
        search_kwargs={"k": 3}
    )
```

At request time, retrieval can be asynchronous:

```python
documents = await retriever.ainvoke(question)
```

The retrieved documents are then used as context for the LLM.

---

### `chain.py`

Responsible for combining the retrieved context with the user's question and calling the LLM.

A typical LangChain pipeline is:

```text
Prompt → Model → Parser
```

Example:

```python
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI


prompt = ChatPromptTemplate.from_template(
    """
    Answer the question using the following context.

    Context:
    {context}

    Question:
    {question}
    """
)

model = ChatOpenAI(
    model="gpt-5-mini"
)

chain = prompt | model
```

The `|` operator is **LangChain Expression Language (LCEL) composition**.

It connects the output of one runnable to the input of the next:

```text
prompt | model | parser
```

---

## Synchronous vs Asynchronous RAG

Not every part of RAG needs to be asynchronous.

### Offline indexing

Document loading and vector-store creation can remain synchronous:

```text
Load PDF
   ↓
Split documents
   ↓
Create embeddings
   ↓
Build FAISS index
```

This work can be performed when building or updating the index.

### Online query

The request-serving path should use asynchronous APIs where available:

```text
User Question
      ↓
await retriever.ainvoke()
      ↓
Relevant Documents
      ↓
await chain.ainvoke()
      ↓
Answer
```

Example:

```python
async def answer_question(question: str):
    documents = await retriever.ainvoke(question)

    context = "\n\n".join(
        document.page_content
        for document in documents
    )

    response = await chain.ainvoke({
        "context": context,
        "question": question,
    })

    return response
```

This fits naturally with an asynchronous FastAPI application.

> Note: FAISS itself is a local, synchronous library. Simply adding `async` to a function does not make FAISS operations non-blocking. For a learning project, keep the implementation simple. Thread offloading can be considered later if retrieval becomes CPU-heavy or affects concurrency.

## Example Usage

```python
from .documents import load_pdf
from .embeddings import create_embeddings
from .vector_stores import create_vector_store
from .retrievers import create_retriever


documents = load_pdf("./data/Resturaunt Q&A.pdf")

embeddings = create_embeddings()

vector_store = create_vector_store(
    documents,
    embeddings
)

retriever = create_retriever(vector_store)

results = retriever.invoke(
    "What restaurants are mentioned?"
)
```

For an async request:

```python
results = await retriever.ainvoke(
    "What restaurants are mentioned?"
)
```

## Key Concepts

| Component       | Purpose                              |
| --------------- | ------------------------------------ |
| Document Loader | Loads source documents               |
| Document        | Stores text and metadata             |
| Text Splitter   | Splits documents into smaller chunks |
| Embedding       | Converts text into vectors           |
| Vector Store    | Stores and searches vectors          |
| Retriever       | Finds relevant documents             |
| Prompt          | Formats context and question         |
| LLM             | Generates the answer                 |
| RAG Chain       | Combines retrieval and generation    |

## RAG vs Traditional Search

Traditional keyword search might look for:

```text
"Italian restaurant"
```

RAG retrieval using embeddings can find semantically related content even when the exact words are different.

A RAG system therefore combines:

```text
Semantic Retrieval
       +
LLM Generation
```

## Learning Goal

This package is a **LangChain implementation of RAG** for learning and comparison with the original custom RAG implementation.

The original RAG implementation separates the underlying concepts manually, while this package demonstrates how LangChain provides abstractions such as:

* `Document`
* document loaders
* embeddings
* vector stores
* retrievers
* prompts
* runnables
* chains
* asynchronous invocation
