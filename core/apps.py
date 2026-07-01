from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"

    def ready(self):
        import core.lifecycle_seed  # noqa: F401  (post_migrate lifecycle sync)
        import core.signals  # noqa: F401
