import asyncio
import threading
from functools import cached_property

from rag.chunking import TextChunker
from rag.documents import DocumentLoader
from rag.generation import GenerationService
from rag.retrieval import Retriever
from rag.vector_store import VectorStore

DEFAULT_CHROMA_PATH = "./chroma_db"
DOCUMENT_PATH = "data/Resturaunt Q&A.pdf"
NO_RELEVANT_CONTEXT_ANSWER = "I don't have enough information to answer that."


class RAGService:

    def __init__(
            self,
            chroma_path: str = DEFAULT_CHROMA_PATH,
            document_path: str = DOCUMENT_PATH,
            embedding_function=None,
    ):

        self.document_path = document_path

        self.document_loader = DocumentLoader()

        self.chunker = TextChunker(
            chunk_size=500,
            chunk_overlap=100
        )

        self.vector_store = VectorStore(
            persist_directory=chroma_path,
            collection_name="documents",
            embedding_function=embedding_function,
        )

        self.add_pdf_to_db()

        self.retriever = Retriever(
            vector_store=self.vector_store
        )

    @cached_property
    def generator(self) -> GenerationService:
        # Created on first use: searching needs no OpenAI key.
        return GenerationService()

    def add_pdf_to_db(self):
        pages = self.document_loader.load_pdf(self.document_path)
        chunks = self.chunker.split_documents(pages)
        self.vector_store.sync_documents(chunks)

    def search(
            self,
            query: str,
            top_k: int = 3
    ) -> list[dict]:
        """Passages relevant to the query, best first. Empty if nothing is relevant."""

        return [
            {
                "text": item["text"],
                "source": item["metadata"]["source"],
                "page": item["metadata"]["page"],
                "distance": item["distance"],
            }
            for item in self.retriever.retrieve(query=query, top_k=top_k)
        ]

    async def answer(
            self,
            question: str,
            top_k: int = 3
    ) -> dict:

        # Embedding and searching are blocking, so they stay off the event loop.
        retrieved = await asyncio.to_thread(
            self.retriever.retrieve,
            query=question,
            top_k=top_k,
        )

        if not retrieved:
            return {"answer": NO_RELEVANT_CONTEXT_ANSWER, "sources": []}

        context_parts = [
            item["text"]
            for item in retrieved
        ]

        context = "\n\n---\n\n".join(context_parts)

        answer = await self.generator.generate(
            context=context,
            question=question,
        )

        return {
            "answer": answer,
            "sources": [
                item["metadata"]
                for item in retrieved
            ]
        }


_services: dict[str, RAGService] = {}
_services_lock = threading.Lock()


def get_rag_service(chroma_path: str = DEFAULT_CHROMA_PATH) -> RAGService:
    """One service per index, so the PDF is loaded once rather than on every request."""
    with _services_lock:
        if chroma_path not in _services:
            _services[chroma_path] = RAGService(chroma_path=chroma_path)
        return _services[chroma_path]
