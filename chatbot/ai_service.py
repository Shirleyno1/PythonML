import os

from dotenv import load_dotenv
from openai import OpenAI

from chatbot.models import AIResponse
from chatbot.user_intent import UserIntent

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

def classify_message(
        message: str,
) -> UserIntent:

    response = client.responses.parse(
        model="gpt-5-mini",
        input=[
            {
                "role": "system",
                "content": """
You are an intent classifier for a post management application.

Classify the user's message into exactly one of:

- search
- create
- delete
- general

Rules:

search:
The user wants to find, search, or retrieve posts.

create:
The user wants to create a new post.

delete:
The user wants to delete a post.

general:
The user is asking a general question that does not require
post management.

If the intent is search, extract the search query.

If the intent is not search, query should be null.
"""
            },
            {
                "role": "user",
                "content": message
            }
        ],
        text_format=UserIntent
    )

    return response.output_parsed
