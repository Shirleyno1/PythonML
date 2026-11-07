from openai import AsyncOpenAI

from ai_prompts import catalog, get_prompt
from observability.tracing import ai_traceable, trace_model_output, traced_openai


class OpenAIClient:

    def __init__(
            self,
            api_key: str,
    ):
        self.client = traced_openai(AsyncOpenAI(api_key=api_key))

    @ai_traceable(
        name="AG-UI Model Response",
        component="agui-model",
        run_type="chain",
        process_outputs=trace_model_output,
    )
    async def create_response(
            self,
            message: str | list[dict[str, str]],
            tools: list
    ):

        prompt = get_prompt(catalog.AGUI_AGENT)
        if isinstance(message, str):
            message = [{"role": "user", "content": message}]
        response = await self.client.responses.create(
            model = prompt.model,
            input = [*prompt.to_messages(), *message],
            tools = tools
        )

        print(f"create_response: {response}")

        return response

    @ai_traceable(
        name="AG-UI Model Response With Tool Result",
        component="agui-model",
        run_type="chain",
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
            # The prompt's messages came with the first request, via previous_response_id.
            model = get_prompt(catalog.AGUI_AGENT).model,
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