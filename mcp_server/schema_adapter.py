
from copy import deepcopy

from ai_prompts import catalog, get_prompt

# The agent sees these tools described by the prompt catalog, not the MCP server.
TOOL_DESCRIPTIONS = {
    "search_posts": catalog.SEARCH_POSTS_TOOL,
    "search_documents": catalog.SEARCH_DOCUMENTS_TOOL,
    "delete_post": catalog.DELETE_POST_TOOL,
}


class SchemaAdapter:

    @staticmethod
    def mcp_tools_to_openai_tools(mcp_tools):
        openai_tools = []
        for tool in mcp_tools:
            parameters = deepcopy(tool.inputSchema)
            if tool.name in {"search_posts", "delete_post"}:
                parameters.get("properties", {}).pop("user_id", None)
                required = parameters.get("required", [])
                if "user_id" in required:
                    required.remove("user_id")

            openai_tools.append({
                "type":  "function",
                "name": tool.name,
                "description": (
                    get_prompt(TOOL_DESCRIPTIONS[tool.name]).text()
                    if tool.name in TOOL_DESCRIPTIONS
                    else tool.description
                ),
                "parameters": parameters,
            })

        return openai_tools