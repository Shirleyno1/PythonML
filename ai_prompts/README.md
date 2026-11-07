# Prompts and models

Every prompt the app sends to a model is in `catalog.py`, under the name it has
in LangSmith. Call sites ask `get_prompt(catalog.X)` for the messages and model.

## Using LangSmith

| Setting | Meaning |
|---|---|
| `LANGSMITH_PROMPTS_ENABLED=true` | Use the LangSmith prompt of each name, and the OpenAI model saved with it. Needs `LANGSMITH_API_KEY`. |
| `LANGSMITH_PROMPT_TAG=production` | Use the commit with this tag instead of the latest one. |
| `OPENAI_MODEL` | Model for calls whose prompt has no model saved. Default `gpt-5-mini`. |

To create the prompts from the local copies:

```
uv run python -m ai_prompts.push           # list what's missing
uv run python -m ai_prompts.push --apply   # create it; existing prompts are left alone
```

If LangSmith can't be reached, a prompt doesn't exist, or it uses a variable the
app doesn't supply, the local copy is used and LangSmith isn't asked again for
that prompt for 5 minutes. Pulled prompts are cached by the LangSmith client and
refreshed in the background, so an edit takes effect within minutes, without a
deploy. `/langchain/rag` is the exception: it builds its chain once, so it needs
a restart.

Only OpenAI models are used; another provider's model saved with a prompt is
ignored.

## Prompts

| LangSmith name | Used by | Variables |
|---|---|---|
| `pythonml-intent-classifier` | `/ai` intent classification | `message` |
| `pythonml-structured-answer` | `/chat/structured` | `message` |
| `pythonml-chat-assistant` | `/chat` | `message` |
| `pythonml-chat-stream` | `/chat/stream`, before the conversation | none |
| `pythonml-agui-agent` | `/ai/agui` and `/ai/mcp` agent, before the conversation | none |
| `pythonml-rag-answer` | `/rag` | `context`, `question` |
| `pythonml-langchain-rag` | `/langchain/rag` and the RAG evaluation | `context`, `question` |
| `pythonml-tool-search-posts` | Agent's description of `search_posts` | none |
| `pythonml-tool-search-documents` | Agent's description of `search_documents` | none |
| `pythonml-tool-delete-post` | Agent's description of `delete_post` | none |

`pythonml-chat-stream` and `pythonml-agui-agent` have no local messages, because
those calls send no instructions today. Create them in LangSmith to add some;
their messages go before the conversation history.

Tool descriptions use the first message's text. The tool-result notes in
`chatbot/orchestrator.py` (for example, that a post has not been deleted until
the user confirms) stay in code, because the delete flow's tests depend on them.
