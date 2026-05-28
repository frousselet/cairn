"""Add a many-to-many link between RiskTreatmentPlan and compliance.ComplianceActionPlan."""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("compliance", "0035_complianceactionplan_originating_review_and_more"),
        ("risks", "0016_risk_criteria_snapshot"),
    ]

    operations = [
        migrations.AddField(
            model_name="risktreatmentplan",
            name="related_action_plans",
            field=models.ManyToManyField(
                blank=True,
                help_text=(
                    "Compliance action plans implementing or contributing to "
                    "this treatment plan. Linking is symmetric: both sides of "
                    "the relationship surface the connection."
                ),
                related_name="related_treatment_plans",
                to="compliance.complianceactionplan",
                verbose_name="Related action plans",
            ),
        ),
    ]
