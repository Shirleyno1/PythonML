from langchain.models import model
from langchain.prompts import prompt


chain = prompt | model

response = chain.invoke({
    "domain": "AI",
    "question": "What is RAG?"
})

print(response.content)