"""
Mistral OCR document parser.

Sends documents to Mistral AI's OCR API and stores the extracted markdown as
the document's text content. PDFs are kept as-is (the original is the archive
copy); images are converted to a PDF archive so they remain viewable.

When no ``PAPERLESS_MISTRAL_API_KEY`` is configured, ``score()`` returns
``None`` so the parser is invisible to the registry and the built-in Tesseract
parser handles the file instead.

The parser ships with the fork and is registered as a built-in in
``paperless.parsers.registry.ParserRegistry.register_defaults``.
"""

from __future__ import annotations

import base64
import logging
import os
import re
import shutil
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Self

from django.conf import settings

from documents.parsers import ParseError
from documents.parsers import make_thumbnail_from_pdf
from documents.utils import run_subprocess

if TYPE_CHECKING:
    import datetime
    from types import TracebackType

    from mistralai.client.models import OCRResponse

    from paperless.parsers import MetadataEntry
    from paperless.parsers import ParserContext

logger = logging.getLogger("paperless.parsing.mistral_ocr")

_IMAGE_MIME_TYPES: dict[str, str] = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/tiff": ".tif",
    "image/gif": ".gif",
    "image/bmp": ".bmp",
    "image/webp": ".webp",
}

_SUPPORTED_MIME_TYPES: dict[str, str] = {
    "application/pdf": ".pdf",
    **_IMAGE_MIME_TYPES,
}

# Markdown image references emitted by the OCR API, e.g. ``![img-0.png](img-0.png)``.
_OCR_IMAGE_REF_REGEX = re.compile(r"!\[[^\]]*\]\([^)]*\)")

_MAX_FILE_SIZE = 50 * 1024 * 1024  # Mistral API hard limit


