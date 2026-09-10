import os

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from openai import OpenAI
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

def generate_response(message: str):
    stream = client.responses.create(
        model="gpt-5-mini",
        input=message,
        stream=True
    )

    for event in stream:
        if event.type == "response.output_text.delta":
            yield event.delta

@app.post("/chat/stream")
def chat_stream(request: ChatRequest):
    return StreamingResponse(
        generate_response(request.message),
        media_type="text/plain"
    )
