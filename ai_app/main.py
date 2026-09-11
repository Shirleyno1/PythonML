import os

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from openai import OpenAI

from ai_app.coversation_store import add_message, get_conversation
from ai_app.schemas import ChatRequest, ChatResponse

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

app=FastAPI()

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
