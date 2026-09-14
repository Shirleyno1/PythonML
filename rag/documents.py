from pathlib import Path

from pypdf import PdfReader



class DocumentLoader:

    def load_pdf(self, file_path: str) -> list[dict]:
        """
        Load a PDF and return one dictionary per page.

        Each dictionary contains:
        - page number
        - page text
        """

        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        if path.suffix.lower() != ".pdf":
            raise ValueError(f"Expected a PDF file, got: {path.suffix}")

        reader = PdfReader(str(path))

        pages = []

        for page_number, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""

            text = text.strip()

            if not text:
                continue

            pages.append(
                {
                    "page": page_number,
                    "text": text,
                    "source": file_path,
                }
            )

        return pages
