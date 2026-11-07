
from copy import deepcopy


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
                    {
                        "search_posts": (
                            "List public posts from all users, newest first, optionally filtered by "
                            "post type. Post type is the only filter. When the user asks to search or "
                            "see posts, call this straight away instead of asking how to narrow it."
                        ),
                        "search_documents": (
                            "Search the reference documents, which currently hold a restaurant "
                            "Q&A covering hours, location, reservations, menu and events. Always "
                            "call it before answering a question on those topics, and answer only "
                            "from the passages it returns. If it returns nothing, say the documents "
                            "don't cover that."
                        ),
                        "delete_post": "Ask the authenticated user to confirm deleting one of their own posts. The post is deleted only if they accept.",
                    }.get(tool.name, tool.description)
                ),
                "parameters": parameters,
            })

        return openai_tools