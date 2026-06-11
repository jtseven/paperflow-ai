"""Semantic (embedding-based) document search over the LanceDB vector store.

The same vector index that powers chat is reused here to rank documents by
meaning rather than keywords, so a query like "bike order" can surface a German
"Fahrradbestellung". Retrieval is global; the calling view is responsible for
intersecting the results with the documents the user is allowed to view.
"""

import logging

from paperless.config import AIConfig
from paperless_ai.chat import snippet_from_node
from paperless_ai.indexing import load_or_build_index

logger = logging.getLogger("paperless_ai.search")

# Over-fetch relative to the requested limit: a single document is chunked into
# several nodes, and the caller drops anything the user may not view, so we need
# headroom to still return a full page.
SEMANTIC_OVERFETCH = 4


class SemanticSearchResult:
    """One ranked document hit: its id, similarity score and a preview snippet."""

    __slots__ = ("document_id", "score", "snippet")

    def __init__(self, document_id: int, score: float, snippet: str) -> None:
        self.document_id = document_id
        self.score = score
        self.snippet = snippet


def semantic_search(query_str: str, limit: int = 10) -> list[SemanticSearchResult]:
    """Return up to ``limit`` documents ranked by embedding similarity.

    Results are de-duplicated by document (a document may match through several
    chunks; the highest-scoring chunk wins) and ordered by descending score.
    Assumes the LLM index exists — callers should check ``llm_index_exists()``
    first and surface a friendly message otherwise.
    """
    from llama_index.core.retrievers import VectorIndexRetriever

    config = AIConfig()
    index = load_or_build_index(config)
    retriever = VectorIndexRetriever(
        index=index,
        similarity_top_k=max(limit, 1) * SEMANTIC_OVERFETCH,
    )

    nodes = retriever.retrieve(query_str)

    results: list[SemanticSearchResult] = []
    seen: set[int] = set()
    for node in nodes:
        try:
            document_id = int(node.metadata["document_id"])
        except (KeyError, TypeError, ValueError):  # pragma: no cover - defensive
            continue
        if document_id in seen:
            continue
        seen.add(document_id)
        results.append(
            SemanticSearchResult(
                document_id=document_id,
                score=float(node.score) if node.score is not None else 0.0,
                snippet=snippet_from_node(node),
            ),
        )
        if len(results) >= limit:
            break
    return results
