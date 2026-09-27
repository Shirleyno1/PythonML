# LangChain

This folder contains hands-on learning and examples for **LangChain**, focusing on the core building blocks used to develop LLM applications.

The goal is to understand how LangChain components work individually and how they can be composed into larger AI applications such as:

* LLM applications
* Structured-output workflows
* RAG
* Tool calling
* Agents
* AI orchestration

---

# 1. Folder Structure

```text
lang_chain/
├── README.md
├── chains.py
├── messages.py
├── models.py
├── parsers.py
├── prompts.py
├── runnables.py
├── structured_output.py
└── tools.py
```

Each file focuses on a specific LangChain concept.

---

# 2. LangChain Overview

At a high level:

```text
User Input
    ↓
Prompt
    ↓
Model
    ↓
Parser
    ↓
Application Result
```

LangChain provides reusable abstractions for each part of this workflow.

For example:

```python
chain = prompt | model | parser
```

The `|` operator is used to compose components together.

```text
Prompt
  ↓
Model
  ↓
Parser
```

The output from one component becomes the input to the next component.

---

# 3. models.py

`models.py` focuses on interacting with LLMs.

A model is responsible for receiving input and generating a response.

Conceptually:

```text
Application
    ↓
Model
    ↓
LLM Provider
    ↓
Response
```

A simple example:

```python
from langchain_openai import ChatOpenAI

model = ChatOpenAI(
    model="gpt-5-mini"
)

response = model.invoke("What is RAG?")

print(response)
```

For asynchronous applications:

```python
response = await model.ainvoke("What is RAG?")
```

This is particularly useful when integrating LangChain with FastAPI.

---

# 4. messages.py

`messages.py` explores the different types of messages used when communicating with chat models.

Common message types include:

```text
SystemMessage
HumanMessage
AIMessage
ToolMessage
```

For example:

```python
from langchain_core.messages import (
    SystemMessage,
    HumanMessage,
)

messages = [
    SystemMessage(
        content="You are a helpful AI assistant."
    ),
    HumanMessage(
        content="What is RAG?"
    ),
]

response = model.invoke(messages)

print(response.content)
```

The message structure allows an application to represent conversations explicitly.

---

# 5. prompts.py

`prompts.py` focuses on creating reusable prompts.

Instead of constructing strings manually, LangChain provides prompt templates.

Example:

```python
from langchain_core.prompts import ChatPromptTemplate

prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        "You are a helpful AI assistant."
    ),
    (
        "human",
        "{question}"
    ),
])
```

The variable can then be supplied:

```python
messages = prompt.invoke({
    "question": "What is RAG?"
})
```

Prompts can also contain multiple variables:

```python
prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        "Answer the question using the context."
    ),
    (
        "human",
        """
        Context:
        {context}

        Question:
        {question}
        """
    ),
])
```

This pattern is particularly useful for RAG.

---

# 6. parsers.py

Output parsers convert model responses into formats that application code can work with.

For example:

```python
from langchain_core.output_parsers import StrOutputParser

parser = StrOutputParser()
```

A model response can then be converted into a string:

```text
Model response
      ↓
StrOutputParser
      ↓
Python string
```

Example:

```python
chain = prompt | model | StrOutputParser()

result = chain.invoke({
    "question": "What is RAG?"
})

print(result)
```

Other useful parsers include:

```text
StrOutputParser
JsonOutputParser
PydanticOutputParser
```

Structured output is covered separately in `structured_output.py`.

---

# 7. structured_output.py

This file focuses on getting structured data from an LLM.

This is particularly important when an LLM response needs to drive application logic.

For example, instead of asking the model to return:

```text
I think the user wants to search for restaurants.
```

we can define a schema:

```python
from pydantic import BaseModel


class Intent(BaseModel):
    intent: str
    query: str
```

The model can then return structured data such as:

```python
Intent(
    intent="search",
    query="Italian restaurants"
)
```

Conceptually:

