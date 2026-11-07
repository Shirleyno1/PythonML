"""Every prompt the app sends to a model, under the name it has in LangSmith.

These are the local copies. With LANGSMITH_PROMPTS_ENABLED, the app uses the
LangSmith prompt of the same name instead, and its model if one is saved with
it. Message templates use f-string variables, so a literal brace is written {{ }}.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class PromptSpec:
    name: str
    description: str
    messages: tuple[tuple[str, str], ...]
    # None means settings.OPENAI_MODEL.
    model: str | None = None
    # Tool descriptions are text, not a model call, so no model goes with them.
    uses_model: bool = True

    @property
    def optional(self) -> bool:
        """Calls that send no instructions today; a LangSmith prompt can add some."""
        return not self.messages


INTENT_CLASSIFIER = PromptSpec(
    name="pythonml-intent-classifier",
    description="Classifies a chat message as search, create, delete or general (/ai).",
    messages=(
        (
            "system",
            """You are an intent classifier for a personal post management application.

Your job is to classify the user's message into exactly one of these intents:

- search
- create
- delete
- update
- general

Rules:

search:
The user wants to find, search, or retrieve posts.

create:
The user wants to create a new post.

delete:
The user wants to delete a post.

general:
The user is asking a general question that does not require
post management.

If the intent is search, extract the search query.

If the intent is not search, query should be null.

In the intent is delete, extract the query, it will be post id that want to delete.""",
        ),
        ("human", "{message}"),
    ),
)

STRUCTURED_ANSWER = PromptSpec(
    name="pythonml-structured-answer",
    description="Answers with a title and summary (/chat/structured).",
    messages=(("human", "{message}"),),
)

CHAT_ASSISTANT = PromptSpec(
    name="pythonml-chat-assistant",
    description="Single-turn chat (/chat).",
    messages=(
        ("system", "You are a helpful AI assistang. Answer clearly and concisely"),
        ("human", "{message}"),
    ),
)

CHAT_STREAM = PromptSpec(
    name="pythonml-chat-stream",
    description=(
        "Streaming chat (/chat/stream). Sends only the conversation today; a LangSmith "
        "prompt's messages go before it."
    ),
    messages=(),
)

AGUI_AGENT = PromptSpec(
    name="pythonml-agui-agent",
    description=(
        "The tool-calling agent behind /ai/agui and /ai/mcp. Sends no instructions today; "
        "a LangSmith prompt's messages go before the conversation."
    ),
    messages=(),
)

RAG_ANSWER = PromptSpec(
    name="pythonml-rag-answer",
    description="Answers from retrieved document passages (/rag).",
    messages=(
        (
            "system",
            """You are a helpful assistant answering questions
using the provided context.

Rules:

1. Answer using the provided context.
2. If the context does not contain enough information,
   say that you don't have enough information.
3. Do not invent facts.
4. Keep the answer clear and concise.""",
        ),
        (
            "human",
            """Context:

{context}

Question:

{question}""",
        ),
    ),
)

LANGCHAIN_RAG = PromptSpec(
    name="pythonml-langchain-rag",
    description="Answers from retrieved document passages (/langchain/rag).",
    messages=(
        (
            "human",
            """Answer the question using only the context below.

Context:
{context}

Question:
{question}""",
        ),
    ),
)

SEARCH_POSTS_TOOL = PromptSpec(
    name="pythonml-tool-search-posts",
    description="What the agent is told the search_posts tool does.",
    messages=(
        (
            "system",
            "List public posts from all users, newest first, optionally filtered by post "
            "type. Post type is the only filter. When the user asks to search or see posts, "
            "call this straight away instead of asking how to narrow it.",
        ),
    ),
    uses_model=False,
)

SEARCH_DOCUMENTS_TOOL = PromptSpec(
    name="pythonml-tool-search-documents",
    description="What the agent is told the search_documents tool does.",
    messages=(
        (
            "system",
            "Search the reference documents, which currently hold a restaurant Q&A covering "
            "hours, location, reservations, menu and events. Always call it before answering "
            "a question on those topics, and answer only from the passages it returns. If it "
            "returns nothing, say the documents don't cover that.",
        ),
    ),
    uses_model=False,
)

DELETE_POST_TOOL = PromptSpec(
    name="pythonml-tool-delete-post",
    description="What the agent is told the delete_post tool does.",
    messages=(
        (
            "system",
            "Ask the authenticated user to confirm deleting one of their own posts. The post "
            "is deleted only if they accept.",
        ),
    ),
    uses_model=False,
)

ALL_PROMPTS = (
    INTENT_CLASSIFIER,
    STRUCTURED_ANSWER,
    CHAT_ASSISTANT,
    CHAT_STREAM,
    AGUI_AGENT,
    RAG_ANSWER,
    LANGCHAIN_RAG,
    SEARCH_POSTS_TOOL,
    SEARCH_DOCUMENTS_TOOL,
    DELETE_POST_TOOL,
)
