from fastapi import APIRouter, Depends

from chatbot.schemas import ChatRequest
from langchain.rag.chain import rag_chain
from langchain.rag.retrievers import RagRetriever
from posts.db import User
from posts.users import current_active_user
from rag.service import RAGService

router = APIRouter()


@router.post("/rag")
async def rag(
    request: ChatRequest,
    user: User = Depends(current_active_user),
):
    return await RAGService().answer(question=request.message)


@router.post("/langchain/rag")
async def langchain_rag(request: ChatRequest):
    retriever = RagRetriever(
        file_path="./data/Resturaunt Q&A.pdf",
    ).get_retriever()
    documents = await retriever.ainvoke(request.message)
    response = await rag_chain.ainvoke(
        {"question": request.message, "context": documents}
    )
    return {"answer": response.content}
