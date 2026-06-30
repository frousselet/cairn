from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class ComplianceConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "compliance"
    verbose_name = _("Compliance")

    def ready(self):
        # Wire RC-01 / RC-02 recalculation triggers on Requirement save / delete
        # so editing a requirement directly (not only when validating an
        # assessment) keeps Section and Framework compliance_level in sync.
        from compliance import signals  # noqa: F401

        # Connect the Risk <-> Requirement M2M handler for risk-driven
        # applicability (the through model is only resolvable once apps load).
        signals.connect_risk_link_signal()

        # Register the module's standardised lifecycles (action plan, assessment).
        from compliance import lifecycles  # noqa: F401
