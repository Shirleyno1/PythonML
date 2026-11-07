import hashlib
import json
from pathlib import Path

import chromadb


class VectorStore:

    def __init__(
            self,
            persist_directory: str = "./chroma_db",
            collection_name: str = "documents",
            embedding_function=None,
    ):

        Path(persist_directory).mkdir(parents=True, exist_ok=True)

        self.client = chromadb.PersistentClient(
            path=persist_directory
        )

        # Left out unless given, so Chroma uses its default embedding model.
        options = (
            {"embedding_function": embedding_function}
            if embedding_function is not None
            else {}
        )
        self.collection = (
            self.client.get_or_create_collection(
                name=collection_name,
                **options,
            )
        )

    def sync_documents(
            self,
            chunks: list[dict],
    ) -> bool:
        """
        Make the index hold exactly these chunks, and return whether it had to change.
        An unchanged index is left alone, so restarting doesn't embed everything again.
        """

        digest = hashlib.sha256(
            json.dumps(chunks, sort_keys=True).encode()
        ).hexdigest()

        existing = self.collection.get(include=["metadatas"])
        is_current = len(existing["ids"]) == len(chunks) and all(
            metadata.get("digest") == digest
            for metadata in existing["metadatas"]
        )
        if is_current:
            return False

        if existing["ids"]:
            self.collection.delete(ids=existing["ids"])
        self.add_documents(chunks, digest=digest)
        return True

    def add_documents(
            self,
            chunks: list[dict],
            digest: str = "",
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
                "digest": digest,
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
