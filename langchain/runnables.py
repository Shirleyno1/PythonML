from langchain_core.runnables import RunnableLambda


def clean_text(text:str) -> str:
    return text.strip().lower()

cleaner = RunnableLambda(clean_text)

result = cleaner.invoke("    HELLO WORLD  ")

print(result)