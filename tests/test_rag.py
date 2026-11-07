import asyncio

import pytest
from chromadb import Documents, EmbeddingFunction, Embeddings
from fastapi import FastAPI
from fastapi.testclient import TestClient
from fastmcp import Client

from chatbot.routes import rag as rag_routes
from mcp_server import server as mcp_server
from mcp_server.schema_adapter import SchemaAdapter
from rag import service as rag_service
from rag.documents import DocumentLoader
from rag.retrieval import MAX_BEST_DISTANCE, Retriever
from rag.service import NO_RELEVANT_CONTEXT_ANSWER, RAGService
from rag.vector_store import VectorStore


class CountingEmbedding(EmbeddingFunction):
    """Embeds by letter counts, so tests need no model download. Records what it embeds."""

    def __init__(self):
        self.embedded = []

    def __call__(self, input: Documents) -> Embeddings:
        self.embedded.extend(input)
        return [
            [float(text.lower().count(letter)) for letter in "abcdefghij"]
            for text in input
        ]


def make_chunks(*texts, source="doc.pdf"):
    return [
        {"text": text, "source": source, "page": 1, "chunk_index": index}
        for index, text in enumerate(texts)
    ]


@pytest.fixture
def embedding():
    return CountingEmbedding()


@pytest.fixture
def store(tmp_path, embedding):
    return VectorStore(persist_directory=str(tmp_path), embedding_function=embedding)


def test_sync_indexes_new_documents(store):
    assert store.sync_documents(make_chunks("one", "two")) is True
    assert store.count() == 2


def test_sync_does_not_embed_an_unchanged_document_again(store, embedding):
    chunks = make_chunks("one", "two")
    store.sync_documents(chunks)
    embedding.embedded.clear()

    assert store.sync_documents(chunks) is False
    assert embedding.embedded == []


def test_unchanged_document_is_not_embedded_again_after_a_restart(tmp_path, embedding):
    chunks = make_chunks("one", "two")
    VectorStore(str(tmp_path), embedding_function=embedding).sync_documents(chunks)
    embedding.embedded.clear()

    reopened = VectorStore(str(tmp_path), embedding_function=embedding)

    assert reopened.sync_documents(chunks) is False
    assert embedding.embedded == []


def test_sync_drops_chunks_from_an_older_or_replaced_document(store):
    store.sync_documents(make_chunks("one", "two", "three", source="restaurant.pdf"))

    assert store.sync_documents(make_chunks("fern care", source="plants.pdf")) is True

    assert store.collection.get()["documents"] == ["fern care"]


def test_sync_replaces_an_index_written_before_digests_existed(store):
    store.add_documents(make_chunks("old"))

    assert store.sync_documents(make_chunks("new")) is True

    assert store.collection.get()["documents"] == ["new"]


class StubStore:
    def __init__(self, distances):
        self.distances = distances

    def search(self, query, top_k):
        count = len(self.distances)
        return {
            "documents": [[f"doc-{index}" for index in range(count)]],
            "metadatas": [[{"source": "doc.pdf", "page": index} for index in range(count)]],
            "distances": [self.distances],
        }


def test_unrelated_results_are_dropped():
    retriever = Retriever(StubStore([MAX_BEST_DISTANCE + 0.1, MAX_BEST_DISTANCE + 0.2]))

    assert retriever.retrieve("how do I water my fern?") == []


def test_a_good_best_match_keeps_the_further_results_too():
    retriever = Retriever(StubStore([MAX_BEST_DISTANCE - 0.1, MAX_BEST_DISTANCE + 0.1]))

    assert [item["text"] for item in retriever.retrieve("hours?")] == ["doc-0", "doc-1"]


def test_empty_index_finds_nothing():
    assert Retriever(StubStore([])).retrieve("anything") == []


def test_pdf_text_is_loaded_without_a_line_break_after_every_word():
    pages = DocumentLoader().load_pdf("data/Resturaunt Q&A.pdf")

    assert "What are your hours of operation?" in pages[0]["text"]
    assert "\n" not in pages[0]["text"]