class MistralOcrDocumentParser:
    """Parse documents via Mistral AI's OCR API.

    Class attributes
    ----------------
    name, version, author, url : str
        Attribution metadata read by the parser registry without
        instantiating the parser.
    """

    name: str = "Paperflow Mistral OCR Parser"
    version: str = "2.0.0"
    author: str = "Paperflow AI"
    url: str = "https://github.com/jtseven/paperflow-ai"

    # ------------------------------------------------------------------
    # Class methods
    # ------------------------------------------------------------------

    @classmethod
    def supported_mime_types(cls) -> dict[str, str]:
        """Return the MIME types this parser handles.

        The full set is always returned; ``score()`` handles the
        "am I active?" logic by returning ``None`` when no API key is set.
        """
        return _SUPPORTED_MIME_TYPES

    @classmethod
    def score(
        cls,
        mime_type: str,
        filename: str,
        path: Path | None = None,
    ) -> int | None:
        """Return the priority score for handling this file, or ``None``.

        Returns ``None`` when no API key is configured (parser invisible to
        the registry) or the ``mistralai`` package is unavailable. When
        configured, returns 30 — higher than Tesseract (10) and the remote
        OCR parser (20) — so Mistral OCR takes priority.
        """
        if mime_type not in _SUPPORTED_MIME_TYPES:
            return None
        if not os.getenv("PAPERLESS_MISTRAL_API_KEY"):
            return None
        try:
            import mistralai  # noqa: F401
        except ImportError:
            logger.warning(
                "PAPERLESS_MISTRAL_API_KEY is set but the 'mistralai' package "
                "is not installed; Mistral OCR is disabled.",
            )
            return None
        return 30

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def can_produce_archive(self) -> bool:
        """Image inputs are converted to a PDF archive; PDFs keep the original."""
        return True

    @property
    def requires_pdf_rendition(self) -> bool:
        """All supported originals are displayable (PDF) or archived (images)."""
        return False

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def __init__(self, logging_group: object = None) -> None:
        from paperless_mistralocr.config import MistralOcrConfig

        settings.SCRATCH_DIR.mkdir(parents=True, exist_ok=True)
        self._tempdir = Path(
            tempfile.mkdtemp(prefix="paperless-", dir=settings.SCRATCH_DIR),
        )
        self._logging_group = logging_group
        self._config = MistralOcrConfig()
        self._text: str | None = None
        self._date: datetime.datetime | None = None
        self._archive_path: Path | None = None

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        logger.debug("Cleaning up temporary directory %s", self._tempdir)
        shutil.rmtree(self._tempdir, ignore_errors=True)

    # ------------------------------------------------------------------
    # Core parsing interface
    # ------------------------------------------------------------------

    def configure(self, context: ParserContext) -> None:
        pass

    def parse(
        self,
        document_path: Path,
        mime_type: str,
        *,
        produce_archive: bool = True,
    ) -> None:
        """Send the document to Mistral OCR and store the extracted markdown.

        For non-PDF inputs an archive PDF is generated so the original remains
        viewable in the frontend.
        """
        logger.info("Parsing %s with the Mistral OCR API", document_path)

        ocr_response = self._call_mistral_api(document_path, mime_type)
        self._text = self._combine_markdown(ocr_response)

        # Date extraction is handled by the consumer's date-parser plugin when
        # get_date() returns None, mirroring upstream's built-in parsers.

        if mime_type != "application/pdf" and produce_archive:
            self._archive_path = self._convert_image_to_pdf(document_path)

    # ------------------------------------------------------------------
    # Result accessors
    # ------------------------------------------------------------------

    def get_text(self) -> str:
        return self._text or ""

    def get_date(self) -> datetime.datetime | None:
        return self._date

    def get_archive_path(self) -> Path | None:
        return self._archive_path

    # ------------------------------------------------------------------
    # Thumbnail, page count and metadata
    # ------------------------------------------------------------------

    def get_thumbnail(self, document_path: Path, mime_type: str) -> Path:
        """Render a WebP thumbnail from the PDF (original or generated archive)."""
        if mime_type == "application/pdf":
            return make_thumbnail_from_pdf(
                document_path,
                self._tempdir,
                self._logging_group,
            )
        if self._archive_path is None:
            self._archive_path = self._convert_image_to_pdf(document_path)
        return make_thumbnail_from_pdf(
            self._archive_path,
            self._tempdir,
            self._logging_group,
        )

    def get_page_count(
        self,
        document_path: Path,
        mime_type: str,
    ) -> int | None:
        if mime_type != "application/pdf":
            return None
        from paperless.parsers.utils import get_page_count_for_pdf

        return get_page_count_for_pdf(document_path, log=logger)

    def extract_metadata(
        self,
        document_path: Path,
        mime_type: str,
    ) -> list[MetadataEntry]:
        if mime_type != "application/pdf":
            return []
        from paperless.parsers.utils import extract_pdf_metadata

        return extract_pdf_metadata(document_path, log=logger)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _call_mistral_api(self, document_path: Path, mime_type: str) -> OCRResponse:
        """Call the Mistral OCR API and return the raw response."""
        from mistralai.client import Mistral
        from mistralai.client.models import DocumentURLChunk
        from mistralai.client.models import ImageURLChunk

        api_key = self._config.api_key
        if not api_key:
            raise ParseError(
                "Mistral API key not configured. Set PAPERLESS_MISTRAL_API_KEY.",
            )

        file_size = document_path.stat().st_size
        if file_size > _MAX_FILE_SIZE:
            raise ParseError(
                f"File too large for the Mistral API: "
                f"{file_size / (1024 * 1024):.2f}MB (max 50MB)",
            )

        is_image = mime_type in _IMAGE_MIME_TYPES
        file_base64 = base64.b64encode(document_path.read_bytes()).decode("utf-8")
        data_uri = (
            f"data:{mime_type};base64,{file_base64}"
            if is_image
            else f"data:application/pdf;base64,{file_base64}"
        )
        document = (
            ImageURLChunk(image_url=data_uri)
            if is_image
            else DocumentURLChunk(document_url=data_uri)
        )

        try:
            with Mistral(api_key=api_key) as client:
                return client.ocr.process(
                    model=self._config.model,
                    document=document,
                    include_image_base64=False,
                )
        except ParseError:
            raise
        except Exception as e:
            raise ParseError(f"Error calling the Mistral OCR API: {e!s}") from e

    def _combine_markdown(self, ocr_response: OCRResponse) -> str:
        """Join per-page markdown, stripping inline image references.

        Image references are removed rather than persisted: the document
        content feeds the search index and the LLM index, where embedded
        image data would be noise.
        """
        pages = [
            _OCR_IMAGE_REF_REGEX.sub("", page.markdown).strip()
            for page in ocr_response.pages
        ]
        return "\n\n".join(p for p in pages if p)

    def _convert_image_to_pdf(self, document_path: Path) -> Path:
        """Convert an image to a single-page PDF archive via ImageMagick."""
        pdf_path = self._tempdir / "archive.pdf"
        try:
            run_subprocess(
                [
                    settings.CONVERT_BINARY,
                    str(document_path),
                    str(pdf_path),
                ],
                logger=logger,
            )
        except Exception as e:
            raise ParseError(f"Error converting image to PDF: {e!s}") from e
        return pdf_path
