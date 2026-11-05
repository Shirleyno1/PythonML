import asyncio
import logging
import time

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from chatbot.ai_service import classify_message
from chatbot.classifier import UserIntent
from observability.tracing import (
    ai_traceable,
    trace_ai_request_input,
    trace_ai_result,
)
from chatbot.schemas import ChatRequest
from posts.app import upload_file
from posts.db import User, get_async_session
from posts.users import current_active_user
from posts.repository import PostRepository
from posts.service import PostService

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/ai")
@ai_traceable(
    name="AI Post Management Request",
    component="ai-request",
    run_type="chain",
    process_inputs=trace_ai_request_input,
    process_outputs=trace_ai_result,
)
async def ai_endpoint(
    request: ChatRequest,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user),
):
    intent = await classify_with_retry(request.message)
    if intent is None:
        return {
            "status": "error",
            "message": {"The AI service is temporary unavailable."},
        }

    if intent.confidence < 0.7:
        return {
            "intent": "general",
            "message": "I'm not sure what you want me to do",
        }

    return await decide_by_user_intent(intent, session=session, user=user)


async def classify_with_retry(
    message: str,
    max_retries: int = 3,
) -> UserIntent | None:
    for attempt in range(max_retries):
        try:
            started_at = time.perf_counter()
            result = classify_message(message)
            logger.info(
                "AI classification complete",
                extra={
                    "intent": result.intent,
                    "confidence": result.confidence,
                    "latency": time.perf_counter() - started_at,
                },
            )
            return result
        except Exception:
            if attempt == max_retries - 1:
                logger.exception("AI classification failed after retries")
                raise
            await asyncio.sleep(2**attempt)
    return None


async def decide_by_user_intent(
    intent: UserIntent,
    session: AsyncSession,
    user: User,
):
    handlers = {
        "search": user_search,
        "create": user_create,
        "delete": user_delete,
    }
    handler = handlers.get(intent.intent)
    if handler is None:
        return await general()
    if intent.intent == "create":
        return await handler(intent)
    return await handler(intent=intent, session=session, user=user)


async def user_search(
    intent: UserIntent,
    session: AsyncSession,
    user: User,
):
    posts_result = await PostService(PostRepository(session)).get_my_posts(user.id)
    return {
        "intent": "search",
        "query": intent.query,
        "results": [
            {
                "id": post["id"],
                "title": post["caption"],
                "content": post.get("description")
                or ", ".join(
                    image["file_name"] for image in post.get("images", [])
                ),
            }
            for post in posts_result["posts"]
        ],
    }


async def user_create(intent: UserIntent):
    post = await upload_file()
    return {
        "intent": "create",
        "status": "success",
        "post": {
            "id": post["id"],
            "title": post["caption"],
            "content": post.get("description")
            or ", ".join(image["file_name"] for image in post.get("images", [])),
        },
    }


async def user_delete(
    intent: UserIntent,
    session: AsyncSession,
    user: User,
):
    if not intent.query:
        return {
            "status": "missing_information",
            "message": "Which post would you like to delete?",
        }

    post = await PostService(PostRepository(session)).get_own_post_summary(
        intent.query,
        user.id,
    )
    if post is None:
        return {
            "intent": "delete",
            "status": "not_found",
            "message": "I couldn't find that post among your posts.",
        }

    # Nothing is deleted here: the client asks the user, then calls this endpoint.
    return {
        "intent": "delete",
        "status": "confirmation_required",
        "message": "Please confirm you want to delete this post.",
        "post": post,
        "confirm": {"method": "DELETE", "path": f"/posts/{post['id']}"},
    }


async def general():
    return None
