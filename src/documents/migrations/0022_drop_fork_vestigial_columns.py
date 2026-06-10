from django.db import migrations


def _drop_vestigial_columns(apps, schema_editor):
    connection = schema_editor.connection
    with connection.cursor() as cursor:
        columns = {
            column.name
            for column in connection.introspection.get_table_description(
                cursor,
                "documents_document",
            )
        }
    for column in ("embedding_index_ids", "ocr_image_count"):
        if column in columns:
            schema_editor.execute(
                "ALTER TABLE documents_document DROP COLUMN "
                + schema_editor.quote_name(column),
            )


class Migration(migrations.Migration):
    """Drop columns left behind by the removed Paperflow fork migrations.

    The fork's v2.x migrations (1066/1067/...) added ``embedding_index_ids`` and
    ``ocr_image_count`` to ``documents_document``. Those migrations have been
    deleted and the model fields removed, but on databases that were already
    running the fork the columns physically remain. Both are NOT NULL without a
    database default, so inserts from the v3 code (which no longer references
    them) would fail.

    This is a pure database operation with no model-state change, so it does not
    show up in ``makemigrations``. The column check makes it a no-op on a fresh
    v3 install where the columns never existed, and keeps the SQL portable
    (SQLite has no ``DROP COLUMN IF EXISTS``).
    """

    dependencies = [
        ("documents", "0021_widen_workflow_integer_fields"),
    ]

    operations = [
        migrations.RunPython(
            _drop_vestigial_columns,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
