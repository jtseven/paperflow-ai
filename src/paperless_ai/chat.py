import json
import logging
import sys

from asgiref.sync import sync_to_async

from documents.models import Document
from paperless_ai.client import AIClient
from paperless_ai.indexing import get_rag_prompt_helper
from paperless_ai.indexing import load_or_build_index

logger = logging.getLogger("paperless_ai.chat")

CHAT_ERROR_MESSAGE = "Sorry, something went wrong while generating a response."
CHAT_NO_CONTENT_MESSAGE = "Sorry, I couldn't find any content to answer your question."
MAX_CHAT_REFERENCES = 3
CHAT_RETRIEVER_TOP_K = 5

# Maximum characters of a node's text kept as a citation preview snippet.
CITATION_SNIPPET_MAX = 240

# --- Structured streaming protocol ----------------------------------------
# The chat endpoint streams newline-delimited JSON (one event per line). These
# type names are mirrored in the frontend ChatService
# (src-ui/src/app/services/chat.service.ts) — keep both sides in sync.
EVENT_TOOL_CALL = "tool_call"
EVENT_TOOL_RESULT = "tool_result"
EVENT_TOKEN = "token"
EVENT_CITATION = "citation"
EVENT_ERROR = "error"
EVENT_DONE = "done"


def chat_event(event_type: str, **fields) -> str:
    """Serialize a single chat-stream event as one NDJSON line."""
    return json.dumps({"type": event_type, **fields}, separators=(",", ":")) + "\n"


def token_event(text: str) -> str:
    return chat_event(EVENT_TOKEN, text=text)


def error_event(message: str = CHAT_ERROR_MESSAGE) -> str:
    return chat_event(EVENT_ERROR, message=message)


def done_event() -> str:
    return chat_event(EVENT_DONE)


def snippet_from_node(node) -> str:
    """A short, single-line preview of a node's text for citation hovers."""
    text = " ".join(node.get_content().split())
    if len(text) > CITATION_SNIPPET_MAX:
        text = text[:CITATION_SNIPPET_MAX].rstrip() + "…"
    return text


async def aiterate_sync_stream(sync_iterable):
    """Adapt a synchronous generator into an async iterator.

    Under ASGI, ``StreamingHttpResponse.__aiter__`` falls back to ``list()``-ing
    a *synchronous* ``streaming_content`` before sending anything, which buffers
    the entire response and defeats token-by-token streaming. Handing the
    response an *async* iterator keeps Django on its incremental ``async for``
    path so each chunk is flushed as soon as it is produced.

    Each ``next()`` runs via ``sync_to_async`` (thread-sensitive, so the whole
    generator runs on a single worker thread throughout), where Django ORM
    access remains legal — the same reason the underlying chat generators are
    written synchronously.
    """
    sentinel = object()
    iterator = iter(sync_iterable)
    while True:
        item = await sync_to_async(next)(iterator, sentinel)
        if item is sentinel:
            break
        yield item

CHAT_PROMPT_TMPL = """Context information is below.
    ---------------------
    {context_str}
    ---------------------
    Given the context information and not prior knowledge, answer the query.
    Query: {query_str}
    Answer:"""


def _build_document_reference(
    document: Document,
    title: str | None = None,
) -> dict[str, int | str]:
    return {
        "id": document.pk,
        "title": title or document.title or document.filename,
    }


def _citations_from_nodes(
    documents: list[Document],
    top_nodes: list,
) -> list[dict]:
    """Build ``citation`` event payloads from retrieved nodes.

    One citation per distinct allowed document, numbered ``1..n`` in retrieval
    order, carrying the document title and a preview snippet of the matched
    chunk. The marker lines up with the ``[n]`` markers the model is asked to
    cite inline.
    """
    allowed_documents = {doc.pk: doc for doc in documents}
    citations: list[dict] = []
    seen_document_ids: set[int] = set()

    for node in top_nodes:
        try:
            document_id = int(node.metadata["document_id"])
        except (KeyError, TypeError, ValueError):  # pragma: no cover
            continue

        if document_id in seen_document_ids or document_id not in allowed_documents:
            continue

        seen_document_ids.add(document_id)
        document = allowed_documents[document_id]
        reference = _build_document_reference(document, node.metadata.get("title"))
        citations.append(
            {
                "marker": len(citations) + 1,
                "document_id": reference["id"],
                "title": reference["title"],
                "snippet": snippet_from_node(node),
            },
        )

        if len(citations) >= MAX_CHAT_REFERENCES:  # pragma: no cover
            break

    return citations


