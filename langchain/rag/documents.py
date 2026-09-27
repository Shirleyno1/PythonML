from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from langchain.rag.embeddings import embeddings

# document = Document(
#     page_content="LangChain is a framework for building LLM applications.",
#     metadata={
#         "source": "example.txt"
#     }
# )

def load_pdf(path: str):
    loader = PyPDFLoader(path)

    return loader.load()

def split_documents(documents: list):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50,
    )
    return splitter.split_documents(documents)