from chromadb.utils import embedding_functions
from dotenv import load_dotenv
from openai import OpenAI


class EmbeddingService:
    def __init__(self):
        self.embedding_function = (
            embedding_functions.DefaultEmbeddingFunction()
        )

    def embed_documents(
            self,
            documents: list[str]
    ):
        """
        Convert documents to embeddings.
        """

        return self.embedding_function(documents)

    def embed_query(
            self,
            query: str,
    ):
        """
        Convert query to embeddings.
        """

        result = self.embedding_function([query])

        return result[0]