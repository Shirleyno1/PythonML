from pathlib import Path

from langchain_community.vectorstores import FAISS

from langchain.rag.documents import load_pdf, split_documents
from langchain.rag.embeddings import embeddings

def create_vector_store(pdf_path: str | Path) -> FAISS:
    """ Create a FAISS vector store from a PDF document. """
    documents = load_pdf(pdf_path)
    chunks = split_documents(documents)
    vector_store = FAISS.from_documents(
        documents=chunks,
        embedding=embeddings,
    )
    return vector_store

