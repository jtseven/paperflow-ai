from __future__ import annotations

from unittest import mock

from django.contrib.auth.models import Permission
from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.test import APITestCase

from documents.models import Document
from paperless_ai.search import SemanticSearchResult


class TestSemanticSearchView(APITestCase):
    ENDPOINT = "/api/search/semantic/"

    def setUp(self) -> None:
        super().setUp()
        self.user = User.objects.create_superuser(username="temp_admin")
        self.client.force_authenticate(user=self.user)

    def _ai_enabled(self) -> mock.MagicMock:
        m = mock.MagicMock()
        m.llm_index_enabled = True
        return m

    def test_short_query_is_rejected(self) -> None:
        resp = self.client.get(self.ENDPOINT, {"query": "ab"})
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_ai_disabled_returns_empty_with_flag(self) -> None:
        disabled = mock.MagicMock()
        disabled.llm_index_enabled = False
        with mock.patch("documents.views.AIConfig", return_value=disabled):
            resp = self.client.get(self.ENDPOINT, {"query": "invoice"})
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data == {
            "documents": [],
            "ai_enabled": False,
            "index_ready": False,
        }

    def test_index_not_ready_returns_empty_with_flag(self) -> None:
        with (
            mock.patch("documents.views.AIConfig", return_value=self._ai_enabled()),
            mock.patch("paperless_ai.indexing.llm_index_exists", return_value=False),
        ):
            resp = self.client.get(self.ENDPOINT, {"query": "invoice"})
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["index_ready"] is False
        assert resp.data["documents"] == []

    def test_returns_ranked_documents_with_score_and_snippet(self) -> None:
        doc1 = Document.objects.create(
            title="Bike order",
            content="Fahrradbestellung bei Sport Conrad",
            checksum="sem-1",
            mime_type="application/pdf",
        )
        doc2 = Document.objects.create(
            title="Insurance",
            content="Versicherungspolice",
            checksum="sem-2",
            mime_type="application/pdf",
        )
        # doc2 ranks first, doc1 second
        ranked = [
            SemanticSearchResult(doc2.id, 0.91, "Versicherung snippet"),
            SemanticSearchResult(doc1.id, 0.72, "Fahrrad snippet"),
        ]
        with (
            mock.patch("documents.views.AIConfig", return_value=self._ai_enabled()),
            mock.patch("paperless_ai.indexing.llm_index_exists", return_value=True),
            mock.patch(
                "paperless_ai.search.semantic_search",
                return_value=ranked,
            ) as mock_search,
        ):
            resp = self.client.get(
                self.ENDPOINT,
                {"query": "bicycle order", "limit": 5},
            )

        assert resp.status_code == status.HTTP_200_OK
        mock_search.assert_called_once()
        docs = resp.data["documents"]
        # Ranking order from the semantic helper is preserved.
        assert [d["id"] for d in docs] == [doc2.id, doc1.id]
        assert docs[0]["search_score"] == 0.91
        assert docs[0]["search_snippet"] == "Versicherung snippet"
        assert resp.data["ai_enabled"] is True
        assert resp.data["index_ready"] is True

    def test_results_excluded_when_user_cannot_view_document(self) -> None:
        """A hit the user may not view must be dropped from the results."""
        owner = User.objects.create_user(username="owner")
        private = Document.objects.create(
            title="Private",
            content="secret",
            checksum="sem-3",
            mime_type="application/pdf",
            owner=owner,
        )
        viewer = User.objects.create_user(username="viewer")
        # Global view_document permission, but no object access to the owned doc.
        viewer.user_permissions.add(
            Permission.objects.get(
                codename="view_document",
                content_type__app_label="documents",
            ),
        )
        self.client.force_authenticate(user=viewer)

        with (
            mock.patch("documents.views.AIConfig", return_value=self._ai_enabled()),
            mock.patch("paperless_ai.indexing.llm_index_exists", return_value=True),
            mock.patch(
                "paperless_ai.search.semantic_search",
                return_value=[SemanticSearchResult(private.id, 0.99, "secret")],
            ),
        ):
            resp = self.client.get(self.ENDPOINT, {"query": "secret stuff"})

        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["documents"] == []
