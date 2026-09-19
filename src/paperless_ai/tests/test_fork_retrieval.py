import asyncio
from types import SimpleNamespace

import pytest
from llama_index.core.schema import TextNode

from paperless_ai.agent_chat import _build_search_tool
from paperless_ai.agent_chat import _ReferenceRegistry
from paperless_ai.chat import aiterate_sync_stream
from paperless_ai.indexing import load_or_build_index
from paperless_ai.indexing import read_store
from paperless_ai.search import semantic_search
from paperless_ai.vector_store import PaperlessSqliteVecVectorStore


@pytest.fixture
def fork_index(temp_llm_index_dir, mock_embed_model, mocker):
    config = SimpleNamespace()
    mocker.patch("paperless_ai.search.AIConfig", return_value=config)
    with PaperlessSqliteVecVectorStore(uri=str(temp_llm_index_dir)) as store:
        store.add(
            [
                TextNode(
                    id_=str(pk),
                    text=text,
                    metadata={"document_id": str(pk), "title": text},
                    embedding=[0.1] * 384,
                )
                for pk, text in [(1, "Visible invoice"), (2, "Private invoice")]
            ],
        )
    return config


def test_semantic_search_scopes_sqlite_retrieval(fork_index):
    results = semantic_search("invoice", document_ids=[1])
    assert [result.document_id for result in results] == [1]
    assert results[0].snippet == "Visible invoice"
    assert semantic_search("invoice", document_ids=[]) == []


def test_async_agent_tool_uses_sqlite_on_its_owning_thread(fork_index):
    registry = _ReferenceRegistry(
        [
            SimpleNamespace(pk=1, title="Visible invoice", filename="invoice.pdf"),
        ],
    )
    with read_store() as store:
        tool = _build_search_tool(load_or_build_index(fork_index, store), registry)
        result = asyncio.run(tool.acall(query="invoice"))
    assert "Visible invoice" in result.content
    assert "Private invoice" not in result.content
    assert not result.is_error
    assert registry.drain_pending()[0]["document_id"] == 1


def test_async_stream_closes_generator_on_disconnect():
    closed = []

    def source():
        try:
            yield "first"
            yield "second"
        finally:
            closed.append(True)

    async def disconnect():
        stream = aiterate_sync_stream(source())
        assert await anext(stream) == "first"
        await stream.aclose()

    asyncio.run(disconnect())
    assert closed == [True]
