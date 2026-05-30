"""
Agentic, all-documents chat backend.

Upstream's :func:`paperless_ai.chat.stream_chat_with_documents` performs a
single retrieval + synthesis pass scoped to one (or a fixed list of) document.
The Paperflow dashboard widget instead offers an *agentic* chat over the whole
collection: the LLM drives a retrieval tool, may call it several times to
gather evidence, and cites the documents it actually used.

This module reuses upstream's FAISS document-filtered retriever and the
streaming-metadata protocol (``__PAPERLESS_CHAT_METADATA__`` trailer) so the
frontend needs no special handling — it parses the same trailer it already
parses for the per-document chat. Citations are *dynamic*: only documents the
retrieval tool surfaced during the run appear as references, numbered in the
order they were first seen so the inline ``[n]`` markers line up.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from paperless_ai.chat import CHAT_ERROR_MESSAGE
from paperless_ai.chat import CHAT_NO_CONTENT_MESSAGE
from paperless_ai.chat import _build_document_reference
from paperless_ai.chat import _format_chat_metadata_trailer
from paperless_ai.chat import _get_document_filtered_retriever

if TYPE_CHECKING:
    from collections.abc import Generator

    from documents.models import Document

logger = logging.getLogger("paperless_ai.agent_chat")

AGENT_RETRIEVER_TOP_K = 5
AGENT_MAX_REFERENCES = 10

AGENT_SYSTEM_PROMPT = """You are a helpful assistant for a document management system.
Answer the user's question using only information found in the user's documents.
Always use the `search_documents` tool to look for relevant information before
answering; call it multiple times with different queries if that helps. If the
tool returns nothing relevant, say so politely and do not invent information.
Reply in the same language as the question and format your answer with markdown.

Each chunk returned by the tool is prefixed with a citation marker like `[1]`.
Cite your sources inline using those exact markers, placing each citation
directly after the information it supports. Reuse the same marker for several
chunks that share the same document id. Do not write your own list of
references at the end — the application renders that for you."""


class _ReferenceRegistry:
    """Tracks which documents the retrieval tool surfaced, in citation order."""

    def __init__(self, documents: list[Document]) -> None:
        self._allowed = {str(doc.pk): doc for doc in documents}
        self._numbers: dict[str, int] = {}
        self._titles: dict[str, str | None] = {}

    def register(self, document_id: str, title: str | None) -> int | None:
        """Assign (or return) the 1-based citation number for a document."""
        if document_id not in self._allowed:
            return None
        if document_id not in self._numbers:
            if len(self._numbers) >= AGENT_MAX_REFERENCES:
                return None
            self._numbers[document_id] = len(self._numbers) + 1
            self._titles[document_id] = title
        return self._numbers[document_id]

    def references(self) -> list[dict[str, int | str]]:
        ordered = sorted(self._numbers.items(), key=lambda kv: kv[1])
        return [
            _build_document_reference(self._allowed[doc_id], self._titles.get(doc_id))
            for doc_id, _ in ordered
        ]


def _build_search_tool(index, registry: _ReferenceRegistry):
    from llama_index.core.tools import FunctionTool

    doc_ids = set(registry._allowed.keys())
    retriever = _get_document_filtered_retriever(
        index,
        doc_ids,
        AGENT_RETRIEVER_TOP_K,
    )

    def search_documents(query: str) -> str:
        """Search the user's documents for information relevant to a query.

        Returns the most relevant document chunks, each prefixed with a
        citation marker to use when referring to it in the answer.
        """
        nodes = retriever.retrieve(query)
        if not nodes:
            return "No relevant documents were found for that query."

        blocks: list[str] = []
        for node_with_score in nodes:
            metadata = node_with_score.node.metadata
            document_id = str(metadata.get("document_id"))
            number = registry.register(document_id, metadata.get("title"))
            if number is None:
                continue
            title = metadata.get("title") or document_id
            content = node_with_score.node.get_content()
            blocks.append(f"[{number}] (document id {document_id}: {title})\n{content}")

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
    """Stream an agentic answer over ``documents``.

    Yields text chunks followed by the standard chat-metadata trailer carrying
    the documents the agent actually cited.
    """
    try:
        yield from _drive_async_stream(query_str, documents)
    except Exception as e:  # pragma: no cover - defensive
        logger.exception("Failed to stream agentic chat response: %s", e)
        yield CHAT_ERROR_MESSAGE


def _drive_async_stream(
    query_str: str,
    documents: list[Document],
) -> Generator[str, None, None]:
    """Pump the async streaming generator from a synchronous context."""
    loop = asyncio.new_event_loop()
    try:
        agen = _astream_agentic_chat(query_str, documents)
        while True:
            try:
                chunk = loop.run_until_complete(agen.__anext__())
            except StopAsyncIteration:
                break
            yield chunk
    finally:
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.close()


async def _astream_agentic_chat(query_str: str, documents: list[Document]):
    from llama_index.core.agent.workflow import AgentStream
    from llama_index.core.agent.workflow import FunctionAgent

    from paperless_ai.client import AIClient
    from paperless_ai.indexing import load_or_build_index

    if not documents:
        yield CHAT_NO_CONTENT_MESSAGE
        return

    client = AIClient()
    index = load_or_build_index()
    registry = _ReferenceRegistry(documents)
    search_tool = _build_search_tool(index, registry)

    agent = FunctionAgent(
        tools=[search_tool],
        llm=client.llm,
        system_prompt=AGENT_SYSTEM_PROMPT,
    )

    logger.debug("Agentic chat query: %s", query_str)

    handler = agent.run(query_str)
    produced_text = False
    async for event in handler.stream_events():
        if isinstance(event, AgentStream) and event.delta:
            produced_text = True
            yield event.delta

    # Surface any error raised inside the workflow.
    await handler

    if not produced_text:
        yield CHAT_NO_CONTENT_MESSAGE
        return

    references = registry.references()
    if references:
        yield _format_chat_metadata_trailer(references)
