import json
from types import SimpleNamespace
from unittest.mock import MagicMock
from unittest.mock import patch

from llama_index.core.agent.workflow import AgentStream
from llama_index.core.agent.workflow import ToolCall
from llama_index.core.agent.workflow import ToolCallResult
from llama_index.core.tools import ToolOutput

from paperless_ai.agent_chat import AGENT_MAX_REFERENCES
from paperless_ai.agent_chat import CHAT_INDEX_NOT_READY_MESSAGE
from paperless_ai.agent_chat import _ReferenceRegistry
from paperless_ai.agent_chat import stream_agentic_chat
from paperless_ai.chat import CHAT_ERROR_MESSAGE
from paperless_ai.chat import CHAT_NO_CONTENT_MESSAGE
from paperless_ai.chat import build_chat_history


def _doc(pk: int, title: str = "") -> SimpleNamespace:
    return SimpleNamespace(pk=pk, title=title or f"Doc {pk}", filename=f"{pk}.pdf")


def _events(chunks: list[str]) -> list[dict]:
    """Parse the yielded NDJSON lines into event dicts."""
    return [json.loads(chunk) for chunk in chunks]


class TestReferenceRegistry:
    def test_assigns_sequential_numbers_in_order_seen(self):
        registry = _ReferenceRegistry([_doc(7), _doc(3), _doc(5)])
        assert registry.register("3", "Three", "s") == 1
        assert registry.register("7", "Seven", "s") == 2
        # Re-registering returns the same number and does not re-queue a citation.
        assert registry.register("3", "ignored", "s") == 1

    def test_ignores_documents_outside_allowed_set(self):
        registry = _ReferenceRegistry([_doc(1)])
        assert registry.register("999", "Nope", "s") is None
        assert registry.drain_pending() == []

    def test_pending_citations_ordered_and_drained_once(self):
        registry = _ReferenceRegistry([_doc(1, "One"), _doc(2, "Two")])
        registry.register("2", "Two", "snip2")
        registry.register("1", "One", "snip1")
        assert registry.drain_pending() == [
            {"marker": 1, "document_id": 2, "title": "Two", "snippet": "snip2"},
            {"marker": 2, "document_id": 1, "title": "One", "snippet": "snip1"},
        ]
        # Draining is idempotent — already-emitted citations are not repeated.
        assert registry.drain_pending() == []

    def test_caps_number_of_references(self):
        docs = [_doc(i) for i in range(1, AGENT_MAX_REFERENCES + 5)]
        registry = _ReferenceRegistry(docs)
        for doc in docs:
            registry.register(str(doc.pk), doc.title, "s")
        assert len(registry.drain_pending()) == AGENT_MAX_REFERENCES


class _FakeHandler:
    def __init__(self, events):
        self._events = events

    async def stream_events(self):
        for event in self._events:
            yield event

    def __await__(self):
        async def _noop():
            return None

        return _noop().__await__()


def _agent_stream(delta: str) -> AgentStream:
    return AgentStream(
        delta=delta,
        response=delta,
        current_agent_name="agent",
        tool_calls=[],
        raw=None,
    )


