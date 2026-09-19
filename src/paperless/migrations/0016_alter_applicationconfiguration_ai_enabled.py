from django.db import migrations
from django.db import models


def normalize_ai_enabled(apps, schema_editor):
    from django.db.migrations.recorder import MigrationRecorder

    if (
        MigrationRecorder(schema_editor.connection)
        .migration_qs.filter(
            app="paperless",
            name="0013_alter_applicationconfiguration_ai_enabled",
        )
        .exists()
    ):
        return
    application_configuration = apps.get_model(
        "paperless",
        "ApplicationConfiguration",
    )
    application_configuration.objects.filter(ai_enabled=False).update(ai_enabled=None)


class Migration(migrations.Migration):
    dependencies = [
        ("paperless", "0015_applicationconfiguration_remote_ocr_mode"),
    ]

    operations = [
        migrations.AlterField(
            model_name="applicationconfiguration",
            name="ai_enabled",
            field=models.BooleanField(
                null=True,
                verbose_name="Enables AI features",
            ),
        ),
        migrations.RunPython(normalize_ai_enabled, migrations.RunPython.noop),
    ]
