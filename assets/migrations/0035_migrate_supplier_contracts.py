"""Seed the new Contract entity from the legacy single-contract supplier fields.

Each supplier that carries any contract data (reference / start / end) gets one
Contract created and linked as a party. The legacy ``contract_*`` columns are
left in place for now (a later step retires them once the contract module owns
all contract editing).
"""

from django.db import migrations


def seed_contracts(apps, schema_editor):
    Supplier = apps.get_model("assets", "Supplier")
    Contract = apps.get_model("assets", "Contract")
    for s in Supplier.objects.all():
        if not (s.contract_reference or s.contract_start_date or s.contract_end_date):
            continue
        status = "active"
        if s.contract_end_date and s.status == "archived":
            status = "terminated"
        c = Contract.objects.create(
            reference=s.contract_reference or "",
            start_date=s.contract_start_date,
            end_date=s.contract_end_date,
            status=status,
        )
        c.suppliers.add(s)


def drop_contracts(apps, schema_editor):
    apps.get_model("assets", "Contract").objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ("assets", "0034_contract_historicalcontract_and_more"),
    ]

    operations = [
        migrations.RunPython(seed_contracts, drop_contracts),
    ]
