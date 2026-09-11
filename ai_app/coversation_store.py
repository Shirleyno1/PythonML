

conversations = {}

def create_conversation(conversation_id: str):
    conversations[conversation_id] = []

def get_conversation(conversation_id: str):
    return conversations[conversation_id]

def add_message(
        conversation_id: str,
        role: str,
        content: str,
):
    if conversation_id not in conversations:
        conversations[conversation_id] = []

    conversations[conversation_id].append(
        {
            "role": role,
            "content": content,
        }
    )

