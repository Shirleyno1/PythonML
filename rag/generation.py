import os

from dotenv import load_dotenv
from openai import AsyncOpenAI

from ai_prompts import catalog, get_prompt
from observability.tracing import traced_openai


class GenerationService:

    def __init__(
            self,
            model: str | None = None,
    ):
        # None means the model of the rag answer prompt.
        self.model = model
        load_dotenv()
        self.client = traced_openai(AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY")))

    async def generate(
            self,
            question: str,
            context: str,
    ):
        prompt = get_prompt(catalog.RAG_ANSWER)
        response = await self.client.responses.create(
            model=self.model or prompt.model,
            input=prompt.to_messages(context=context, question=question),
        )

        return response.output_text