```text
User message
      ↓
     LLM
      ↓
Structured Output
      ↓
Pydantic Object
      ↓
Application Logic
```

This is especially useful for:

* Intent classification
* Tool selection
* Agent workflows
* API request generation
* Data extraction

---

# 8. runnables.py

`runnables.py` explores LangChain's **Runnable** abstraction.

Runnables are components that can be executed and composed together.

Common methods include:

```python
invoke()
ainvoke()
batch()
abatch()
stream()
astream()
```

For example:

```python
result = chain.invoke(input)
```

or asynchronously:

```python
result = await chain.ainvoke(input)
```

---

## Runnable Composition

LangChain allows multiple runnables to be composed:

```python
chain = prompt | model | parser
```

The flow is:

```text
Input
  ↓
Prompt Runnable
  ↓
Model Runnable
  ↓
Parser Runnable
  ↓
Output
```

This composition model is known as **LCEL — LangChain Expression Language**.

---

# 9. chains.py

`chains.py` focuses on combining LangChain components into reusable workflows.

A simple chain:

```python
chain = prompt | model | parser
```

Then:

```python
result = chain.invoke({
    "question": "What is RAG?"
})
```

The chain hides the individual steps behind one callable object.

Instead of:

```python
messages = prompt.invoke(...)
response = model.invoke(messages)
result = parser.invoke(response)
```

we can use:

```python
result = chain.invoke(...)
```

---

# 10. tools.py

`tools.py` focuses on giving an LLM access to external capabilities.

A tool is a function that the AI can request to execute.

For example:

```python
from langchain_core.tools import tool


@tool
def search_posts(query: str) -> str:
    """Search posts using a query."""
    ...
```

Conceptually:

```text
User
 ↓
LLM
 ↓
Decides a tool is needed
 ↓
search_posts()
 ↓
Tool result
 ↓
LLM
 ↓
Final response
```

The important distinction is that the LLM does **not** directly execute arbitrary application code.

The application defines which capabilities are available as tools.

---

# 11. Tools and MCP

Tools are closely related to the MCP work in this project.

The project currently has MCP tools such as:

```text
search_posts
delete_post
```

A simplified architecture is:

```text
                 LLM / Agent
                     │
                     ▼
                   Tool
                     │
                     ▼
                MCP Client
                     │
                     ▼
                MCP Server
                     │
                     ▼
             Application Logic
                     │
                     ▼
                 Database
```

LangChain tools therefore provide a useful foundation for understanding agent tool calling, while MCP provides a protocol for exposing tools across application boundaries.

---

# 12. Putting the Components Together

The core LangChain workflow can be represented as:

```text
                    User
                      │
                      ▼
                  Prompt
                      │
                      ▼
                    Model
                      │
             ┌────────┴────────┐
             │                 │
             ▼                 ▼
           Parser            Tool
             │                 │
             ▼                 ▼
        Application        Tool Result
             │                 │
             └────────┬────────┘
                      ▼
                   Response
```

For a simple LLM chain:

```python
chain = prompt | model | parser
```

For a tool-enabled AI application, the model can additionally interact with tools.

---

# 13. LangChain and RAG

The concepts learned here are also used by the project's RAG implementation.

A typical LangChain RAG pipeline is:

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
Vector Store
 ↓
Retriever
 ↓
Prompt
 ↓
Model
 ↓
Parser
 ↓
Answer
```

For example:

```python
documents = load_pdf("./data/Resturaunt Q&A.pdf")

chunks = split_documents(documents)

vector_store = FAISS.from_documents(
    documents=chunks,
    embedding=embeddings,
)

retriever = vector_store.as_retriever()
```

At query time:

```python
context = await retriever.ainvoke(question)
```

The retrieved chunks can then be passed to a prompt and model.

---

# 14. Sync vs Async

LangChain provides synchronous and asynchronous execution.

Synchronous:

```python
result = chain.invoke(input)
```

Asynchronous:

```python
result = await chain.ainvoke(input)
```

For a FastAPI application, asynchronous execution is useful when calling external services such as:

* LLM APIs
* Retrievers
* HTTP services
* Databases
* MCP servers

Example:

```python
async def answer_question(question: str):
    result = await chain.ainvoke({
        "question": question
    })

    return result
