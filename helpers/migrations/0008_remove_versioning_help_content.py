from django.db import migrations


def remove_versioning_help(apps, schema_editor):
    """Drop the help banner for the removed Versioning configuration page."""
    HelpContent = apps.get_model("helpers", "HelpContent")
    HelpContent.objects.filter(key="core.versioning_config_list").delete()


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("helpers", "0007_complete_helper_content"),
    ]

    operations = [
        migrations.RunPython(remove_versioning_help, noop),
    ]
