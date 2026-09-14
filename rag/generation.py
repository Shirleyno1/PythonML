import os

from dotenv import load_dotenv
from openai import AsyncOpenAI


class GenerationService:

    def __init__(
            self,
            model: str = "gpt-5-mini",
    ):
        self.model = model
        load_dotenv()
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    async def generate(
            self,
            question: str,
            context: str,
    ):

        system_prompt = """
        You are a helpful assistant answering questions
        using the provided context.

        Rules:

        1. Answer using the provided context.
        2. If the context does not contain enough information,
           say that you don't have enough information.
        3. Do not invent facts.
        4. Keep the answer clear and concise.
        """

        response = await self.client.responses.create(
            model=self.model,
            instructions=system_prompt,
            input=f"""
Context:

{context}

Question:

{question}         
"""
        )

        return response.output_text