```

---

# 15. Key Concepts

| File                   | Concept           | Purpose                        |
| ---------------------- | ----------------- | ------------------------------ |
| `models.py`            | Models            | Communicate with LLMs          |
| `messages.py`          | Messages          | Represent conversations        |
| `prompts.py`           | Prompts           | Define model instructions      |
| `parsers.py`           | Output Parsers    | Convert model output           |
| `structured_output.py` | Structured Output | Return typed data              |
| `runnables.py`         | Runnables         | Compose executable components  |
| `chains.py`            | Chains            | Combine multiple steps         |
| `tools.py`             | Tools             | Give AI access to capabilities |

---

# 16. Important Relationships

The concepts are easier to remember as layers:

```text
Messages
   ↓
Prompts
   ↓
Models
   ↓
Parsers
```

These can then be combined using:

```text
Runnables
   ↓
Chains
```

And capabilities can be added through:

```text
Tools
   ↓
Agents
```

Structured output provides another way for the model to communicate reliably with application code.

---

# 17. Simple Example

A basic LangChain application can be reduced to:

```python
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate


prompt = ChatPromptTemplate.from_template(
    "Explain {topic} in simple terms."
)

model = ChatOpenAI(
    model="gpt-5-mini"
)

parser = StrOutputParser()

chain = prompt | model | parser


result = chain.invoke({
    "topic": "RAG"
})

print(result)
```

The architecture is:

```text
topic
 ↓
PromptTemplate
 ↓
ChatOpenAI
 ↓
StrOutputParser
 ↓
String
```

This small example demonstrates several of the core LangChain concepts in this folder.

---

# 18. Learning Progression

The concepts in this folder can be learned in this order:

```text
1. Models
      ↓
2. Messages
      ↓
3. Prompts
      ↓
4. Output Parsers
      ↓
5. Structured Output
      ↓
6. Runnables / LCEL
      ↓
7. Chains
      ↓
8. Tools
      ↓
9. Agents
      ↓
10. RAG
```

The goal is to understand **why each abstraction exists**, rather than simply memorising LangChain APIs.

---

# 19. LangChain vs LangGraph

LangChain and LangGraph solve related but different problems.

### LangChain

Useful for composing LLM application components:

```text
Prompt
 ↓
Model
 ↓
Parser
```

and:

```text
Model
 ↓
Tools
```

### LangGraph

Useful when the workflow requires explicit state and graph-based orchestration:

```text
              ┌───────────┐
              │ Classify  │
              └─────┬─────┘
                    ↓
             Conditional Edge
              ↙     ↓      ↘
          Search  Delete   General
              ↘     ↓      ↙
                  Response
```

A useful mental model is:

```text
LangChain
→ Building blocks

LangGraph
→ Stateful workflow/orchestration
```

---

# 20. LangChain in This Project

The LangChain learning is connected to the rest of the AI project:

```text
                    AI Application
                          │
          ┌───────────────┼────────────────┐
          │               │                │
          ▼               ▼                ▼
       FastAPI           RAG              MCP
          │               │                │
          │               ▼                ▼
          │           LangChain          Tools
          │
          ▼
       AI Agent
          │
          ▼
      LangGraph
```

This provides hands-on experience with the major building blocks of modern LLM applications.

---

# 21. Main Takeaway

The most important concept from this folder is that LangChain is a collection of composable abstractions.

Instead of treating an LLM call as:

```text
Input → LLM → Output
```

we can build:

```text
Input
 ↓
Prompt
 ↓
Model
 ↓
Parser
 ↓
Application
```

and extend it with:

```text
                    ┌── Tool
                    │
Input → Prompt → Model
                    │
                    └── Structured Output
```

These components can then be composed into chains, RAG pipelines, and agent-based applications.
