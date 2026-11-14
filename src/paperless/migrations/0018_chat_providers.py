from django.db import migrations
from django.db import models


class Migration(migrations.Migration):
    dependencies = [("paperless", "0017_merge_fork_ai_configuration")]
    operations = [
        migrations.AddField(
            model_name="applicationconfiguration",
            name="chat_openai_api_key",
            field=models.CharField(blank=True, null=True, max_length=1024),
        ),
        migrations.AddField(
            model_name="applicationconfiguration",
            name="chat_openai_models",
            field=models.CharField(blank=True, null=True, max_length=2048),
        ),
        migrations.AddField(
            model_name="applicationconfiguration",
            name="chat_anthropic_api_key",
            field=models.CharField(blank=True, null=True, max_length=1024),
        ),
        migrations.AddField(
            model_name="applicationconfiguration",
            name="chat_anthropic_models",
            field=models.CharField(blank=True, null=True, max_length=2048),
        ),
        migrations.AddField(
            model_name="applicationconfiguration",
            name="chat_mistral_api_key",
            field=models.CharField(blank=True, null=True, max_length=1024),
        ),
        migrations.AddField(
            model_name="applicationconfiguration",
            name="chat_mistral_models",
            field=models.CharField(blank=True, null=True, max_length=2048),
        ),
    ]
