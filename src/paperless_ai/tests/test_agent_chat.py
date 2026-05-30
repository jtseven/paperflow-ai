import json
from types import SimpleNamespace
from unittest.mock import MagicMock
from unittest.mock import patch

from llama_index.core.agent.workflow import AgentStream

from paperless_ai.agent_chat import AGENT_MAX_REFERENCES
from paperless_ai.agent_chat import _ReferenceRegistry
from paperless_ai.agent_chat import stream_agentic_chat
from paperless_ai.chat import CHAT_METADATA_DELIMITER
from paperless_ai.chat import CHAT_NO_CONTENT_MESSAGE


def _doc(pk: int, title: str = "") -> SimpleNamespace:
    return SimpleNamespace(pk=pk, title=title or f"Doc {pk}", filename=f"{pk}.pdf")


class TestReferenceRegistry:
    def test_assigns_sequential_numbers_in_order_seen(self):
        registry = _ReferenceRegistry([_doc(7), _doc(3), _doc(5)])
        assert registry.register("3", "Three") == 1
        assert registry.register("7", "Seven") == 2
        # Re-registering returns the same number and keeps the original title.
        assert registry.register("3", "ignored") == 1

    def test_ignores_documents_outside_allowed_set(self):
        registry = _ReferenceRegistry([_doc(1)])
        assert registry.register("999", "Nope") is None
        assert registry.references() == []

    def test_references_ordered_by_citation_number(self):
        registry = _ReferenceRegistry([_doc(1, "One"), _doc(2, "Two")])
        registry.register("2", "Two")
        registry.register("1", "One")
        refs = registry.references()
        assert refs == [
            {"id": 2, "title": "Two"},
            {"id": 1, "title": "One"},
        ]

    def test_caps_number_of_references(self):
        docs = [_doc(i) for i in range(1, AGENT_MAX_REFERENCES + 5)]
        registry = _ReferenceRegistry(docs)
        for doc in docs:
            registry.register(str(doc.pk), doc.title)
        assert len(registry.references()) == AGENT_MAX_REFERENCES


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
        chunks = list(stream_agentic_chat("question", []))
        assert chunks == [CHAT_NO_CONTENT_MESSAGE]

    def test_streams_text_then_metadata_trailer(self):
        documents = [_doc(1, "Invoice"), _doc(2, "Receipt")]

        def fake_build_tool(index, registry):
            # Simulate the agent's retrieval surfacing document 2.
            registry.register("2", "Receipt")
            return MagicMock()

        fake_agent = MagicMock()
        fake_agent.run.return_value = _FakeHandler(
            [_agent_stream("Hello "), _agent_stream("world [1]")],
        )

        with (
            patch("paperless_ai.client.AIClient"),
            patch("paperless_ai.indexing.load_or_build_index"),
            patch(
                "paperless_ai.agent_chat._build_search_tool",
                side_effect=fake_build_tool,
            ),
            patch(
                "llama_index.core.agent.workflow.FunctionAgent",
                return_value=fake_agent,
            ),
        ):
            chunks = list(stream_agentic_chat("question", documents))

        text = "".join(c for c in chunks if not c.startswith(CHAT_METADATA_DELIMITER))
        assert text == "Hello world [1]"

        trailer = next(c for c in chunks if c.startswith(CHAT_METADATA_DELIMITER))
        payload = json.loads(trailer[len(CHAT_METADATA_DELIMITER) :])
        assert payload == {"references": [{"id": 2, "title": "Receipt"}]}

    def test_no_text_produced_yields_no_content(self):
        documents = [_doc(1)]
        fake_agent = MagicMock()
        fake_agent.run.return_value = _FakeHandler([])

        with (
            patch("paperless_ai.client.AIClient"),
            patch("paperless_ai.indexing.load_or_build_index"),
            patch("paperless_ai.agent_chat._build_search_tool", return_value=MagicMock()),
            patch(
                "llama_index.core.agent.workflow.FunctionAgent",
                return_value=fake_agent,
            ),
        ):
            chunks = list(stream_agentic_chat("question", documents))

        assert chunks == [CHAT_NO_CONTENT_MESSAGE]
