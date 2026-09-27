from langchain_core.prompts import ChatPromptTemplate

from langchain.models import model

prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        "You are an expert {domain} assistant."
    ),
    (
        "human",
        "{question}"
    )
])

messages = prompt.invoke({
    "domain": "AI",
    "question": "What is RAG?"
})

response = model.invoke(messages)

print(response.content)