class TestStreamAgenticChat:
    def test_no_documents_yields_no_content(self):
        events = _events(list(stream_agentic_chat("question", [])))
        assert events == [
            {"type": "token", "text": CHAT_NO_CONTENT_MESSAGE},
            {"type": "done"},
        ]

    def test_streams_tokens_then_citation_and_done(self):
        documents = [_doc(1, "Invoice"), _doc(2, "Receipt")]

        def fake_build_tool(index, registry, filters=None):
            # Simulate the agent's retrieval surfacing document 2.
            registry.register("2", "Receipt", "the matched chunk")
            return MagicMock()

        fake_agent = MagicMock()
        fake_agent.run.return_value = _FakeHandler(
            [_agent_stream("Hello "), _agent_stream("world [1]")],
        )

        with (
            patch("paperless_ai.client.AIClient"),
            patch("paperless_ai.indexing.llm_index_exists", return_value=True),
            patch("paperless_ai.indexing.load_or_build_index"),
            patch("paperless_ai.indexing.read_store"),
            patch(
                "paperless_ai.agent_chat._build_search_tool",
                side_effect=fake_build_tool,
            ),
            patch(
                "llama_index.core.agent.workflow.FunctionAgent",
                return_value=fake_agent,
            ),
        ):
            events = _events(list(stream_agentic_chat("question", documents)))

        text = "".join(e["text"] for e in events if e["type"] == "token")
        assert text == "Hello world [1]"

        citations = [e for e in events if e["type"] == "citation"]
        assert citations == [
            {
                "type": "citation",
                "marker": 1,
                "document_id": 2,
                "title": "Receipt",
                "snippet": "the matched chunk",
            },
        ]
        assert events[-1] == {"type": "done"}

    def test_forwards_chat_history_to_agent(self):
        documents = [_doc(1, "Invoice")]
        fake_agent = MagicMock()
        fake_agent.run.return_value = _FakeHandler([_agent_stream("hi")])
        history = build_chat_history(
            [
                {"role": "user", "content": "previous question"},
                {"role": "assistant", "content": "previous answer"},
            ],
        )

        with (
            patch("paperless_ai.client.AIClient"),
            patch("paperless_ai.indexing.llm_index_exists", return_value=True),
            patch("paperless_ai.indexing.load_or_build_index"),
            patch("paperless_ai.indexing.read_store"),
            patch(
                "paperless_ai.agent_chat._build_search_tool",
                return_value=MagicMock(),
            ),
            patch(
                "llama_index.core.agent.workflow.FunctionAgent",
                return_value=fake_agent,
            ),
        ):
            list(
                stream_agentic_chat(
                    "question",
                    documents,
                    chat_history=history,
                ),
            )

        fake_agent.run.assert_called_once()
        assert fake_agent.run.call_args.args[0] == "question"
        assert fake_agent.run.call_args.kwargs["chat_history"] == history

    def test_empty_history_passes_none_to_agent(self):
        documents = [_doc(1, "Invoice")]
        fake_agent = MagicMock()
        fake_agent.run.return_value = _FakeHandler([_agent_stream("hi")])

        with (
            patch("paperless_ai.client.AIClient"),
            patch("paperless_ai.indexing.llm_index_exists", return_value=True),
            patch("paperless_ai.indexing.load_or_build_index"),
            patch("paperless_ai.indexing.read_store"),
            patch(
                "paperless_ai.agent_chat._build_search_tool",
                return_value=MagicMock(),
            ),
            patch(
                "llama_index.core.agent.workflow.FunctionAgent",
                return_value=fake_agent,
            ),
        ):
            list(stream_agentic_chat("question", documents))

        assert fake_agent.run.call_args.kwargs["chat_history"] is None

    def test_emits_tool_call_and_result_events(self):
        documents = [_doc(5, "Lease")]

        def fake_build_tool(index, registry, filters=None):
            registry.register("5", "Lease", "rent is due monthly")
            registry.record_call(
                "rent",
                1,
                [{"id": 5, "title": "Lease", "marker": 1}],
            )
            return MagicMock()

        fake_agent = MagicMock()
        fake_agent.run.return_value = _FakeHandler(
            [
                ToolCall(
                    tool_name="search_documents",
                    tool_kwargs={"query": "rent"},
                    tool_id="t1",
                ),
                ToolCallResult(
                    tool_name="search_documents",
                    tool_kwargs={"query": "rent"},
                    tool_id="t1",
                    tool_output=ToolOutput(
                        content="[1] ...",
                        tool_name="search_documents",
                        raw_input={"query": "rent"},
                        raw_output="[1] ...",
                    ),
                    return_direct=False,
                ),
                _agent_stream("Your rent is due monthly [1]"),
            ],
        )

        with (
            patch("paperless_ai.client.AIClient"),
            patch("paperless_ai.indexing.llm_index_exists", return_value=True),
            patch("paperless_ai.indexing.load_or_build_index"),
            patch("paperless_ai.indexing.read_store"),
            patch(
                "paperless_ai.agent_chat._build_search_tool",
                side_effect=fake_build_tool,
            ),
            patch(
                "llama_index.core.agent.workflow.FunctionAgent",
                return_value=fake_agent,
            ),
        ):
            events = _events(list(stream_agentic_chat("question", documents)))

        assert [e["type"] for e in events] == [
            "tool_call",
            "tool_result",
            "citation",
            "token",
            "done",
        ]
        assert events[0] == {
            "type": "tool_call",
            "id": "t1",
            "name": "search_documents",
            "query": "rent",
        }
        assert events[1]["count"] == 1
        assert events[1]["documents"] == [{"id": 5, "title": "Lease", "marker": 1}]
        assert events[2]["document_id"] == 5

    def test_missing_index_yields_index_not_ready_and_queues_build(self):
        documents = [_doc(1)]
        with (
            patch("paperless_ai.client.AIClient"),
            patch("paperless_ai.indexing.llm_index_exists", return_value=False),
            patch(
                "paperless_ai.indexing.queue_llm_index_update_if_needed",
            ) as mock_queue,
        ):
            events = _events(list(stream_agentic_chat("question", documents)))

        assert events == [
            {"type": "token", "text": CHAT_INDEX_NOT_READY_MESSAGE},
            {"type": "done"},
        ]
        mock_queue.assert_called_once()

    def test_no_text_produced_yields_no_content(self):
        documents = [_doc(1)]
        fake_agent = MagicMock()
        fake_agent.run.return_value = _FakeHandler([])

        with (
            patch("paperless_ai.client.AIClient"),
            patch("paperless_ai.indexing.llm_index_exists", return_value=True),
            patch("paperless_ai.indexing.load_or_build_index"),
            patch("paperless_ai.indexing.read_store"),
            patch(
                "paperless_ai.agent_chat._build_search_tool",
                return_value=MagicMock(),
            ),
            patch(
                "llama_index.core.agent.workflow.FunctionAgent",
                return_value=fake_agent,
            ),
        ):
            events = _events(list(stream_agentic_chat("question", documents)))

        assert events == [
            {"type": "token", "text": CHAT_NO_CONTENT_MESSAGE},
            {"type": "done"},
        ]

    def test_unexpected_error_yields_error_event(self):
        documents = [_doc(1)]
        fake_agent = MagicMock()
        fake_agent.run.side_effect = RuntimeError("boom")

        with (
            patch("paperless_ai.client.AIClient"),
            patch("paperless_ai.indexing.llm_index_exists", return_value=True),
            patch("paperless_ai.indexing.load_or_build_index"),
            patch("paperless_ai.indexing.read_store"),
            patch(
                "paperless_ai.agent_chat._build_search_tool",
                return_value=MagicMock(),
            ),
            patch(
                "llama_index.core.agent.workflow.FunctionAgent",
                return_value=fake_agent,
            ),
        ):
            events = _events(list(stream_agentic_chat("question", documents)))

        assert events == [{"type": "error", "message": CHAT_ERROR_MESSAGE}]


