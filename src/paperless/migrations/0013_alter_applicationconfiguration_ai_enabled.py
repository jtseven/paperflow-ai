from django.db import migrations
from django.db import models


def reset_default_ai_enabled_to_null(apps, schema_editor):
    """Treat the old ``default=False`` as "unset" so it inherits the env.

    ``ai_enabled`` previously defaulted to ``False`` and was merged with a plain
    ``or``, so a stored ``False`` could never override an environment that
    enabled AI — it was indistinguishable from "not configured". Now that the
    resolver honours an explicit ``False``, migrate those rows to ``NULL`` so
    they keep inheriting the environment value rather than force-disabling AI.
    """
    ApplicationConfiguration = apps.get_model("paperless", "ApplicationConfiguration")
    ApplicationConfiguration.objects.filter(ai_enabled=False).update(ai_enabled=None)


class Migration(migrations.Migration):
    dependencies = [
        ("paperless", "0012_applicationconfiguration_llm_output_language"),
    ]

    operations = [
        migrations.AlterField(
            model_name="applicationconfiguration",
            name="ai_enabled",
            field=models.BooleanField(null=True, verbose_name="Enables AI features"),
        ),
        migrations.RunPython(
            reset_default_ai_enabled_to_null,
            migrations.RunPython.noop,
        ),
    ]
