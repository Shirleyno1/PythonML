from langchain.rag.vector_stores import vector_store

retriever = vector_store.as_retriever(
    search_kwargs={"k": 3}
)