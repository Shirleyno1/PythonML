import uuid

import requests

import streamlit as st


st.title("AI Intent classifier")

message = st.chat_input("Ask something...")

if message:
    with st.chat_message("user"):
        st.write(message)

    try:

        if "conversation_id" not in st.session_state:
            st.session_state.conversation_id = str(uuid.uuid4)

        response = requests.post(
            "http://0.0.0.0:8080/classify",
            json={
                "message": message,
                "conversation_id": st.session_state.conversation_id
            },
            timeout=60
        )

        response.raise_for_status()

        data = response.json()

        with st.chat_message("assistant"):
            st.write(f"**Intent:** {data['intent']}")

            st.write(f"**Query:** {data['query']}")

            st.write(f"**Confidence:** {data['confidence']:.2f}")

            with st.expander("Raw structured response"):
                st.json(data)

    except requests.RequestException as e:
        st.error(f"API Error: {e}")