"""Seed the new SupplierContact rows from the legacy single-contact fields.

Each supplier that carried a contact name / email / phone gets one
SupplierContact created. The legacy ``contact_*`` columns are left in place for
now (retired once contact editing moves to the contacts CRUD).
"""

from django.db import migrations


def seed_contacts(apps, schema_editor):
    Supplier = apps.get_model("assets", "Supplier")
    SupplierContact = apps.get_model("assets", "SupplierContact")
    for s in Supplier.objects.all():
        if not (s.contact_name or s.contact_email or s.contact_phone):
            continue
        SupplierContact.objects.create(
            supplier=s,
            name=s.contact_name or s.contact_email or "Contact",
            email=s.contact_email or "",
            phone=s.contact_phone or "",
        )


def drop_contacts(apps, schema_editor):
    apps.get_model("assets", "SupplierContact").objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ("assets", "0036_historicalsuppliercontact_suppliercontact"),
    ]

    operations = [
        migrations.RunPython(seed_contacts, drop_contacts),
    ]
