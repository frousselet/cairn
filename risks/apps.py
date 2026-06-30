from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class RisksConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "risks"
    verbose_name = _("Risk management")

    def ready(self):
        from risks import signals  # noqa: F401

        # Register the module's standardised lifecycles (risk, assessment,
        # treatment plan, acceptance, vulnerability and the EBIOS deliverables).
        from risks import lifecycles  # noqa: F401
