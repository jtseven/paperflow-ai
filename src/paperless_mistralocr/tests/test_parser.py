import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from django.test import TestCase

from paperless_mistralocr.parsers import MistralOcrDocumentParser


def _ocr_response(*markdowns: str) -> SimpleNamespace:
    """Build a minimal stand-in for ``mistralai.models.OCRResponse``."""
    return SimpleNamespace(
        pages=[SimpleNamespace(markdown=md) for md in markdowns],
    )


class TestMistralOcrParserScore(TestCase):
    """``score`` drives whether the parser is visible to the registry."""

    def test_score_none_without_api_key(self):
        with mock.patch.dict("os.environ", {}, clear=False):
            import os

            os.environ.pop("PAPERLESS_MISTRAL_API_KEY", None)
            self.assertIsNone(
                MistralOcrDocumentParser.score("application/pdf", "a.pdf"),
            )

    def test_score_none_for_unsupported_mime(self):
        with mock.patch.dict(
            "os.environ",
            {"PAPERLESS_MISTRAL_API_KEY": "key"},
        ):
            self.assertIsNone(
                MistralOcrDocumentParser.score("text/plain", "a.txt"),
            )

    def test_score_value_when_configured(self):
        with mock.patch.dict(
            "os.environ",
            {"PAPERLESS_MISTRAL_API_KEY": "key"},
        ):
            self.assertEqual(
                MistralOcrDocumentParser.score("application/pdf", "a.pdf"),
                30,
            )

    def test_supported_mime_types(self):
        types = MistralOcrDocumentParser.supported_mime_types()
        self.assertIn("application/pdf", types)
        self.assertIn("image/png", types)


class TestMistralOcrParser(TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.parser = MistralOcrDocumentParser(None)
        self.addCleanup(self.parser.__exit__, None, None, None)

    def test_combine_markdown_joins_pages(self):
        response = _ocr_response("Page 1", "Page 2", "Page 3")
        self.assertEqual(
            self.parser._combine_markdown(response),
            "Page 1\n\nPage 2\n\nPage 3",
        )

    def test_combine_markdown_empty(self):
        self.assertEqual(self.parser._combine_markdown(_ocr_response()), "")

    def test_combine_markdown_strips_image_refs(self):
        response = _ocr_response("Text before ![img-0.png](img-0.png) text after")
        self.assertEqual(
            self.parser._combine_markdown(response),
            "Text before  text after",
        )

    @mock.patch.object(MistralOcrDocumentParser, "_call_mistral_api")
    def test_parse_pdf_stores_text(self, mock_call_api):
        mock_call_api.return_value = _ocr_response(
            "# Sample Document\n\nThis is a test document.",
        )

        sample_file = Path(self.tempdir.name) / "sample.pdf"
        sample_file.write_bytes(b"%PDF-1.4 fake")

        self.parser.parse(sample_file, "application/pdf")

        self.assertEqual(
            self.parser.get_text(),
            "# Sample Document\n\nThis is a test document.",
        )
        # PDFs are their own archive copy.
        self.assertIsNone(self.parser.get_archive_path())
        mock_call_api.assert_called_once()

    def test_call_mistral_api_invokes_client(self):
        sample_file = Path(self.tempdir.name) / "sample.pdf"
        sample_file.write_bytes(b"%PDF-1.4 fake")
        self.parser._config.api_key = "test_api_key"
        self.parser._config.model = "mistral-ocr-latest"

        expected = _ocr_response("# Test Document")

        with mock.patch("mistralai.client.Mistral") as mock_mistral:
            client = mock_mistral.return_value.__enter__.return_value
            client.ocr.process.return_value = expected

            result = self.parser._call_mistral_api(
                sample_file,
                "application/pdf",
            )

        self.assertIs(result, expected)
        mock_mistral.assert_called_once_with(api_key="test_api_key")
        client.ocr.process.assert_called_once()
        _, kwargs = client.ocr.process.call_args
        self.assertEqual(kwargs["model"], "mistral-ocr-latest")
