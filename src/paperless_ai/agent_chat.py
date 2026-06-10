"""
Agentic, all-documents chat backend.

Upstream's :func:`paperless_ai.chat.stream_chat_with_documents` performs a
single retrieval + synthesis pass scoped to one (or a fixed list of) document.
The Paperflow dashboard widget instead offers an *agentic* chat over the whole
collection: the LLM drives a retrieval tool, may call it several times to
gather evidence, and cites the documents it actually used.

The backend streams the same structured NDJSON event protocol as the
per-document chat (see :mod:`paperless_ai.chat`): ``tool_call`` / ``tool_result``
events expose the agent's searches live, ``token`` events stream the answer,
``citation`` events map each ``[n]`` marker to the exact source document (with a
preview snippet), and a final ``done`` (or ``error``) closes the stream. The
frontend renders only the markers that actually appear in the answer, so
citations are *dynamic* — only documents the model truly used are shown.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from paperless_ai.chat import CHAT_NO_CONTENT_MESSAGE
from paperless_ai.chat import EVENT_CITATION
from paperless_ai.chat import EVENT_TOOL_CALL
from paperless_ai.chat import EVENT_TOOL_RESULT
from paperless_ai.chat import _build_document_reference
from paperless_ai.chat import chat_event
from paperless_ai.chat import done_event
from paperless_ai.chat import error_event
from paperless_ai.chat import snippet_from_node
from paperless_ai.chat import token_event

if TYPE_CHECKING:
    from collections.abc import Generator

    from documents.models import Document

logger = logging.getLogger("paperless_ai.agent_chat")

AGENT_RETRIEVER_TOP_K = 5
AGENT_MAX_REFERENCES = 10

CHAT_INDEX_NOT_READY_MESSAGE = (
    "The document index isn't ready yet. It is being built in the background — "
    "please try again in a few minutes."
)

AGENT_SYSTEM_PROMPT = """You are a helpful assistant for a document management system.
Answer the user's question using only information found in the user's documents.
Always use the `search_documents` tool to look for relevant information before
answering; call it multiple times with different queries if that helps. If the
tool returns nothing relevant, say so politely and do not invent information.
Reply in the same language as the question and format your answer with markdown.

