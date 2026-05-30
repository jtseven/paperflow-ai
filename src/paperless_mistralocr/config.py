import dataclasses
import os

from paperless.config import OutputTypeConfig


@dataclasses.dataclass
class MistralOcrConfig(OutputTypeConfig):
    """
    Configuration for the Mistral OCR API.

    ``output_type`` (the PDF/A variant used for generated archives) is
    inherited from :class:`paperless.config.OutputTypeConfig`. The API key and
    model are read from the environment so the parser can score itself out
    cheaply when no key is configured.
    """

    api_key: str = dataclasses.field(init=False)
    model: str = dataclasses.field(init=False)

    def __post_init__(self) -> None:
        super().__post_init__()

        self.api_key = os.getenv("PAPERLESS_MISTRAL_API_KEY", "")
        self.model = os.getenv("PAPERLESS_MISTRAL_MODEL", "mistral-ocr-latest")
