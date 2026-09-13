from chatbot.ai_service import classify_message


@pytest.mark.parametrize(
    "message,expected",
    [
        (
            "Find my posts about Android",
            "search"
        ),
        (
            "Delete post 10",
            "delete"
        ),
        (
                "What is FastAPI?",
                "general"
        ),
    ]
)
def test_intent(message, expected):
    result = classify_message(message)

    assert result.intent == expected