Each chunk returned by the tool is prefixed with a citation marker such as [1].
Cite your sources inline using those exact markers written as plain text, for
example: "The lease runs for 24 months [1]." Do NOT wrap the markers in
backticks, code spans, bold, or any other formatting — write them as bare
[number]. Place each citation directly after the information it supports, and
reuse the same marker for several chunks that share the same document id. Do
not write your own list of references at the end — the application renders that
for you."""


class _ReferenceRegistry:
    """Tracks which documents the retrieval tool surfaced, in citation order.

    Markers are assigned the first time a document is surfaced; the matching
    ``citation`` event payload is queued in ``_pending`` so the driver can emit
    it as soon as it is discovered. Per-search bookkeeping in ``calls`` lets the
    driver report a result count and the documents found for each ``tool_call``.
    """

    def __init__(self, documents: list[Document]) -> None:
        self._allowed = {str(doc.pk): doc for doc in documents}
        self._numbers: dict[str, int] = {}
        self._pending: list[dict] = []
        self.calls: dict[str, dict] = {}

    def register(
        self,
        document_id: str,
        title: str | None,
        snippet: str,
    ) -> int | None:
        """Assign (or return) the 1-based citation number for a document."""
        if document_id not in self._allowed:
            return None
        if document_id not in self._numbers:
            if len(self._numbers) >= AGENT_MAX_REFERENCES:
                return None
            marker = len(self._numbers) + 1
            self._numbers[document_id] = marker
            reference = _build_document_reference(self._allowed[document_id], title)
            self._pending.append(
                {
                    "marker": marker,
                    "document_id": reference["id"],
                    "title": reference["title"],
                    "snippet": snippet,
                },
            )
        return self._numbers[document_id]

    def title_for(self, document_id: str) -> str:
        return _build_document_reference(self._allowed[document_id])["title"]

    def drain_pending(self) -> list[dict]:
        pending, self._pending = self._pending, []
        return pending

    def record_call(self, query: str, count: int, documents: list[dict]) -> None:
        self.calls[query] = {"count": count, "documents": documents}


def _build_search_tool(index, registry: _ReferenceRegistry):
    from llama_index.core.retrievers import VectorIndexRetriever
    from llama_index.core.tools import FunctionTool

    from paperless_ai.indexing import _document_id_filters

    retriever = VectorIndexRetriever(
        index=index,
        similarity_top_k=AGENT_RETRIEVER_TOP_K,
        filters=_document_id_filters(registry._allowed.keys()),
    )

    def search_documents(query: str) -> str:
        """Search the user's documents for information relevant to a query.

        Returns the most relevant document chunks, each prefixed with a
        citation marker to use when referring to it in the answer.
        """
        nodes = retriever.retrieve(query)
        if not nodes:
            registry.record_call(query, 0, [])
            return "No relevant documents were found for that query."

        blocks: list[str] = []
        surfaced: list[dict] = []
        surfaced_ids: set[int] = set()
        for node_with_score in nodes:
            metadata = node_with_score.node.metadata
            document_id = str(metadata.get("document_id"))
            number = registry.register(
                document_id,
                metadata.get("title"),
                snippet_from_node(node_with_score.node),
            )
            if number is None:
                continue
            title = metadata.get("title") or document_id
            content = node_with_score.node.get_content()
            blocks.append(f"[{number}] (document id {document_id}: {title})\n{content}")
            doc_pk = int(document_id)
            if doc_pk not in surfaced_ids:
                surfaced_ids.add(doc_pk)
                surfaced.append(
                    {
                        "id": doc_pk,
                        "title": registry.title_for(document_id),
                        "marker": number,
                    },
                )

        registry.record_call(query, len(nodes), surfaced)
        if not blocks:
            return "No relevant documents were found for that query."
        return "\n\n".join(blocks)

    return FunctionTool.from_defaults(
        fn=search_documents,
        name="search_documents",
        description=(
            "Search the user's document collection for information relevant to "
            "a natural-language query and return the most relevant excerpts."
        ),
    )


def stream_agentic_chat(
    query_str: str,
    documents: list[Document],
) -> Generator[str, None, None]:
    """Stream an agentic answer over ``documents`` as NDJSON events.

    All Django ORM access (``AIClient`` reads the configuration from the
    database, building the index may query documents) happens **here**, in the
    synchronous generator, which the streaming view iterates on a worker thread
    where the ORM is available. Only the agent's event streaming — which talks
    to the LLM and the memory-mapped LanceDB table, never the ORM — runs inside
    the private event loop in :func:`_drive_async_stream`. Doing the ORM work
    inside that loop would trip Django's ``SynchronousOnlyOperation`` guard.
    """
    try:
        from llama_index.core.agent.workflow import FunctionAgent

        from paperless_ai.client import AIClient
        from paperless_ai.indexing import llm_index_exists
        from paperless_ai.indexing import load_or_build_index
        from paperless_ai.indexing import queue_llm_index_update_if_needed

        if not documents:
            yield token_event(CHAT_NO_CONTENT_MESSAGE)
            yield done_event()
            return

        client = AIClient()
        if not llm_index_exists():
            # No index has been built yet. Queue a build and tell the user
            # instead of letting every search come back empty.
            logger.info("Agentic chat requested before the LLM index was built.")
            queue_llm_index_update_if_needed(
                rebuild=True,
                reason="Agentic chat requested before the LLM index was built",
            )
            yield token_event(CHAT_INDEX_NOT_READY_MESSAGE)
            yield done_event()
            return
        index = load_or_build_index(client.settings)
        registry = _ReferenceRegistry(documents)
        search_tool = _build_search_tool(index, registry)

        agent = FunctionAgent(
            tools=[search_tool],
            llm=client.llm,
            system_prompt=AGENT_SYSTEM_PROMPT,
        )

        logger.debug("Agentic chat query: %s", query_str)

        yield from _drive_async_stream(agent, query_str, registry)
    except Exception as e:  # pragma: no cover - defensive
        logger.exception("Failed to stream agentic chat response: %s", e)
        yield error_event()
        return
    yield done_event()


def _drive_async_stream(
    agent,
    query_str: str,
    registry: _ReferenceRegistry,
) -> Generator[str, None, None]:
    """Pump the async agent-event stream from a synchronous context.

    Receives an already-constructed ``agent`` so that no Django ORM access
    happens inside the event loop (see :func:`stream_agentic_chat`).
    """
    loop = asyncio.new_event_loop()
    try:
        agen = _astream_agent_events(agent, query_str, registry)
        while True:
            try:
                chunk = loop.run_until_complete(agen.__anext__())
            except StopAsyncIteration:
                break
            yield chunk
    finally:
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.close()


async def _astream_agent_events(agent, query_str: str, registry: _ReferenceRegistry):
    from llama_index.core.agent.workflow import AgentStream
    from llama_index.core.agent.workflow import ToolCall
    from llama_index.core.agent.workflow import ToolCallResult

    handler = agent.run(query_str)
    produced_text = False
    async for event in handler.stream_events():
        # ToolCallResult subclasses ToolCall in some llama-index versions, so
        # check the more specific type first.
        if isinstance(event, ToolCallResult):
            info = registry.calls.get(event.tool_kwargs.get("query", ""), {})
            yield chat_event(
                EVENT_TOOL_RESULT,
                id=event.tool_id,
                name=event.tool_name,
                count=info.get("count", 0),
                documents=info.get("documents", []),
            )
            for citation in registry.drain_pending():
                yield chat_event(EVENT_CITATION, **citation)
        elif isinstance(event, ToolCall):
            yield chat_event(
                EVENT_TOOL_CALL,
                id=event.tool_id,
                name=event.tool_name,
                query=event.tool_kwargs.get("query", ""),
            )
        elif isinstance(event, AgentStream) and event.delta:
            produced_text = True
            for citation in registry.drain_pending():
                yield chat_event(EVENT_CITATION, **citation)
            yield token_event(event.delta)

    # Surface any error raised inside the workflow.
    await handler

    if not produced_text:
        yield token_event(CHAT_NO_CONTENT_MESSAGE)
        return

    for citation in registry.drain_pending():
        yield chat_event(EVENT_CITATION, **citation)
