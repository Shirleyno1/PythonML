import json
from collections.abc import Awaitable, Callable
from typing import Any

from observability.tracing import ai_traceable, trace_agent_input, trace_tool_input


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

    @ai_traceable(
        name="AG-UI Agent Run",
        component="agui-agent",
        run_type="chain",
        process_inputs=trace_agent_input,
    )
    async def run_agent(
        self,
        message: str,
        user_id: str,
        history: list[dict[str, str]] | None = None,
        on_tool_event: Callable[[dict[str, str]], Awaitable[None]] | None = None,
    ):

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

            input_messages = [
                *(history or [])[-19:],
                {"role": "user", "content": message},
            ]
            response = await self.openai_client.create_response(
                message=input_messages,
                tools=openai_tools,
            )

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
                    public_arguments = dict(arguments)
                    if tool_call["name"] in {"search_posts", "delete_post"}:
                        public_arguments.pop("user_id", None)
                    await self._emit_tool_event(
                        on_tool_event,
                        {
                            "type": "start",
                            "tool_call_id": tool_call["call_id"],
                            "tool_name": tool_call["name"],
                        },
                    )
                    await self._emit_tool_event(
                        on_tool_event,
                        {
                            "type": "args",
                            "tool_call_id": tool_call["call_id"],
                            "arguments": json.dumps(public_arguments),
                        },
                    )
                    await self._emit_tool_event(
                        on_tool_event,
                        {
                            "type": "end",
                            "tool_call_id": tool_call["call_id"],
                        },
                    )
                    if tool_call["name"] in {"search_posts", "delete_post"}:
                        arguments["user_id"] = user_id

                    # 6. Call MCP dynamically

                    result = await self._call_tool(
                        name=tool_call["name"],
                        arguments=arguments,
                    )

                    # 7. Convert MCP result into something OpenAI can read

                    tool_result = self._serialize_result(result)
                    await self._emit_tool_event(
                        on_tool_event,
                        {
                            "type": "result",
                            "tool_call_id": tool_call["call_id"],
                            "content": tool_result,
                        },
                    )

                    # 8. Give tool result back to the model

                    response = (
                        await self.openai_client.create_response_with_tool_result(
                            response_id = response.id,
                            tool_call_id = tool_call["call_id"],
                            tool_result = tool_result,
                            tools = openai_tools,
                        )
                    )

    @ai_traceable(
        name="AG-UI MCP Tool Call",
        component="agui-tool",
        run_type="tool",
        process_inputs=trace_tool_input,
    )
    async def _call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        return await self.mcp_client.call_tool(name=name, arguments=arguments)

    @staticmethod
    async def _emit_tool_event(
        callback: Callable[[dict[str, str]], Awaitable[None]] | None,
        event: dict[str, str],
    ) -> None:
        if callback is not None:
            await callback(event)


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
