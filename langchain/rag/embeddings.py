import os

from dotenv import load_dotenv
from langchain_community.embeddings import OpenAIEmbeddings

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

embeddings = OpenAIEmbeddings(
    api_key=api_key,
    model="text-embedding-3-small"
)