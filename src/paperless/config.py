import dataclasses
import json
from typing import Any

from django.conf import settings

from paperless.models import ApplicationConfiguration
from paperless.models import ArchiveFileGenerationChoices
from paperless.models import CleanChoices
from paperless.models import ColorConvertChoices
from paperless.models import ModeChoices
from paperless.models import OutputTypeChoices

# Single source of truth pairing each ApplicationConfiguration model field with
# the Django settings attribute (env var / paperless.conf / built-in default)
# it falls back to when the field has no UI override. Used both to resolve the
# effective configuration and to expose the inherited fallbacks to the frontend
# (see get_configuration_defaults), so admins can see values sourced from the
# environment even when nothing is stored in the database.
CONFIG_SETTINGS_MAP: dict[str, str] = {
    # General / output
    "output_type": "OCR_OUTPUT_TYPE",
    # OCR
    "pages": "OCR_PAGES",
    "language": "OCR_LANGUAGE",
    "mode": "OCR_MODE",
    "archive_file_generation": "ARCHIVE_FILE_GENERATION",
    "image_dpi": "OCR_IMAGE_DPI",
    "unpaper_clean": "OCR_CLEAN",
    "deskew": "OCR_DESKEW",
    "rotate_pages": "OCR_ROTATE_PAGES",
    "rotate_pages_threshold": "OCR_ROTATE_PAGES_THRESHOLD",
    "max_image_pixels": "OCR_MAX_IMAGE_PIXELS",
    "color_conversion_strategy": "OCR_COLOR_CONVERSION_STRATEGY",
    "user_args": "OCR_USER_ARGS",
    # Barcode
    "barcodes_enabled": "CONSUMER_ENABLE_BARCODES",
    "barcode_enable_tiff_support": "CONSUMER_BARCODE_TIFF_SUPPORT",
    "barcode_string": "CONSUMER_BARCODE_STRING",
    "barcode_retain_split_pages": "CONSUMER_BARCODE_RETAIN_SPLIT_PAGES",
    "barcode_enable_asn": "CONSUMER_ENABLE_ASN_BARCODE",
    "barcode_asn_prefix": "CONSUMER_ASN_BARCODE_PREFIX",
    "barcode_upscale": "CONSUMER_BARCODE_UPSCALE",
    "barcode_dpi": "CONSUMER_BARCODE_DPI",
    "barcode_max_pages": "CONSUMER_BARCODE_MAX_PAGES",
    "barcode_enable_tag": "CONSUMER_ENABLE_TAG_BARCODE",
    "barcode_tag_mapping": "CONSUMER_TAG_BARCODE_MAPPING",
    "barcode_tag_split": "CONSUMER_TAG_BARCODE_SPLIT",
    # AI
    "ai_enabled": "AI_ENABLED",
    "llm_embedding_backend": "LLM_EMBEDDING_BACKEND",
    "llm_embedding_model": "LLM_EMBEDDING_MODEL",
    "llm_embedding_endpoint": "LLM_EMBEDDING_ENDPOINT",
    "llm_embedding_chunk_size": "LLM_EMBEDDING_CHUNK_SIZE",
    "llm_context_size": "LLM_CONTEXT_SIZE",
    "llm_backend": "LLM_BACKEND",
    "llm_model": "LLM_MODEL",
    "llm_api_key": "LLM_API_KEY",
    "llm_endpoint": "LLM_ENDPOINT",
    "llm_output_language": "LLM_OUTPUT_LANGUAGE",
}

# Fields whose inherited value must never be exposed verbatim to the frontend.
_SECRET_CONFIG_FIELDS = frozenset({"llm_api_key"})
_SECRET_PLACEHOLDER = "********"


def _coalesce(db_value: Any, settings_value: Any) -> Any:
    """Resolve a config value: an explicit UI override wins, else the fallback.

    ``None`` and ``""`` both mean "not set in the UI — inherit from the
    environment". Unlike a plain ``or``, this preserves a deliberately falsy
    override (e.g. a boolean toggled *off*), so a setting enabled by an
    environment variable can still be disabled from the UI.
    """
    if db_value is None or db_value == "":
        return settings_value
    return db_value


def get_configuration_defaults() -> dict[str, Any]:
    """Return the inherited (env / config-file / built-in) value per field.

    These are the values that apply when a field has no database override. The
    frontend shows them as placeholders so the configuration panel reflects
    values sourced from the environment. Secrets are masked, never returned.
    """
    defaults: dict[str, Any] = {
        field: getattr(settings, settings_attr, None)
        for field, settings_attr in CONFIG_SETTINGS_MAP.items()
    }
    for field in _SECRET_CONFIG_FIELDS:
        if defaults.get(field):
            defaults[field] = _SECRET_PLACEHOLDER
    return defaults


