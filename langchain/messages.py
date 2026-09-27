from langchain_core.messages import SystemMessage, HumanMessage

from langchain.models import model

messages = [
    SystemMessage(
        content="You are an AI assistant."
    ),
    HumanMessage(
         content="What is TAG?"
    )
]

response = model.invoke(messages)
print(response.content)