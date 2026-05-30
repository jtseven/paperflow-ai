from django.db import migrations


class Migration(migrations.Migration):
    """Drop columns left behind by the removed Paperflow fork migrations.

    The fork's v2.x migrations (1066/1067/...) added ``embedding_index_ids`` and
    ``ocr_image_count`` to ``documents_document``. Those migrations have been
    deleted and the model fields removed, but on databases that were already
    running the fork the columns physically remain. Both are NOT NULL without a
    database default, so inserts from the v3 code (which no longer references
    them) would fail.

    This is a pure database operation with no model-state change, so it does not
    show up in ``makemigrations``. ``DROP COLUMN IF EXISTS`` makes it a no-op on
    a fresh v3 install where the columns never existed.
    """

    dependencies = [
        ("documents", "0021_widen_workflow_integer_fields"),
    ]

    operations = [
        migrations.RunSQL(
            sql=(
                "ALTER TABLE documents_document "
                "DROP COLUMN IF EXISTS embedding_index_ids;"
                "ALTER TABLE documents_document "
                "DROP COLUMN IF EXISTS ocr_image_count;"
            ),
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
