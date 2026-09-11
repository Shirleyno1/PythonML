import os

from dotenv import load_dotenv
from openai import OpenAI

from chatbot.models import AIResponse


load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def generate_structured_response(
        message: str
) -> AIResponse:

    response = client.responses.parse(
        model="gpt-5-mini",
        input=message,
        text_format=AIResponse
    )
    result = response.output_parsed
    print(f"Title is {result.title}\nSummary is {result.summary}")

    return result
