from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from langchain.rag.embeddings import embeddings

# document = Document(
#     page_content="LangChain is a framework for building LLM applications.",
#     metadata={
#         "source": "example.txt"
#     }
# )

loader = PyPDFLoader("./data/Resturaunt Q&A.pdf")

documents = loader.load()

splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=50,
)

for document in documents:
    chunks = splitter.split_documents([document])

    # for chunk in chunks:
        # print(chunk.page_content)


