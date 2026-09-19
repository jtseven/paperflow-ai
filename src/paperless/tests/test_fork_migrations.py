from importlib import import_module
from types import SimpleNamespace

import pytest
from django.apps import apps
from django.db import connection
from django.db.migrations.loader import MigrationLoader
from django.db.migrations.recorder import MigrationRecorder

from paperless.models import ApplicationConfiguration


@pytest.mark.django_db
def test_fork_migration_graph_has_one_leaf_per_app():
    loader = MigrationLoader(connection)
    for app in ("paperless", "documents"):
        assert len(loader.graph.leaf_nodes(app)) == 1


@pytest.mark.django_db
def test_upstream_normalization_preserves_fork_explicit_false():
    config, _ = ApplicationConfiguration.objects.get_or_create()
    config.ai_enabled = False
    config.save()
    MigrationRecorder(connection).record_applied(
        "paperless",
        "0013_alter_applicationconfiguration_ai_enabled",
    )
    migration = import_module(
        "paperless.migrations.0016_alter_applicationconfiguration_ai_enabled",
    )
    migration.normalize_ai_enabled(apps, SimpleNamespace(connection=connection))
    config.refresh_from_db()
    assert config.ai_enabled is False


@pytest.mark.django_db
def test_upstream_normalization_still_handles_nonfork_databases():
    config, _ = ApplicationConfiguration.objects.get_or_create()
    config.ai_enabled = False
    config.save()
    MigrationRecorder(connection).record_unapplied(
        "paperless",
        "0013_alter_applicationconfiguration_ai_enabled",
    )
    migration = import_module(
        "paperless.migrations.0016_alter_applicationconfiguration_ai_enabled",
    )
    migration.normalize_ai_enabled(apps, SimpleNamespace(connection=connection))
    config.refresh_from_db()
    assert config.ai_enabled is None
