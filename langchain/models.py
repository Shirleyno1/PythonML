from langchain_openai import ChatOpenAI

from settings.config import settings

model = ChatOpenAI(
    api_key=settings.OPENAI_API_KEY,
    model="gpt-5-mini",
    temperature=0,
)