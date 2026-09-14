from rag.chunking import TextChunker
from rag.documents import DocumentLoader
from rag.generation import GenerationService
from rag.retrieval import Retriever
from rag.vector_store import VectorStore


class RAGService:

    def __init__(
            self,
            chroma_path: str = "./chroma_db"
    ):

        self.document_loader = DocumentLoader()

        self.chunker = TextChunker(
            chunk_size=1000,
            chunk_overlap=200
        )

        self.vector_store = VectorStore(
            persist_directory=chroma_path,
            collection_name="documents",
        )

        self.add_pdf_to_db()

        self.retriever =Retriever(
            vector_store=self.vector_store
        )

        self.generator = GenerationService()

    def add_pdf_to_db(self):
        pages = self.document_loader.load_pdf("data/Resturaunt Q&A.pdf")
        chunks = self.chunker.split_documents(pages)
        self.vector_store.add_documents(chunks)


    async def answer(
            self,
            question: str,
            top_k: int = 3
    ) -> dict:

        retrieved = self.retriever.retrieve(query=question, top_k=top_k)

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