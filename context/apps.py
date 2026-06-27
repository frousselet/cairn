from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class ContextConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "context"
    verbose_name = _("Governance")

    def ready(self):
        # Register the module's standardised lifecycles (new engine: the scope
        # perimeter lifecycle). Must run in every context (tests, management
        # commands, servers) so governance / transitions / history resolve.
        from context import lifecycles  # noqa: F401
