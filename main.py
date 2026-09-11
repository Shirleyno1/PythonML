import uvicorn

#
# if __name__ == "__main__":
#     uvicorn.run("app.app:app", reload=True, port=8000, host="0.0.0.0")

if __name__ == "__main__":
    uvicorn.run("chatbot.main:app", reload=True, port=8080, host="0.0.0.0")
