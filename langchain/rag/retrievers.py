from langchain_community.vectorstores import FAISS

from langchain.rag.documents import documents
from langchain.rag.embeddings import embeddings

vector_store = FAISS.from_documents(documents=documents, embedding=embeddings)

retriever = vector_store.as_retriever(
    search_kwargs={"k": 3}
)