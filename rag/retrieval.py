


class Retriever:

    def __init__(self, vector_store):
        self.vector_store = vector_store

    def retrieve(
            self,
            query: str,
            top_k: int = 3
    ) -> list[dict]:

        results = self.vector_store.search(
            query=query,
            top_k=top_k
        )

        documents = results.get(
            "documents",
            [[]]
        )[0]

        metadatas = results.get(
            "metadatas",
            [[]]
        )[0]

        distances = results.get(
            "distances",
            [[]]
        )[0]

        retrieved = []

        for index, document in enumerate(documents):

            retrieved.append({
                "text": document,
                "metadata": metadatas[index],
                "distance": distances[index]
            })

        return retrieved