@dataclasses.dataclass
class BaseConfig:
    """
    Almost all parsers care about the chosen PDF output format
    """

    @staticmethod
    def _get_config_instance() -> ApplicationConfiguration:
        app_config = ApplicationConfiguration.objects.all().first()
        # Workaround for a test where the migration hasn't run to create the single model
        if app_config is None:
            ApplicationConfiguration.objects.create()
            app_config = ApplicationConfiguration.objects.all().first()
        return app_config


@dataclasses.dataclass
class OutputTypeConfig(BaseConfig):
    """
    Almost all parsers care about the chosen PDF output format
    """

    output_type: OutputTypeChoices = dataclasses.field(init=False)

    def __post_init__(self) -> None:
        app_config = self._get_config_instance()

        self.output_type = app_config.output_type or OutputTypeChoices(
            settings.OCR_OUTPUT_TYPE,
        )


@dataclasses.dataclass
class OcrConfig(OutputTypeConfig):
    """
    Specific settings for the Tesseract based parser.  Options generally
    correspond almost directly to the OCRMyPDF options
    """

    pages: int | None = dataclasses.field(init=False)
    language: str = dataclasses.field(init=False)
    mode: ModeChoices = dataclasses.field(init=False)
    archive_file_generation: ArchiveFileGenerationChoices = dataclasses.field(
        init=False,
    )
    image_dpi: int | None = dataclasses.field(init=False)
    clean: CleanChoices = dataclasses.field(init=False)
    deskew: bool = dataclasses.field(init=False)
    rotate: bool = dataclasses.field(init=False)
    rotate_threshold: float = dataclasses.field(init=False)
    max_image_pixel: float | None = dataclasses.field(init=False)
    color_conversion_strategy: ColorConvertChoices = dataclasses.field(init=False)
    user_args: dict[str, str] | None = dataclasses.field(init=False)

    def __post_init__(self) -> None:
        super().__post_init__()

        app_config = self._get_config_instance()

        self.pages = app_config.pages or settings.OCR_PAGES
        self.language = app_config.language or settings.OCR_LANGUAGE
        self.mode = app_config.mode or ModeChoices(settings.OCR_MODE)
        self.archive_file_generation = (
            app_config.archive_file_generation
            or ArchiveFileGenerationChoices(settings.ARCHIVE_FILE_GENERATION)
        )
        self.image_dpi = app_config.image_dpi or settings.OCR_IMAGE_DPI
        self.clean = app_config.unpaper_clean or CleanChoices(settings.OCR_CLEAN)
        self.deskew = (
            app_config.deskew if app_config.deskew is not None else settings.OCR_DESKEW
        )
        self.rotate = (
            app_config.rotate_pages
            if app_config.rotate_pages is not None
            else settings.OCR_ROTATE_PAGES
        )
        self.rotate_threshold = (
            app_config.rotate_pages_threshold or settings.OCR_ROTATE_PAGES_THRESHOLD
        )
        self.max_image_pixel = (
            app_config.max_image_pixels or settings.OCR_MAX_IMAGE_PIXELS
        )
        self.color_conversion_strategy = (
            app_config.color_conversion_strategy
            or ColorConvertChoices(settings.OCR_COLOR_CONVERSION_STRATEGY)
        )

        user_args = None
        if app_config.user_args:
            user_args = app_config.user_args
        elif settings.OCR_USER_ARGS is not None:  # pragma: no cover
            try:
                user_args = json.loads(settings.OCR_USER_ARGS)
            except json.JSONDecodeError:
                user_args = {}
        self.user_args = user_args


