from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class ReportsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "reports"
    verbose_name = _("Reports")

    def ready(self):
        # Register the module's standardised lifecycle (management review).
        from reports import lifecycles  # noqa: F401
