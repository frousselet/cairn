from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class TrustCenterConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "trust_center"
    verbose_name = _("Trust Center")

    def ready(self):
        # Register the module's specific lifecycle workflows (publication,
        # document request) so they are available before any model resolves
        # its workflow.
        from trust_center import workflows  # noqa: F401
