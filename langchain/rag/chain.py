from langchain_core.runnables import Runnable, RunnableLambda, RunnablePassthrough
from langchain_openai import ChatOpenAI

from ai_prompts import catalog, get_prompt
from settings.config import settings


def build_answer_chain() -> Runnable:
    """Prompt and model; takes {"context", "question"}. Resolved once per call."""
    prompt = get_prompt(catalog.LANGCHAIN_RAG)
    model = ChatOpenAI(api_key=settings.OPENAI_API_KEY, model=prompt.model, temperature=0)
    return prompt.template | model


def build_rag_chain(retriever: Runnable) -> Runnable:
    return (
            {
                "context": retriever | RunnableLambda(format_documents),
                "question": RunnablePassthrough(),
            }
            | build_answer_chain()
    )


def format_documents(documents) -> str:
    return "\n\n".join(
        doc.page_content
        for doc in documents
    )
