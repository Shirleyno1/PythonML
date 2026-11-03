from openai import AsyncOpenAI

from observability.tracing import ai_traceable, trace_model_output


class OpenAIClient:

    def __init__(
            self,
            api_key: str,
    ):
        self.client = AsyncOpenAI(api_key=api_key)

    @ai_traceable(
        name="AG-UI Model Response",
        component="agui-model",
        run_type="llm",
        process_outputs=trace_model_output,
    )
    async def create_response(
            self,
            message: str | list[dict[str, str]],
            tools: list
    ):

        response = await self.client.responses.create(
            model = "gpt-5-mini",
            input = message,
            tools = tools
        )

        print(f"create_response: {response}")

        return response

    @ai_traceable(
        name="AG-UI Model Response With Tool Result",
        component="agui-model",
        run_type="llm",
        process_outputs=trace_model_output,
    )
    async def create_response_with_tool_result(
            self,
            response_id: str,
            tool_call_id: str,
            tool_result: str,
            tools: list,
    ):

        result = await self.client.responses.create(
            model = "gpt-5-mini",
            previous_response_id=response_id,

            input = [
                {
                    "type": "function_call_output",
                    "call_id": tool_call_id,
                    "output": tool_result,
                }
            ],

            tools = tools
        )

        print(f"create_response_with_tool_result: {result}")

        return result