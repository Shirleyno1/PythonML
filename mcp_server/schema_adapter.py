

class SchemaAdapter:

    @staticmethod
    def mcp_tools_to_openai_tools(mcp_tools):
        return [
            {
                "type":  "function",
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.inputSchema,
            }
            for tool in mcp_tools
        ]