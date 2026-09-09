import os

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
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
            input=request.message
        )
        return ChatResponse(answer=response.output_text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error{str(e)}")