def _get_document_filtered_retriever(index, doc_ids: set[str], similarity_top_k: int):
    from llama_index.core.base.base_retriever import BaseRetriever
    from llama_index.core.schema import NodeWithScore
    from llama_index.core.vector_stores import VectorStoreQuery

    class DocumentFilteredFaissRetriever(BaseRetriever):
        def __init__(self):
            super().__init__()
            self._cached_query_str = None
            self._cached_nodes = []

        def _retrieve(self, query_bundle):
            if query_bundle.query_str == self._cached_query_str:
                return self._cached_nodes

            if query_bundle.embedding is None:
                query_bundle.embedding = (
                    index._embed_model.get_agg_embedding_from_queries(
                        query_bundle.embedding_strs,
                    )
                )

            faiss_index = index.vector_store._faiss_index
            max_top_k = faiss_index.ntotal
            if max_top_k == 0:
                self._cached_query_str = query_bundle.query_str
                self._cached_nodes = []
                return []

            query_top_k = min(max(similarity_top_k, 1), max_top_k)
            allowed_nodes: list[NodeWithScore] = []
            seen_node_ids: set[str] = set()

            # ``docstore.docs`` deserializes the *entire* docstore on every
            # access, so resolve it once per retrieval instead of per candidate
            # node — otherwise filtering to a small document set (which makes
            # the loop below expand query_top_k repeatedly) is O(N²) and hangs.
            docstore_docs = index.docstore.docs

            while query_top_k <= max_top_k:
                query_result = index.vector_store.query(
                    VectorStoreQuery(
                        query_embedding=query_bundle.embedding,
                        similarity_top_k=query_top_k,
                    ),
                )

                for vector_id, score in zip(
                    query_result.ids or [],
                    query_result.similarities or [],
                    strict=False,
                ):
                    node_id = index.index_struct.nodes_dict.get(vector_id)
                    if node_id is None or node_id in seen_node_ids:
                        continue

                    node = docstore_docs.get(node_id)
                    if node is None or node.metadata.get("document_id") not in doc_ids:
                        continue

                    seen_node_ids.add(node_id)
                    allowed_nodes.append(NodeWithScore(node=node, score=score))

                    if len(allowed_nodes) >= similarity_top_k:
                        self._cached_query_str = query_bundle.query_str
                        self._cached_nodes = allowed_nodes
                        return allowed_nodes

                if query_top_k == max_top_k:
                    self._cached_query_str = query_bundle.query_str
                    self._cached_nodes = allowed_nodes
                    return allowed_nodes

                query_top_k = min(query_top_k * 2, max_top_k)

            self._cached_query_str = query_bundle.query_str
            self._cached_nodes = allowed_nodes
            return allowed_nodes

    return DocumentFilteredFaissRetriever()


def stream_chat_with_documents(query_str: str, documents: list[Document]):
    """Stream a per-document RAG answer as NDJSON events.

    Emits ``citation`` events for the retrieved sources, then ``token`` events
    for the streamed answer, and finally ``done`` (or ``error``).
    """
    try:
        yield from _stream_chat_with_documents(query_str, documents)
    except Exception as e:
        logger.exception(f"Failed to stream document chat response: {e}", exc_info=True)
        yield error_event()
        return
    yield done_event()


def _stream_chat_with_documents(query_str: str, documents: list[Document]):
    client = AIClient()
    index = load_or_build_index()

    doc_ids = [str(doc.pk) for doc in documents]

    # Filter only the node(s) that match the document IDs
    nodes = [
        node
        for node in index.docstore.docs.values()
        if node.metadata.get("document_id") in doc_ids
    ]

    if len(nodes) == 0:
        logger.warning("No nodes found for the given documents.")
        yield token_event(CHAT_NO_CONTENT_MESSAGE)
        return

    from llama_index.core.prompts import PromptTemplate
    from llama_index.core.query_engine import RetrieverQueryEngine
    from llama_index.core.response_synthesizers import get_response_synthesizer

    retriever = _get_document_filtered_retriever(
        index,
        set(doc_ids),
        CHAT_RETRIEVER_TOP_K,
    )

    top_nodes = retriever.retrieve(query_str)
    if len(top_nodes) == 0:
        logger.warning("Retriever returned no nodes for the given documents.")
        yield token_event(CHAT_NO_CONTENT_MESSAGE)
        return

    for citation in _citations_from_nodes(documents, top_nodes):
        yield chat_event(EVENT_CITATION, **citation)

    prompt_template = PromptTemplate(template=CHAT_PROMPT_TMPL)
    response_synthesizer = get_response_synthesizer(
        llm=client.llm,
        prompt_helper=get_rag_prompt_helper(),
        text_qa_template=prompt_template,
        streaming=True,
    )

    query_engine = RetrieverQueryEngine.from_args(
        retriever=retriever,
        llm=client.llm,
        response_synthesizer=response_synthesizer,
        streaming=True,
    )

    logger.debug("Document chat query: %s", query_str)

    response_stream = query_engine.query(query_str)

    for chunk in response_stream.response_gen:
        yield token_event(chunk)
        sys.stdout.flush()
