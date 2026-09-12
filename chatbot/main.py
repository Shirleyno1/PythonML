import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import StreamingResponse
from openai import OpenAI
from sqlalchemy.ext.asyncio import AsyncSession

from chatbot.ai_service import generate_structured_response, classify_message
from chatbot.coversation_store import add_message, get_conversation
from chatbot.schemas import ChatRequest, ChatResponse
from chatbot.user_intent import UserIntent
from posts.app import get_posts, upload_file, delete_post, posts_router
from posts.db import get_async_session, User, create_db_tables
from posts.schema import UserRead, UserUpdate, UserCreate
from posts.users import current_active_user, fastapi_users, auth_backend


load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_db_tables()
    yield
app = FastAPI(lifespan=lifespan)
app.include_router(posts_router)

app.include_router(fastapi_users.get_auth_router(auth_backend), prefix="/auth/jwt", tags=["auth"])
app.include_router(fastapi_users.get_register_router(UserRead, UserCreate), prefix="/auth", tags=["auth"])
app.include_router(fastapi_users.get_reset_password_router(), prefix="/auth", tags=["auth"])
app.include_router(fastapi_users.get_verify_router(UserRead), prefix="/auth", tags=["auth"])
app.include_router(fastapi_users.get_users_router(UserRead, UserUpdate), prefix="/users", tags=["users"])

client = OpenAI(api_key=api_key)

@app.post("/chat", response_model = ChatResponse)
def chat(request: ChatRequest):
    try:
        response = client.responses.create(
            model="gpt-5-mini",
            input=[
                {
                    "role": "system",
                    "content": "You are a helpful AI assistang. Answer clearly and concisely"
                },
                {
                    "role": "user",
                    "content": request.message
                }
            ]
        )
        return ChatResponse(answer=response.output_text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error{str(e)}")

def generate_response(conversation_id: str, message: str):
    try:
        add_message(
            conversation_id=conversation_id,
            role="user", content=message
        )

        history = get_conversation(conversation_id=conversation_id)
        stream = client.responses.create(
            model="gpt-5-mini",
            input=history,
            stream=True
        )

        full_response = ""

        for event in stream:
            if event.type == "response.output_text.delta":
                delta = event.delta
                full_response += delta
                yield delta

        add_message(
            conversation_id=conversation_id,
            role="assistant",
            content=full_response
        )
    except Exception as e:
        yield (f"\n[Error generating response: {e}]")


@app.post("/chat/stream")
def chat_stream(request: ChatRequest):
    return StreamingResponse(
        generate_response(conversation_id=request.conversation_id, message=request.message),
        media_type="text/plain"
    )

@app.post("/chat/structured")
def chat_structured(request: ChatRequest):
    result = generate_structured_response(request.message)

    return result

@app.post("/ai")
async def ai_endpoint(
    request: ChatRequest,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user),
):
    intent = classify_message(request.message)

    if intent.confidence < 0.7:
        return {
            "intent": "general",
            "message": "I'm not sure what you want me to do"
        }


    return await decide_by_user_intent(intent, session=session, user=user)


async def decide_by_user_intent(
        intent: UserIntent,
        session: AsyncSession,
        user: User,
):
    if intent.intent == "search":
        return await user_search(intent=intent, session=session, user=user)
    if intent.intent == "create":
        return await user_create(intent)
    if intent.intent == "delete":
        return await user_delete(intent=intent, session=session, user=user)
    else:
        return await general()


async def user_search(
        intent: UserIntent,
        session: AsyncSession,
        user: User,
):

    posts = await get_posts(session=session, user=user)
    print(posts)

    return {
        "intent": "search",
        "query": intent.query,
        "results": [
            {
                "id": post["id"],
                "title": post["caption"],
                "content": post["file_name"]
            }
            for post in posts["posts"]
        ]
    }

async def user_create(intent):
    post = await upload_file()

    return {
        "intent": "create",
        "status": "success",
        "post": {
            "id": post.id,
            "title": post.caption,
            "content": post.file_name
        }
    }


async def user_delete(
        intent: UserIntent,
        session: AsyncSession,
        user: User,
):

    if not intent.query:
         return {
            "status": "missing_information",
            "message": "Which post would you like to delete?"
         }

    result = await delete_post(
        post_id=intent.query,
        session=session,
        user=user
    )

    return {
        "intent": "create",
        "status": result,
    }

async def general():
    pass


