import asyncio
from functools import lru_cache

from fastapi import APIRouter, Depends

from chatbot.schemas import ChatRequest
from langchain.rag.chain import build_rag_chain
from langchain.rag.retrievers import RagRetriever
from observability.tracing import langsmith_run_config
from posts.db import User
from posts.users import current_active_user
from rag.service import get_rag_service

router = APIRouter()


@router.post("/rag")
async def rag(
        request: ChatRequest,
        user: User = Depends(current_active_user),
):
    service = await asyncio.to_thread(get_rag_service)
    return await service.answer(question=request.message)


@lru_cache(maxsize=1)
def get_langchain_pipeline():
    """Built once: building embeds the whole PDF, which is billed by OpenAI."""
    retriever = RagRetriever(
        file_path="./data/Resturaunt Q&A.pdf",
    ).get_retriever()
    return build_rag_chain(retriever)


@router.post("/langchain/rag")
async def langchain_rag(
        request: ChatRequest,
        user: User = Depends(current_active_user),
):
    pipeline = await asyncio.to_thread(get_langchain_pipeline)
    response = await pipeline.ainvoke(
        request.message,
        config=langsmith_run_config(
            "rag",
        ),
    )
    return {"answer": response.content}
