import json
from collections.abc import Awaitable, Callable
from typing import Any

from fastapi.encoders import jsonable_encoder

from observability.tracing import (
    ai_traceable,
    trace_agent_input,
    trace_delete_confirmation_input,
    trace_tool_input,
)
from posts.db import async_session_maker
from posts.repository import PostRepository
from posts.service import PostService

SEARCH_POSTS_TOOL = "search_posts"
DELETE_POST_TOOL = "delete_post"
MAX_POST_CARDS = 10
POST_CARDS_SHOWN_NOTE = (
    "The app shows the user these posts as a visual list under your reply, so don't "
    "list or repeat them. Introduce them in one short sentence, or answer directly if "
    "the user asked something specific about them."
)
DELETE_NOT_FOUND_RESULT = (
    "Nothing was deleted: this post doesn't exist or doesn't belong to the user."
)
DELETE_CONFIRMATION_SHOWN_RESULT = (
    "The post has NOT been deleted. The app is showing the user a confirmation prompt, "
    "and the post is deleted only if they accept it. Tell them to check the prompt, and "
    "don't say the post was deleted."
)
DELETE_CONFIRMATION_UNAVAILABLE_RESULT = (
    "The post has NOT been deleted. Deleting needs a confirmation this chat can't show, "
    "so tell the user to delete the post from their posts screen."
)


async def find_own_post(post_id: str, user_id: str) -> dict[str, Any] | None:
    async with async_session_maker() as session:
        service = PostService(PostRepository(session))
        # Encoded here because it goes onto the event stream, which needs plain JSON.
        return jsonable_encoder(
            await service.get_own_post_for_confirmation(post_id, user_id)
        )


class AgentOrchestrator:

    def __init__(
            self,
            openai_client,
            mcp_client,
            schema_adapter,
            post_lookup: Callable[[str, str], Awaitable[dict[str, Any] | None]] = find_own_post,
    ):
        self.openai_client = openai_client
        self.mcp_client = mcp_client
        self.schema_adapter = schema_adapter
        self.post_lookup = post_lookup

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
        on_tool_event: Callable[[dict[str, Any]], Awaitable[None]] | None = None,
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

            # Cards wait for the end of the run: the model also searches to find a
            # post to delete, and the user shouldn't see a list then.

            found_posts: list[dict] = []
            delete_requested = False

            # 4. Agent loop

            while True:

                tool_calls = self._get_tool_calls(response.output)

                # No tool call means the model has produced the final answer
                if not tool_calls:
                    if found_posts and not delete_requested:
                        await self._emit_tool_event(
                            on_tool_event,
                            {
                                "type": "post_results",
                                "posts": found_posts[:MAX_POST_CARDS],
                                "total": len(found_posts),
                            },
                        )
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

                    if tool_call["name"] == DELETE_POST_TOOL:

                        # The model can only ask for a delete. The post is deleted
                        # when the user accepts the prompt and the app calls the API.

                        delete_requested = True
                        tool_result = await self._request_delete_confirmation(
                            arguments=arguments,
                            user_id=user_id,
                            tool_call_id=tool_call["call_id"],
                            on_tool_event=on_tool_event,
                        )
                    else:

                        # 6. Call MCP dynamically

                        result = await self._call_tool(
                            name=tool_call["name"],
                            arguments=arguments,
                        )

                        # 7. Convert MCP result into something OpenAI can read

                        tool_result = self._serialize_result(result)

                        if tool_call["name"] == SEARCH_POSTS_TOOL and on_tool_event is not None:
                            found_posts = self._get_posts(result)
                            if found_posts:
                                tool_result = f"{tool_result}\n\n{POST_CARDS_SHOWN_NOTE}"
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

    @ai_traceable(
        name="AG-UI Delete Confirmation",
        component="agui-tool",
        run_type="tool",
        process_inputs=trace_delete_confirmation_input,
    )
    async def _request_delete_confirmation(
        self,
        arguments: dict[str, Any],
        user_id: str,
        tool_call_id: str,
        on_tool_event: Callable[[dict[str, Any]], Awaitable[None]] | None,
    ) -> str:
        post = await self.post_lookup(str(arguments.get("post_id")), user_id)
        if post is None:
            return DELETE_NOT_FOUND_RESULT
        if on_tool_event is None:
            return DELETE_CONFIRMATION_UNAVAILABLE_RESULT

        await on_tool_event(
            {
                "type": "delete_confirmation",
                "tool_call_id": tool_call_id,
                "post_id": post["id"],
                "title": post["title"],
                "post": post["post"],
            }
        )
        return DELETE_CONFIRMATION_SHOWN_RESULT

    @staticmethod
    async def _emit_tool_event(
        callback: Callable[[dict[str, Any]], Awaitable[None]] | None,
        event: dict[str, Any],
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
    def _get_posts(result: Any) -> list[dict]:
        posts = getattr(result, "data", result)
        return posts if isinstance(posts, list) else []

    @staticmethod
    def _serialize_result(
            result: Any,
    ) -> str:

        return str(result)
