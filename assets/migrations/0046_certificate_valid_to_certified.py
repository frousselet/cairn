"""Data migration: remap legacy ``valid`` certificates to ``certified``.

The certificate lifecycle gained an Assessment stage and renamed ``valid`` (the
in-force state) to ``certified``. Certificates created before that change carry
``status`` / ``workflow_state`` = ``valid``, which is no longer a lifecycle
step, so the lifecycle stepper cannot locate the current state and renders every
node inactive / unclickable. Remap them to ``certified`` (both fields, plus the
history rows). A no-op on fresh installs (no ``valid`` rows ever written).
"""

from django.db import migrations


def valid_to_certified(apps, schema_editor):
    Certificate = apps.get_model("assets", "Certificate")
    Certificate.objects.filter(status="valid").update(status="certified")
    Certificate.objects.filter(workflow_state="valid").update(workflow_state="certified")

    Historical = apps.get_model("assets", "HistoricalCertificate")
    Historical.objects.filter(status="valid").update(status="certified")
    Historical.objects.filter(workflow_state="valid").update(workflow_state="certified")


def certified_to_valid(apps, schema_editor):
    Certificate = apps.get_model("assets", "Certificate")
    Certificate.objects.filter(status="certified").update(status="valid")
    Certificate.objects.filter(workflow_state="certified").update(workflow_state="valid")

    Historical = apps.get_model("assets", "HistoricalCertificate")
    Historical.objects.filter(status="certified").update(status="valid")
    Historical.objects.filter(workflow_state="certified").update(workflow_state="valid")


class Migration(migrations.Migration):

    dependencies = [
        ("assets", "0045_alter_certificate_status_and_more"),
    ]

    operations = [
        migrations.RunPython(valid_to_certified, certified_to_valid),
    ]