def test_service_loads_the_pdf_when_created_and_searches_without_openai(
    tmp_path, embedding, monkeypatch
):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(rag_service, "GenerationService", pytest.fail)
    service = RAGService(chroma_path=str(tmp_path), embedding_function=embedding)
    service.retriever.max_best_distance = float("inf")
    embedded_while_loading = len(embedding.embedded)
    assert embedded_while_loading > 1

    results = service.search("hours", top_k=2)

    assert len(results) == 2
    assert set(results[0]) == {"text", "source", "page", "distance"}
    # Only the query was embedded: searching doesn't load the PDF again.
    assert len(embedding.embedded) == embedded_while_loading + 1


def test_answer_without_relevant_context_does_not_call_the_model(
    tmp_path, embedding, monkeypatch
):
    monkeypatch.setattr(rag_service, "GenerationService", pytest.fail)
    service = RAGService(chroma_path=str(tmp_path), embedding_function=embedding)
    service.retriever.max_best_distance = -1

    assert asyncio.run(service.answer("how do I water my fern?")) == {
        "answer": NO_RELEVANT_CONTEXT_ANSWER,
        "sources": [],
    }


def test_answer_passes_retrieved_context_to_the_model(tmp_path, embedding, monkeypatch):
    questions = []

    class FakeGenerator:
        async def generate(self, question, context):
            questions.append((question, context))
            return "We open at 11."

    monkeypatch.setattr(rag_service, "GenerationService", FakeGenerator)
    service = RAGService(chroma_path=str(tmp_path), embedding_function=embedding)
    service.retriever.max_best_distance = float("inf")

    result = asyncio.run(service.answer("hours?", top_k=1))

    assert result["answer"] == "We open at 11."
    assert result["sources"][0]["source"] == "data/Resturaunt Q&A.pdf"
    assert questions[0][0] == "hours?"
    assert questions[0][1]


def test_get_rag_service_creates_one_service_per_index(tmp_path, monkeypatch):
    created = []

    class FakeService:
        def __init__(self, chroma_path):
            created.append(chroma_path)

    monkeypatch.setattr(rag_service, "RAGService", FakeService)
    monkeypatch.setattr(rag_service, "_services", {})

    first = rag_service.get_rag_service("a")

    assert rag_service.get_rag_service("a") is first
    rag_service.get_rag_service("b")
    assert created == ["a", "b"]


def test_mcp_search_documents_tool_returns_passages(monkeypatch):
    class FakeService:
        def search(self, query, top_k):
            return [{"text": f"{query}:{top_k}", "source": "doc.pdf", "page": 1, "distance": 0.5}]

    paths = []

    def fake_get_service(path):
        paths.append(path)
        return FakeService()

    monkeypatch.setattr(mcp_server, "get_rag_service", fake_get_service)

    async def run():
        async with Client(mcp_server.mcp) as client:
            return await client.call_tool("search_documents", {"query": "hours", "top_k": 2})

    assert asyncio.run(run()).data[0]["text"] == "hours:2"
    assert paths == [mcp_server.RAG_CHROMA_PATH]


def test_mcp_search_documents_tool_is_offered_to_the_model_without_a_user_id():
    async def run():
        async with Client(mcp_server.mcp) as client:
            return await client.list_tools()

    tools = {
        tool["name"]: tool
        for tool in SchemaAdapter.mcp_tools_to_openai_tools(asyncio.run(run()))
    }

    tool = tools["search_documents"]
    assert "restaurant" in tool["description"]
    assert tool["parameters"]["required"] == ["query"]
    assert "user_id" not in tool["parameters"]["properties"]


@pytest.mark.parametrize("path", ["/rag", "/langchain/rag"])
def test_rag_endpoints_require_login(path, monkeypatch):
    monkeypatch.setattr(rag_routes, "get_rag_service", pytest.fail)
    monkeypatch.setattr(rag_routes, "get_langchain_pipeline", pytest.fail)
    app = FastAPI()
    app.include_router(rag_routes.router)

    response = TestClient(app).post(path, json={"message": "hours?"})

    assert response.status_code == 401


