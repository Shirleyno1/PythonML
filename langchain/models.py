import os

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI


load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

model = ChatOpenAI(
    api_key=api_key,
    model="gpt-5-mini",
    temperature=0
)

response = model.invoke("")

print(response.content)