from langchain.rag.vector_stores import create_vector_store


class RagRetriever:
    def __init__(self, file_path: str):
        self.file_path = file_path

    def get_retriever(self):
        return create_vector_store(self.file_path).as_retriever( search_kwargs={"k": 3})