@dataclasses.dataclass
class BarcodeConfig(BaseConfig):
    """
    Barcodes settings
    """

    barcodes_enabled: bool = dataclasses.field(init=False)
    barcode_enable_tiff_support: bool = dataclasses.field(init=False)
    barcode_string: str = dataclasses.field(init=False)
    barcode_retain_split_pages: bool = dataclasses.field(init=False)
    barcode_enable_asn: bool = dataclasses.field(init=False)
    barcode_asn_prefix: str = dataclasses.field(init=False)
    barcode_upscale: float = dataclasses.field(init=False)
    barcode_dpi: int = dataclasses.field(init=False)
    barcode_max_pages: int = dataclasses.field(init=False)
    barcode_enable_tag: bool = dataclasses.field(init=False)
    barcode_tag_mapping: dict[str, str] = dataclasses.field(init=False)
    barcode_tag_split: bool = dataclasses.field(init=False)

    def __post_init__(self) -> None:
        app_config = self._get_config_instance()

        self.barcodes_enabled = (
            app_config.barcodes_enabled or settings.CONSUMER_ENABLE_BARCODES
        )
        self.barcode_enable_tiff_support = (
            app_config.barcode_enable_tiff_support
            or settings.CONSUMER_BARCODE_TIFF_SUPPORT
        )
        self.barcode_string = (
            app_config.barcode_string or settings.CONSUMER_BARCODE_STRING
        )
        self.barcode_retain_split_pages = (
            app_config.barcode_retain_split_pages
            or settings.CONSUMER_BARCODE_RETAIN_SPLIT_PAGES
        )
        self.barcode_enable_asn = (
            app_config.barcode_enable_asn or settings.CONSUMER_ENABLE_ASN_BARCODE
        )
        self.barcode_asn_prefix = (
            app_config.barcode_asn_prefix or settings.CONSUMER_ASN_BARCODE_PREFIX
        )
        self.barcode_upscale = (
            app_config.barcode_upscale or settings.CONSUMER_BARCODE_UPSCALE
        )
        self.barcode_dpi = app_config.barcode_dpi or settings.CONSUMER_BARCODE_DPI
        self.barcode_max_pages = (
            app_config.barcode_max_pages or settings.CONSUMER_BARCODE_MAX_PAGES
        )
        self.barcode_enable_tag = (
            app_config.barcode_enable_tag or settings.CONSUMER_ENABLE_TAG_BARCODE
        )
        self.barcode_tag_mapping = (
            app_config.barcode_tag_mapping or settings.CONSUMER_TAG_BARCODE_MAPPING
        )
        self.barcode_tag_split = (
            app_config.barcode_tag_split or settings.CONSUMER_TAG_BARCODE_SPLIT
        )


@dataclasses.dataclass
class GeneralConfig(BaseConfig):
    """
    General application settings that require global scope
    """

    app_title: str = dataclasses.field(init=False)
    app_logo: str = dataclasses.field(init=False)

    def __post_init__(self) -> None:
        app_config = self._get_config_instance()

        self.app_title = app_config.app_title or None
        self.app_logo = app_config.app_logo.url if app_config.app_logo else None


@dataclasses.dataclass
class AIConfig(BaseConfig):
    """
    AI related settings that require global scope
    """

    ai_enabled: bool = dataclasses.field(init=False)
    llm_embedding_backend: str = dataclasses.field(init=False)
    llm_embedding_model: str = dataclasses.field(init=False)
    llm_embedding_endpoint: str = dataclasses.field(init=False)
    llm_embedding_chunk_size: int = dataclasses.field(init=False)
    llm_context_size: int = dataclasses.field(init=False)
    llm_backend: str = dataclasses.field(init=False)
    llm_model: str = dataclasses.field(init=False)
    llm_api_key: str = dataclasses.field(init=False)
    llm_endpoint: str = dataclasses.field(init=False)
    llm_output_language: str = dataclasses.field(init=False)
    llm_allow_internal_endpoints: bool = dataclasses.field(init=False)

    # The AI fields all resolve the same way (DB override → settings fallback)
    # and map 1:1 onto CONFIG_SETTINGS_MAP, so resolve them in a loop. Using
    # _coalesce (rather than ``or``) means ai_enabled toggled off in the UI is
    # honoured even when AI_ENABLED is set in the environment.
    _FIELDS = (
        "ai_enabled",
        "llm_embedding_backend",
        "llm_embedding_model",
        "llm_embedding_endpoint",
        "llm_embedding_chunk_size",
        "llm_context_size",
        "llm_backend",
        "llm_model",
        "llm_api_key",
        "llm_endpoint",
        "llm_output_language",
    )

    def __post_init__(self) -> None:
        app_config = self._get_config_instance()

        for field in self._FIELDS:
            setattr(
                self,
                field,
                _coalesce(
                    getattr(app_config, field),
                    getattr(settings, CONFIG_SETTINGS_MAP[field]),
                ),
            )
        self.llm_allow_internal_endpoints = settings.LLM_ALLOW_INTERNAL_ENDPOINTS

    @property
    def llm_index_enabled(self) -> bool:
        return bool(self.ai_enabled and self.llm_embedding_backend)
