from __future__ import annotations

from typing import TYPE_CHECKING
from unittest import mock

import pytest
from asgiref.sync import async_to_sync
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework.test import APITestCase

from paperless_testing.factories import UserFactory
from paperless_testing.permissions import grant_global

if TYPE_CHECKING:
    from django.contrib.auth.models import User
    from pytest_mock import MockerFixture


class TestChatStreamingViewInputValidation(APITestCase):
    def setUp(self) -> None:
        super().setUp()
        self.user = UserFactory(username="temp_admin", superuser=True)
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

    def test_answer_is_not_compressed(self) -> None:
        """
        GIVEN:
            - A client that accepts compressed responses
        WHEN:
            - It asks the chat endpoint a question
        THEN:
            - The answer is streamed unencoded, chunk for chunk

        The stream compressors buffer, so a compressed answer arrives in one
        piece. The view cannot opt out by flagging the request: DRF's request
        wrapper proxies reads but keeps writes to itself, so the flag never
        reaches the Django request the middleware sees.
        """
        chunks = [f"token{i} " for i in range(40)]
        with (
            mock.patch(
                "documents.views.AIConfig",
                return_value=self._mock_ai_enabled(),
            ),
            mock.patch(
                "paperless_ai.agent_chat.stream_agentic_chat",
                return_value=iter(chunks),
            ),
        ):
            resp = self.client.post(
                "/api/documents/chat/",
                {"q": "What is in my archive?"},
                format="json",
                HTTP_ACCEPT_ENCODING="gzip, deflate, br, zstd",
            )

        assert resp.status_code == status.HTTP_200_OK
        assert not resp.has_header("Content-Encoding")

        # The chat view streams through an async generator (aiterate_sync_stream).
        async def collect() -> list[bytes]:
            return [chunk async for chunk in resp.streaming_content]

        assert async_to_sync(collect)() == [c.encode() for c in chunks]

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
            mock.patch("paperless_ai.chat.build_chat_history") as mock_build,
            mock.patch("paperless_ai.agent_chat.stream_agentic_chat") as mock_stream,
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


@pytest.mark.django_db
class TestChatStreamingViewUnrestrictedFlag:
    """The document id filter may only be skipped (``unrestricted=True``) for
    an active superuser, never for a regular user -- regardless of what
    permissions that user holds.
    """

    @pytest.fixture
    def mocked_stream_chat(self, mocker: MockerFixture) -> mock.MagicMock:
        """AI enabled, with stream_agentic_chat patched so the view
        never touches the real vector store; returns the patched callable so
        tests can inspect how it was called.
        """
        mocker.patch("documents.views.AIConfig").return_value.ai_enabled = True
        return mocker.patch(
            "paperless_ai.agent_chat.stream_agentic_chat",
            return_value=iter(()),
        )

    @pytest.fixture
    def viewer_client(self, user_client: APIClient, regular_user: User) -> APIClient:
        """The conftest regular-user client, granted the global
        view_document permission -- the minimum ViewDocumentsPermissions
        needs to reach the view at all. Model-level only: says nothing
        about which documents (if any) this user can actually see.
        """
        grant_global(regular_user, "view_document")
        return user_client

    @pytest.mark.parametrize(
        ("client_fixture", "expected_unrestricted"),
        [
            pytest.param("admin_client", True, id="superuser_is_unrestricted"),
            pytest.param("viewer_client", False, id="regular_user_is_restricted"),
        ],
    )
    def test_unrestricted_only_for_superuser(
        self,
        request: pytest.FixtureRequest,
        mocked_stream_chat: mock.MagicMock,
        client_fixture: str,
        *,
        expected_unrestricted: bool,
    ) -> None:
        """
        GIVEN:
            - A superuser, or a regular user holding the global
              view_document permission (but no object-level document access)
        WHEN:
            - They post a chat question with no document_id
        THEN:
            - stream_agentic_chat is called with unrestricted=True
              only for the superuser; the regular user is always
              unrestricted=False, regardless of their permissions
        """
        client: APIClient = request.getfixturevalue(client_fixture)

        client.post(
            "/api/documents/chat/",
            data={"q": "What's in these documents?"},
            format="json",
        )

        assert (
            mocked_stream_chat.call_args.kwargs["unrestricted"] is expected_unrestricted
        )
