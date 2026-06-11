import pytest
from django.test import override_settings

from paperless.config import BarcodeConfig
from paperless.models import ApplicationConfiguration


@pytest.mark.django_db
@override_settings(CONSUMER_ENABLE_BARCODES=True)
def test_barcodes_inherit_env_when_unset():
    config = ApplicationConfiguration.objects.first()
    config.barcodes_enabled = None
    config.save()
    assert BarcodeConfig().barcodes_enabled is True


@pytest.mark.django_db
@override_settings(CONSUMER_ENABLE_BARCODES=True)
def test_barcodes_can_be_disabled_from_ui_despite_env():
    """Regression: a UI override of False must win over the enabling env var."""
    config = ApplicationConfiguration.objects.first()
    config.barcodes_enabled = False
    config.save()
    assert BarcodeConfig().barcodes_enabled is False


@pytest.mark.django_db
@override_settings(CONSUMER_BARCODE_STRING="ENV-STRING")
def test_barcode_string_override_wins_over_env():
    config = ApplicationConfiguration.objects.first()
    config.barcode_string = "UI-STRING"
    config.save()
    assert BarcodeConfig().barcode_string == "UI-STRING"
