from types import SimpleNamespace
from typing import Literal
from unittest.mock import Mock

import pytest

import chatbot.ai_service as ai_service
from chatbot.classifier import UserIntent


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
def test_intent(
    message: str,
    expected: Literal["search", "delete", "general"],
    monkeypatch: pytest.MonkeyPatch,
):
    parsed_intent = UserIntent(intent=expected, confidence=1.0)
    parse = Mock(return_value=SimpleNamespace(output_parsed=parsed_intent))
    client = SimpleNamespace(responses=SimpleNamespace(parse=parse))
    monkeypatch.setattr(ai_service, "_get_client", lambda: client)

    result = ai_service.classify_message(message)

    assert result == parsed_intent
    parse.assert_called_once()
