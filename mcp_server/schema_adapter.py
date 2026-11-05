
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
                        "search_posts": "Search public posts from all users, optionally filtered by post type.",
                        "delete_post": "Ask the authenticated user to confirm deleting one of their own posts. The post is deleted only if they accept.",
                    }.get(tool.name, tool.description)
                ),
                "parameters": parameters,
            })

        return openai_tools