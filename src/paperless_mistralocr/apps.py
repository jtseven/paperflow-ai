from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class PaperlessMistralOcrConfig(AppConfig):
    name = "paperless_mistralocr"
    verbose_name = _("Paperflow Mistral OCR")

    # The parser ships with the fork and is registered as a built-in in
    # paperless.parsers.registry.ParserRegistry.register_defaults, so no
    # signal wiring or app-level registration is required here.
