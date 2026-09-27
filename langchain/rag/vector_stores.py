from langchain_community.vectorstores import FAISS

from langchain.rag.documents import load_pdf, split_documents
from langchain.rag.embeddings import embeddings

documents = load_pdf("./data/Resturaunt Q&A.pdf")
chunks = split_documents(documents)

vector_store = FAISS.from_documents(documents=chunks, embedding=embeddings)