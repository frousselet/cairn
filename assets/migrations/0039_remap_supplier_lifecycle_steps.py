"""Remap suppliers onto the new branching supplier-risk lifecycle.

Migration 0033 landed legacy suppliers on the *first generation* of the
supplier-risk lifecycle, whose intermediate step codes were
``onboarding / risk_scoring / contracts / ict_chain / cloud / monitoring /
change_management / audit_assurance``. The lifecycle has since been rebuilt as a
branching, cyclic flow (``integration -> risk_questionnaire -> evaluation ->
compliant | non_compliant``), so NONE of those eight codes exist as steps any
more. A supplier left on one of them falls off the lifecycle:
``BaseModel._current_step`` returns ``None`` and the detail page / badge degrade
to a raw code with an all-future graph.

This data migration remaps every stale code to a valid new step so existing
suppliers (and their ``HistoricalSupplier`` audit rows) keep a coherent state.
``draft`` and ``archived`` are valid in both generations and are left untouched.
"""

from django.db import migrations

# Legacy step code -> new step code.
REMAP = {
    # Entry / early onboarding -> the one-off Integration step.
    "onboarding": "integration",
    "risk_scoring": "risk_questionnaire",
    "contracts": "risk_questionnaire",
    "ict_chain": "evaluation",
    "cloud": "evaluation",
    # Ongoing operation -> the compliant outcome of a completed review.
    "monitoring": "compliant",
    "audit_assurance": "compliant",
    # Open remediation -> the non-compliant outcome.
    "change_management": "non_compliant",
}

# Valid step codes of the new branching lifecycle (used to defensively catch any
# other stale value and park it on the cycle entry).
NEW_STEPS = {
    "draft",
    "integration",
    "risk_questionnaire",
    "evaluation",
    "compliant",
    "non_compliant",
    "archived",
}


def forwards(apps, schema_editor):
    for model_name in ("Supplier", "HistoricalSupplier"):
        model = apps.get_model("assets", model_name)
        for old_code, new_code in REMAP.items():
            model.objects.filter(workflow_state=old_code).update(
                workflow_state=new_code
            )
        # Any remaining value that is not a valid new step (defensive : an
        # unexpected leftover code) is parked on the recurring cycle entry so it
        # never falls off the lifecycle.
        model.objects.exclude(workflow_state__in=list(NEW_STEPS)).update(
            workflow_state="risk_questionnaire"
        )


def backwards(apps, schema_editor):
    # The remap is lossy (several legacy codes collapse onto one new code), so a
    # true inverse is impossible. Restore the legacy entry code for everything
    # that is not a draft / archived bookend, matching 0033's own down path.
    for model_name in ("Supplier", "HistoricalSupplier"):
        model = apps.get_model("assets", model_name)
        model.objects.exclude(workflow_state__in=["draft", "archived"]).update(
            workflow_state="onboarding"
        )


class Migration(migrations.Migration):

    dependencies = [
        ("assets", "0038_historicalsupplier_latitude_and_more"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