class TestAgentTools:
    def search_tool(self, documents, nodes=(), error=None):
        from paperless_ai.agent_chat import _build_search_tool

        registry = _ReferenceRegistry(documents)
        with patch("llama_index.core.retrievers.VectorIndexRetriever") as retriever:
            retriever.return_value.retrieve.return_value = list(nodes)
            retriever.return_value.retrieve.side_effect = error
            tool = _build_search_tool(MagicMock(), registry)
        return tool, registry, retriever.return_value.retrieve

    def test_lexical_fallback_finds_exact_identifier_when_vectors_fail(self):
        doc = _doc(1, "Invoice")
        doc.content = "The invoice INV-2026-198 totals EUR 42."
        tool, registry, _retrieve = self.search_tool(
            [doc],
            error=RuntimeError("offline"),
        )
        result = tool.call(query="INV-2026-198").content
        assert "EUR 42" in result
        assert registry.calls["INV-2026-198"]["count"] == 1
        assert registry.drain_pending()[0]["document_id"] == 1

    def test_search_deduplicates_queries_and_enforces_budget(self):
        from paperless_ai.agent_chat import AGENT_MAX_SEARCHES

        tool, _registry, retrieve = self.search_tool([_doc(1)])
        tool.call(query="first")
        tool.call(query=" FIRST ")
        assert retrieve.call_count == 1
        for i in range(AGENT_MAX_SEARCHES - 1):
            tool.call(query=f"query {i}")
        assert "budget exhausted" in tool.call(query="one too many").content
        assert retrieve.call_count == AGENT_MAX_SEARCHES

    def test_filters_unauthorized_vector_results_and_counts_visible_documents(self):
        from llama_index.core.schema import NodeWithScore
        from llama_index.core.schema import TextNode

        nodes = [
            NodeWithScore(
                node=TextNode(text="private", metadata={"document_id": "99"}),
            ),
            NodeWithScore(node=TextNode(text="visible", metadata={"document_id": "1"})),
            NodeWithScore(
                node=TextNode(text="another chunk", metadata={"document_id": "1"}),
            ),
        ]
        tool, registry, _ = self.search_tool([_doc(1)], nodes=nodes)
        result = tool.call(query="question").content
        assert "private" not in result
        assert "visible" in result
        assert registry.calls["question"]["count"] == 1

    def test_read_requires_discovery_and_pages_with_stable_citations(self):
        from paperless_ai.agent_chat import AGENT_READ_LENGTH
        from paperless_ai.agent_chat import _build_read_tool

        doc = _doc(1)
        doc.content = "a" * AGENT_READ_LENGTH + "last page"
        registry = _ReferenceRegistry([doc])
        tool = _build_read_tool(registry)
        assert "Search for this document first" in tool.call(document_id=1).content
        registry.register("1", doc.title, "a")
        first = tool.call(document_id=1).content
        assert f"Next offset: {AGENT_READ_LENGTH}" in first
        assert "last page" not in first
        last = tool.call(document_id=1, offset=AGENT_READ_LENGTH).content
        assert "[1]" in last
        assert "last page" in last
        assert "End of document" in last
        assert "Search for this document first" in tool.call(document_id=99).content

    def test_read_budget_is_enforced(self):
        from paperless_ai.agent_chat import AGENT_MAX_READS
        from paperless_ai.agent_chat import _build_read_tool

        doc = _doc(1)
        doc.content = "text"
        registry = _ReferenceRegistry([doc])
        registry.register("1", doc.title, "text")
        tool = _build_read_tool(registry)
        for _ in range(AGENT_MAX_READS):
            tool.call(document_id=1)
        assert "budget exhausted" in tool.call(document_id=1).content

    def test_empty_or_oversized_query_does_not_use_retrieval(self):
        tool, _registry, retrieve = self.search_tool([_doc(1)])
        for query in [" ", "a" * 1001]:
            assert "at most 1000 characters" in tool.call(query=query).content
        retrieve.assert_not_called()

    def test_negative_read_offset_does_not_consume_budget(self):
        from paperless_ai.agent_chat import _build_read_tool

        registry = _ReferenceRegistry([_doc(1)])
        registry.register("1", "Doc 1", "text")
        tool = _build_read_tool(registry)
        assert "non-negative" in tool.call(document_id=1, offset=-1).content
        assert registry.read_count == 0
