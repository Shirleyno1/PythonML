import pytest

from settings.config import configure_langsmith
from observability.tracing import langsmith_run_config


def test_langsmith_tracing_is_disabled_by_default():
    environ = {}

    assert configure_langsmith(environ) is False
    assert environ["LANGSMITH_TRACING"] == "false"


def test_langsmith_tracing_accepts_legacy_tracking_setting():
    environ = {
        "LANGSMITH_TRACKING": "true",
        "LANGSMITH_API_KEY": "test-key",
    }

    assert configure_langsmith(environ) is True
    assert environ["LANGSMITH_TRACING"] == "true"
    assert environ["LANGSMITH_PROJECT"] == "ai-post-management"


def test_langsmith_tracing_requires_api_key_when_enabled():
    with pytest.raises(ValueError, match="LANGSMITH_API_KEY is required"):
        configure_langsmith({"LANGSMITH_TRACING": "true"})


def test_langsmith_run_config_adds_component_tags_and_metadata():
    config = langsmith_run_config(
        component="rag",
        metadata={"endpoint": "/langchain/rag"},
    )
    assert config["run_name"] == "langchain-rag"
    assert config["tags"] == ["pythonml", "langchain", "rag"]
    assert config["metadata"]["component"] == "rag"
    assert config["metadata"]["endpoint"] == "/langchain/rag"
