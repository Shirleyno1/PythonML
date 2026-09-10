import requests
import streamlit as st

st.title("My AI Chatbot")

message = st.chat_input("Ask me something...")

if message:

    with st.chat_message("user"):
        st.write(message)

    response = requests.post(
        "http://0.0.0.0:8080/chat/stream",
        json={
            "message": message
        },
        stream=True
    )

    if response.status_code == 200:

        full_response = ""

        with st.chat_message("assistant"):
            placeholder = st.empty()
            for chunk in response.iter_content(
                chunk_size=None,
                decode_unicode=True,
            ):
                if chunk:
                    full_response += chunk
                    placeholder.write(full_response)

    else:
        st.error("Something went wrong")