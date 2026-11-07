from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv
from openai import OpenAI

from ai_prompts import catalog, get_prompt
from chatbot.ai_service import generate_structured_response
from chatbot.coversation_store import add_message, get_conversation
from chatbot.schemas import ChatRequest, ChatResponse
from observability.tracing import traced_openai

router = APIRouter()
load_dotenv()
client = traced_openai(OpenAI())


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    try:
        prompt = get_prompt(catalog.CHAT_ASSISTANT)
        response = client.responses.create(
            model=prompt.model,
            input=prompt.to_messages(message=request.message),
        )
        return ChatResponse(answer=response.output_text)
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Internal Server Error{error}",
        ) from error


def generate_response(conversation_id: str, message: str):
    try:
        add_message(conversation_id=conversation_id, role="user", content=message)
        history = get_conversation(conversation_id=conversation_id)
        prompt = get_prompt(catalog.CHAT_STREAM)
        stream = client.responses.create(
            model=prompt.model,
            input=[*prompt.to_messages(), *history],
            stream=True,
        )

        full_response = ""
        for event in stream:
            if event.type == "response.output_text.delta":
                full_response += event.delta
                yield event.delta

        add_message(
            conversation_id=conversation_id,
            role="assistant",
            content=full_response,
        )
    except Exception as error:
        yield f"\n[Error generating response: {error}]"


@router.post("/chat/stream")
def chat_stream(request: ChatRequest):
    return StreamingResponse(
        generate_response(str(request.conversation_id), request.message),
        media_type="text/plain",
    )


@router.post("/chat/structured")
def chat_structured(request: ChatRequest):
    return generate_structured_response(request.message)
