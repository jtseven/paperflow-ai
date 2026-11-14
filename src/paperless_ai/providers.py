"""Server-managed chat providers. Public model catalogs never include credentials."""

import re

from paperless.config import AIConfig
from paperless.models import ApplicationConfiguration
from paperless.models import LLMBackend

PROVIDERS = {
    "openai": ("OpenAI (ChatGPT)", "https://api.openai.com/v1"),
    "anthropic": ("Anthropic (Claude)", "https://api.anthropic.com/v1"),
    "mistral": ("Mistral", "https://api.mistral.ai/v1"),
}


def parse_models(value: str) -> list[str]:
    models = list(dict.fromkeys(x.strip() for x in value.split(",") if x.strip()))
    if len(models) > 30 or any(
        not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._/-]{0,127}", model)
        for model in models
    ):
        raise ValueError(
            "Enter up to 30 comma-separated model IDs (letters, digits, ., _, /, -).",
        )
    return models


def available_chat_models(config: AIConfig | None = None) -> dict:
    config = config or AIConfig()
    models = []
    if config.ai_enabled:
        if config.llm_backend:
            models.append(
                {
                    "id": "default",
                    "provider": "Configured backend",
                    "name": config.llm_model or "Default model",
                },
            )
        app = ApplicationConfiguration.objects.order_by("id").first()
        if app:
            for provider, (label, _) in PROVIDERS.items():
                if not getattr(app, f"chat_{provider}_api_key"):
                    continue
                for model in parse_models(
                    getattr(app, f"chat_{provider}_models") or "",
                ):
                    models.append(
                        {"id": f"{provider}:{model}", "provider": label, "name": model},
                    )
    return {"models": models, "default_model": models[0]["id"] if models else None}


def apply_chat_model(config: AIConfig, selection: str) -> None:
    """Resolve only administrator-allowed models; never accept a client endpoint/key."""
    if selection not in {
        item["id"] for item in available_chat_models(config)["models"]
    }:
        raise ValueError(
            "This chat model is no longer available. Refresh the model list.",
        )
    if selection == "default":
        return
    provider, model = selection.split(":", 1)
    app = ApplicationConfiguration.objects.order_by("id").first()
    config.llm_backend = LLMBackend.OPENAI_LIKE
    config.llm_model = model
    config.llm_endpoint = PROVIDERS[provider][1]
    config.llm_api_key = getattr(app, f"chat_{provider}_api_key")
