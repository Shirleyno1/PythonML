

class TextChunker:
    def __init__(
            self,
            chunk_size: int = 1000,
            chunk_overlap: int = 200
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def split_page(
            self,
            text: str,
    ) -> list[str]:

        if not text:
            return []

        chunks = []

        start = 0
        text_length = len(text)

        while start < text_length:

            end = start + self.chunk_size

            chunk = text[start:end].strip()

            if chunk:
                chunks.append(chunk)

            if end >= text_length:
                break

            start = end - self.chunk_overlap

        return chunks

    def split_documents(
            self,
            pages: list[dict],
    ):

        chunks = []

        for page in pages:

            page_number = page["page"]
            text = page["text"]
            source = page["source"]
            page_chunks = self.split_page(text)

            for chunk_index, chunk in enumerate(page_chunks):

                chunks.append(
                    {
                        "text": chunk,
                        "source": source,
                        "page": page_number,
                        "chunk_index": chunk_index,
                    }
                )

        return chunks



