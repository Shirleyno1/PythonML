from langchain_core.prompts import ChatPromptTemplate

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

def format_documents(documents):
    return "\n\n".join(
        doc.page_content
        for doc in documents
    )