import pytest
from django.test import override_settings

from paperless.config import AIConfig
from paperless.config import _coalesce
from paperless.config import get_configuration_defaults
from paperless.models import ApplicationConfiguration


def test_coalesce_prefers_explicit_override():
    # An explicit value wins, including a deliberately falsy one.
    enabled, disabled = True, False
    assert _coalesce("db", "env") == "db"
    assert _coalesce(disabled, enabled) is False
    assert _coalesce(0, 5) == 0


def test_coalesce_inherits_when_unset():
    # None and "" both mean "inherit from the environment".
    assert _coalesce(None, "env") == "env"
    assert _coalesce("", "env") == "env"


@pytest.mark.django_db
@override_settings(AI_ENABLED=True)
def test_ai_enabled_inherits_env_when_unset():
    config, _ = ApplicationConfiguration.objects.get_or_create()
    config.ai_enabled = None
    config.save()
    assert AIConfig().ai_enabled is True


@pytest.mark.django_db
@override_settings(AI_ENABLED=True)
def test_ai_can_be_disabled_from_ui_despite_env():
    """Regression: a UI override of False must win over AI_ENABLED=True."""
    config, _ = ApplicationConfiguration.objects.get_or_create()
    config.ai_enabled = False
    config.save()
    assert AIConfig().ai_enabled is False


@pytest.mark.django_db
@override_settings(
    LLM_BACKEND="openai-like",
    LLM_MODEL="env-model",
    LLM_API_KEY="secret",
)
def test_ai_string_override_wins_over_env():
    config, _ = ApplicationConfiguration.objects.get_or_create()
    config.llm_model = "ui-model"
    config.save()
    cfg = AIConfig()
    assert cfg.llm_model == "ui-model"
    # Untouched field still inherits the environment value.
    assert cfg.llm_backend == "openai-like"


@pytest.mark.django_db
@override_settings(
    LLM_BACKEND="openai-like",
    LLM_MODEL="env-model",
    LLM_API_KEY="super-secret",
    AI_ENABLED=True,
)
def test_get_configuration_defaults_masks_secret():
    defaults = get_configuration_defaults()
    assert defaults["llm_backend"] == "openai-like"
    assert defaults["llm_model"] == "env-model"
    assert defaults["ai_enabled"] is True
    # The API key is masked, never returned verbatim.
    assert defaults["llm_api_key"] == "********"


@pytest.mark.django_db
@override_settings(LLM_API_KEY="")
def test_get_configuration_defaults_no_key_is_unmasked_empty():
    defaults = get_configuration_defaults()
    assert defaults["llm_api_key"] == ""
