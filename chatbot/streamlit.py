import uuid

import requests
import streamlit as st

st.title("My AI Chatbot")

message = st.chat_input("Ask me something...")

if message:

    if "conversation_id" not in st.session_state:
        st.session_state.conversation_id = str(uuid.uuid4)

    with st.chat_message("user"):
        st.write(message)

    try:
        response = requests.post(
            "http://0.0.0.0:8080/chat/structured",
            json={
                "message": message,
                "conversation_id": st.session_state.conversation_id
            },
            timeout=60
            # stream=True
        )

        response.raise_for_status()

    # if response.status_code == 200:

        data = response.json()
        with st.chat_message("assistant"):

            st.subheader(data["title"])

            st.write(data["summary"])

            st.write("### Key points")

            for point in data["key_points"]:
                st.write(point)

            with st.expander("Raw response"):
                st.json(data)

        # with st.chat_message("assistant"):
        #     full_response = ""
        #
        #     placeholder = st.empty()
        #
        #     with st.spinner("AI is thinking..."):
        #         for chunk in response.iter_content(
        #             chunk_size=None,
        #             decode_unicode=True,
        #         ):
        #             if chunk:
        #                 full_response += chunk
        #                 placeholder.write(full_response)

    except requests.RequestException as e:
        st.error(f"Something went wrong {e}")