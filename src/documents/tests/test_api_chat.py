from __future__ import annotations

from unittest import mock

from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.test import APITestCase


class TestChatStreamingViewInputValidation(APITestCase):
    def setUp(self) -> None:
        super().setUp()
        self.user = User.objects.create_superuser(username="temp_admin")
        self.client.force_authenticate(user=self.user)

    def _mock_ai_enabled(self) -> mock.MagicMock:
        """Return a mock AIConfig instance with ai_enabled=True."""
        m = mock.MagicMock()
        m.ai_enabled = True
        return m

    def test_oversized_question_is_rejected(self) -> None:
        with mock.patch(
            "documents.views.AIConfig",
            return_value=self._mock_ai_enabled(),
        ):
            resp = self.client.post(
                "/api/documents/chat/",
                {"q": "x" * 4001},
                format="json",
            )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_missing_question_is_rejected(self) -> None:
        with mock.patch(
            "documents.views.AIConfig",
            return_value=self._mock_ai_enabled(),
        ):
            resp = self.client.post(
                "/api/documents/chat/",
                {},
                format="json",
            )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_invalid_history_role_is_rejected(self) -> None:
        with mock.patch(
            "documents.views.AIConfig",
            return_value=self._mock_ai_enabled(),
        ):
            resp = self.client.post(
                "/api/documents/chat/",
                {"q": "hi", "history": [{"role": "system", "content": "nope"}]},
                format="json",
            )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_blank_history_content_is_rejected(self) -> None:
        with mock.patch(
            "documents.views.AIConfig",
            return_value=self._mock_ai_enabled(),
        ):
            resp = self.client.post(
                "/api/documents/chat/",
                {"q": "hi", "history": [{"role": "user", "content": "   "}]},
                format="json",
            )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_oversized_history_content_is_rejected(self) -> None:
        with mock.patch(
            "documents.views.AIConfig",
            return_value=self._mock_ai_enabled(),
        ):
            resp = self.client.post(
                "/api/documents/chat/",
                {"q": "hi", "history": [{"role": "user", "content": "x" * 4001}]},
                format="json",
            )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_too_many_history_items_rejected(self) -> None:
        from documents.views import MAX_CHAT_HISTORY_ITEMS

        history = [
            {"role": "user", "content": str(i)}
            for i in range(MAX_CHAT_HISTORY_ITEMS + 1)
        ]
        with mock.patch(
            "documents.views.AIConfig",
            return_value=self._mock_ai_enabled(),
        ):
            resp = self.client.post(
                "/api/documents/chat/",
                {"q": "hi", "history": history},
                format="json",
            )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_valid_history_is_forwarded_to_stream(self) -> None:
        """A valid history reaches build_chat_history and the stream call."""
        history = [
            {"role": "user", "content": "first question"},
            {"role": "assistant", "content": "first answer"},
        ]
        with (
            mock.patch(
                "documents.views.AIConfig",
                return_value=self._mock_ai_enabled(),
            ),
            mock.patch("documents.views.build_chat_history") as mock_build,
            mock.patch("documents.views.stream_agentic_chat") as mock_stream,
        ):
            mock_stream.return_value = iter(['{"type":"done"}\n'])
            resp = self.client.post(
                "/api/documents/chat/",
                {"q": "follow up", "history": history},
                format="json",
            )

        assert resp.status_code == status.HTTP_200_OK
        # The validated history is handed to build_chat_history, whose result is
        # forwarded to the stream function as chat_history.
        mock_build.assert_called_once_with(history)
        assert mock_stream.call_args.kwargs["chat_history"] is mock_build.return_value
