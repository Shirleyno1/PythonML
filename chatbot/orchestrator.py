import json
from typing import Any


class AgentOrchestrator:

    def __init__(
            self,
            openai_client,
            mcp_client,
            schema_adapter,
    ):
        self.openai_client = openai_client
        self.mcp_client = mcp_client
        self.schema_adapter = schema_adapter

    async def run_agent(self, message: str):

        async with self.mcp_client:

            # 1. Discover MCP Tools

            tools = await self.mcp_client.list_tools()

            print("MCP Tools:")

            for tool in tools:
                print(tool.name)

            # 2. Convert MCP Tools to OpenAI Tools

            openai_tools = (
                self.schema_adapter.mcp_tools_to_openai_tools(tools)
            )

            # 3. Send user message + tools to OpenAI

            response = await self.openai_client.create_response(message = message, tools = openai_tools)

            # 4. Agent loop

            while True:

                tool_calls = self._get_tool_calls(response.output)

                # No tool call means the model has produced the final answer
                if not tool_calls:
                    return response.output_text

                # 5. Execute every requested tool

                for tool_call in tool_calls:

                    print(
                        f"Calling MCP tool: "
                        f"{tool_call['name']}"
                    )

                    arguments = json.loads(tool_call["arguments"])

                    # 6. Call MCP dynamically

                    result = await self.mcp_client.call_tool(
                        name = tool_call["name"],
                        arguments = arguments
                    )

                    # 7. Convert MCP result into something OpenAI can read

                    tool_result = self._serialize_result(result)

                    # 8. Give tool result back to the model

                    response = (
                        await self.openai_client.create_response_with_tool_result(
                            response_id = response.id,
                            tool_call_id = tool_call["call_id"],
                            tool_result = tool_result,
                            tools = openai_tools,
                        )
                    )



    @staticmethod
    def _get_tool_calls(output: list[Any]) -> list[dict]:

        tool_calls = []

        for item in output:

            if item.type == "function_call":
                tool_calls.append(
                    {
                        "call_id": item.call_id,
                        "name": item.name,
                        "arguments": item.arguments,
                    }
                )

        return tool_calls

    @staticmethod
    def _serialize_result(
            result: Any,
    ) -> str:

        return str(result)




