# Chroma always returns its nearest chunks, however unrelated. With the default
# embedding model and rag/service.py's chunk size, the sample PDF's answerable
# questions had a best distance of at most 1.59, and off-topic ones from 1.67.
# Measure again when changing the document, chunk size or embedding model.
MAX_BEST_DISTANCE = 1.63


class Retriever:

    def __init__(self, vector_store, max_best_distance: float = MAX_BEST_DISTANCE):
        self.vector_store = vector_store
        self.max_best_distance = max_best_distance

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

        # Judged on the best match alone: the chunk holding the answer isn't always
        # first, and can be further away than the cutoff when it's second or third.
        if not distances or min(distances) > self.max_best_distance:
            return []

        retrieved = []

        for index, document in enumerate(documents):

            retrieved.append({
                "text": document,
                "metadata": metadatas[index],
                "distance": distances[index]
            })

        return retrieved
