from unittest.mock import patch

import pytest
from django.contrib.auth.models import Permission
from django.contrib.auth.models import User
from django.test import TestCase
from django.test import override_settings

from paperless.config import AIConfig
from paperless.models import ApplicationConfiguration
from paperless.serialisers import ApplicationConfigurationSerializer
from paperless_ai.providers import apply_chat_model
from paperless_ai.providers import available_chat_models
from paperless_ai.providers import parse_models


@override_settings(AI_ENABLED=True, LLM_BACKEND="")
class TestChatProviders(TestCase):
    def setUp(self):
        self.config = ApplicationConfiguration(
            chat_openai_api_key="secret-openai",
            chat_openai_models="model-one, model-two",
            chat_anthropic_api_key="secret-claude",
            chat_anthropic_models="claude-test",
            chat_mistral_models="missing-key",
        )
        self.config.save()
        self.user = User.objects.create_user("chat-user")
        self.user.user_permissions.add(Permission.objects.get(codename="view_document"))
        self.client.force_login(self.user)

    def test_catalog_only_lists_configured_models_without_secrets(self):
        response = self.client.get("/api/documents/chat/models/")
        assert response.status_code == 200
        assert response.json() == {
            "models": [
                {
                    "id": "openai:model-one",
                    "provider": "OpenAI (ChatGPT)",
                    "name": "model-one",
                },
                {
                    "id": "openai:model-two",
                    "provider": "OpenAI (ChatGPT)",
                    "name": "model-two",
                },
                {
                    "id": "anthropic:claude-test",
                    "provider": "Anthropic (Claude)",
                    "name": "claude-test",
                },
            ],
            "default_model": "openai:model-one",
        }
        assert "secret" not in response.content.decode()

    def test_catalog_requires_permission(self):
        self.user.user_permissions.clear()
        assert self.client.get("/api/documents/chat/models/").status_code == 403

    def test_selection_uses_server_credentials(self):
        config = AIConfig()
        apply_chat_model(config, "anthropic:claude-test")
        assert config.llm_api_key == "secret-claude"
        assert config.llm_model == "claude-test"
        assert config.llm_endpoint == "https://api.anthropic.com/v1"
        with pytest.raises(ValueError):
            apply_chat_model(AIConfig(), "mistral:missing-key")

    def test_secrets_masked_and_preserved_on_edit_and_can_be_cleared(self):
        data = ApplicationConfigurationSerializer(self.config).data
        assert data["chat_openai_api_key"] != "secret-openai"
        serializer = ApplicationConfigurationSerializer(
            self.config,
            data={
                "chat_openai_api_key": data["chat_openai_api_key"],
                "chat_openai_models": "model-two, model-two",
            },
            partial=True,
        )
        assert serializer.is_valid(), serializer.errors
        saved = serializer.save()
        assert saved.chat_openai_api_key == "secret-openai"
        assert saved.chat_openai_models == "model-two"
        serializer = ApplicationConfigurationSerializer(
            saved,
            data={"chat_openai_api_key": ""},
            partial=True,
        )
        assert serializer.is_valid(), serializer.errors
        serializer.save()
        assert all(
            not item["id"].startswith("openai:")
            for item in available_chat_models()["models"]
        )

    def test_rejects_unknown_model_before_streaming(self):
        response = self.client.post(
            "/api/documents/chat/",
            {"q": "hello", "model": "openai:unapproved"},
            content_type="application/json",
        )
        assert response.status_code == 400
        assert "model" in response.json()

    @patch("paperless_ai.agent_chat.stream_agentic_chat", return_value=iter([]))
    def test_selected_model_forwarded_to_agent(self, stream):
        response = self.client.post(
            "/api/documents/chat/",
            {"q": "hello", "model": "anthropic:claude-test"},
            content_type="application/json",
        )
        assert response.status_code == 200
        assert stream.call_args.kwargs["model"] == "anthropic:claude-test"

    @override_settings(AI_ENABLED=False)
    def test_disabled_ai_has_empty_catalog(self):
        assert available_chat_models() == {"models": [], "default_model": None}


def test_model_ids_are_normalized_and_validated():
    assert parse_models(" first-model, second/model, first-model ") == [
        "first-model",
        "second/model",
    ]
    with pytest.raises(ValueError):
        parse_models("bad model")


@pytest.mark.django_db
@pytest.mark.parametrize("provider", ["openai", "anthropic", "mistral"])
@override_settings(AI_ENABLED=True)
def test_provider_client_uses_selected_endpoint_and_key(provider):
    from paperless_ai.client import AIClient
    from paperless_ai.providers import PROVIDERS

    app = ApplicationConfiguration()
    setattr(app, f"chat_{provider}_api_key", "test-provider-key")
    setattr(app, f"chat_{provider}_models", "test-model")
    app.save()
    with (
        patch("llama_index.llms.openai_like.OpenAILike") as llm,
        patch("paperless_ai.client.create_pinned_httpx_client"),
        patch("paperless_ai.client.create_pinned_async_httpx_client"),
        patch("paperless_ai.openai_compat.CompatibleOpenAI") as sdk,
        patch("paperless_ai.openai_compat.CompatibleAsyncOpenAI") as async_sdk,
    ):
        AIClient(model=f"{provider}:test-model")
    assert llm.call_args.kwargs["model"] == "test-model"
    assert llm.call_args.kwargs["api_key"] == "test-provider-key"
    assert llm.call_args.kwargs["api_base"] == PROVIDERS[provider][1]
    assert llm.call_args.kwargs["is_function_calling_model"] is True
    for client in (sdk, async_sdk):
        assert client.call_args.kwargs["api_key"] == "test-provider-key"
        assert client.call_args.kwargs["base_url"] == PROVIDERS[provider][1]
