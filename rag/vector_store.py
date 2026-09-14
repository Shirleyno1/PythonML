from pathlib import Path

import chromadb


class VectorStore:

    def __init__(
            self,
            persist_directory: str = "./chroma_db",
            collection_name: str = "documents"
    ):

        Path(persist_directory).mkdir(parents=True, exist_ok=True)

        self.client = chromadb.PersistentClient(
            path=persist_directory
        )

        self.collection = (
            self.client.get_or_create_collection(
                name=collection_name
            )
        )

    def add_documents(
            self,
            chunks: list[dict],
    ) -> None:

        if not chunks:
            return

        documents = []
        ids = []
        metadatas = []

        for index, chunk in enumerate(chunks):

            documents.append(
                chunk["text"]
            )

            ids.append(
                self._create_id(chunk, index)
            )

            metadatas.append({
                "source": chunk["source"],
                "page": chunk["page"],
                "chunk_index": chunk["chunk_index"],
            })
        self.collection.upsert(
            documents=documents,
            ids=ids,
            metadatas=metadatas
        )

    def search(
            self,
            query: str,
            top_k: int = 5
    ):
        return self.collection.query(
            query_texts=[query],
            n_results=top_k
        )

    def count(self):
        return self.collection.count()

    @staticmethod
    def _create_id(
            chunk: dict,
            index: int
    ):
        source = Path(
            chunk["source"]
        ).stem

        return (
            f"{source}"
            f"page_{chunk['page']}"
            f"chunk_{chunk['chunk_index']}"
            f"{index}"
        )
