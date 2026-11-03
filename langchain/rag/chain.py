from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable, RunnablePassthrough

from langchain.models import model

rag_prompt = ChatPromptTemplate.from_template(
    """
    Answer the question using only the context below.

    Context:
    {context}

    Question:
    {question}
    """
)

rag_chain = rag_prompt | model


def build_rag_chain(retriever: Runnable) -> Runnable:
    return (
            {
                "context": retriever,
                "question": RunnablePassthrough(),
            }
            | rag_chain
    )


def format_documents(documents):
    return "\n\n".join(
        doc.page_content
        for doc in documents
    )
