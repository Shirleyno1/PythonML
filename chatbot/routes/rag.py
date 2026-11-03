from fastapi import APIRouter, Depends

from chatbot.schemas import ChatRequest
from langchain.rag.chain import build_rag_chain
from langchain.rag.retrievers import RagRetriever
from observability.tracing import langsmith_run_config
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
    pipeline = build_rag_chain(retriever)
    response = await pipeline.ainvoke(
        request.message,
        config=langsmith_run_config(
            "rag",
        ),
    )
    return {"answer": response.content}
