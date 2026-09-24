# AI Graph

This folder contains the LangGraph implementation of the AI agent workflow.

The graph separates the agent into four main responsibilities:

```text
                    ┌──────────────┐
                    │    START     │
                    └──────┬───────┘
                           ↓
                    ┌──────────────┐
                    │     LLM      │
                    │    Node      │
                    └──────┬───────┘
                           ↓
                   should_continue()
                     /           \
                    /             \
               "tools"           "end"
                  ↓                 ↓
          ┌──────────────┐       END
          │    Tools     │
          │     Node     │
          └──────┬───────┘
                 │
                 └──────────→ LLM
```

## Files

### `state.py`

Defines the **state carried through the graph**.

State is the shared data that nodes can read and update while the graph executes.

Example:

```python
from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
```

The `messages` field contains the conversation and tool-call messages needed by the agent.

As the application becomes more complex, state can contain additional information:

```python
class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    user_id: str
    conversation_summary: str
    tool_results: list
    retry_count: int
```

The important concept is:

> **State is the working memory of the graph.**

It is not necessarily the same as the entire conversation that should always be sent to the LLM.

---

## `nodes.py`

Contains the individual **nodes** that perform work.

A node is simply a function that receives the current state and returns an update to the state.

For example, the LLM node:

```python
async def call_model(state: AgentState):
    response = await model.ainvoke(
        state["messages"]
    )

    return {
        "messages": [response]
    }
```

Conceptually:

```text
State
  ↓
LLM Node
  ↓
Updated State
```

Other possible nodes include:

```text
LLM Node
   ↓
RAG Node
   ↓
Tool Node
   ↓
Validation Node
   ↓
Human Approval Node
```

Each node should have a focused responsibility.

---

## `edges.py`

Contains the **routing logic** for the graph.

An edge determines what should execute next.

For example:

```python
def should_continue(state: AgentState):
    last_message = state["messages"][-1]

    if last_message.tool_calls:
        return "tools"

    return "end"
```

This function does not execute the tool.

It only answers:

> **"Where should the graph go next?"**

The result can then be mapped to graph nodes:

```python
graph.add_conditional_edges(
    "llm",
    should_continue,
    {
        "tools": "tools",
        "end": END,
    }
)
```

The mapping means:

```text
Routing result        Destination
──────────────────    ─────────────
"tools"          →    tools node
"end"            →    END
```

This allows the routing decision to be separated from the actual graph structure.

---

## `graph.py`

Responsible for **building and compiling the LangGraph**.

It connects:

* State
* Nodes
* Edges
* Tool nodes
* Start/end points

Example:

```python
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode

from .state import AgentState
from .nodes import AgentNodes
from .edges import should_continue


class AgentGraph:

    def __init__(self, model, tools):
        self.model = model
        self.tools = tools

    def build(self):

        graph = StateGraph(AgentState)

        nodes = AgentNodes(
            self.model,
            self.tools
        )

        graph.add_node(
            "llm",
            nodes.call_model
        )

        graph.add_node(
            "tools",
            ToolNode(self.tools)
        )

        graph.add_edge(
            START,
            "llm"
        )

        graph.add_conditional_edges(
            "llm",
            should_continue,
            {
                "tools": "tools",
                "end": END,
            }
        )

        graph.add_edge(
            "tools",
            "llm"
        )

        return graph.compile()
```

The resulting workflow is:

```text
START
  ↓
LLM
  ↓
Does the LLM want to call a tool?
  │
  ├── No ──→ END
  │
  └── Yes
       ↓
     Tools
       ↓
      LLM
       ↓
     ...
```

The loop continues until the LLM produces a final response without requesting another tool.

---

# How the four files work together

The responsibilities are intentionally separated:

```text
                  graph.py
              Builds the workflow
                     │
        ┌────────────┼────────────┐
        ↓            ↓            ↓
     state.py     nodes.py     edges.py
        │            │            │
      State        Work        Routing
        │            │            │
        └────────────┼────────────┘
                     ↓
              Compiled Graph
```

### `state.py`

> What data does the workflow carry?

### `nodes.py`

> What work does the workflow perform?

### `edges.py`

> Where should the workflow go next?

### `graph.py`

> How are everything connected together?

---

# Relationship to the existing AgentOrchestrator

Before LangGraph, the agent workflow was manually implemented in the orchestrator.

Conceptually:

```python
response = await openai(message)

if response.requests_tool:

    result = await mcp.call_tool(...)

    response = await openai(
        message,
        tool_result=result
    )

return response
```

LangGraph makes this workflow explicit:

```text
                 Manual Orchestrator

                       if
                       │
                       ↓
                   Tool call
                       │
                       ↓
                    OpenAI
```

becomes:

```text
                    LangGraph

                    State
                      │
                      ↓
                  LLM Node
                      │
                      ↓
              Conditional Edge
                 /          \
                /            \
             Tools           END
               │
               ↓
           MCP Tool
               │
               ↓
             LLM Node
```

This makes the workflow easier to extend with:

* retries
* persistent state
* conversation memory
* human approval
* RAG
* validation
* streaming
* multi-agent workflows

---

# LangGraph + MCP

LangGraph and MCP have different responsibilities.

```text
LangGraph
    │
    │ decides
    │ "which tool should I use?"
    ↓
MCP Client
    │
    │ communicates with
    ↓
MCP Server
    │
    ↓
Backend Tool
```

### LangGraph

Responsible for:

* orchestration
* state
* workflow
* routing
* loops
* agent decisions

### MCP

Responsible for:

* exposing tools
* standardizing tool interfaces
* connecting agents to external capabilities

Therefore:

> **LangGraph orchestrates the workflow; MCP standardizes access to tools and external capabilities.**

---

# Long Conversations

For a long-running conversation, the state should not necessarily contain an ever-growing list of messages that is always sent to the LLM.

A production-oriented state can separate:

```text
State
├── recent messages
├── conversation summary
├── user information
├── tool results
├── workflow status
└── retry information
```

For example:

```python
class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    conversation_summary: str
    user_id: str
    tool_results: list
    retry_count: int
```

Older conversation can be summarized while recent messages remain available to the model.

This separates:

```text
LangGraph State
        ≠
LLM Context Window
```

State represents the workflow's working memory, while the context sent to the model can be selected and managed separately.

---

# Mental Model

The easiest way to remember LangGraph is:

```text
Graph = the whole workflow

Node = a piece of work

Edge = the path to the next piece of work

State = the data carried between pieces of work
```

For this project:

```text
             ┌───────────────────┐
             │       Graph       │
             │                   │
             │  ┌─────┐          │
START ──────→│  │ LLM │          │
             │  └──┬──┘          │
             │     │             │
             │     ↓             │
             │  Conditional      │
             │   /       \       │
             │  ↓         ↓      │
             │Tools      END      │
             │  │                │
             │  └──→ LLM         │
             └───────────────────┘
```

The **state travels through the graph**, nodes perform work, and edges determine what happens next.
