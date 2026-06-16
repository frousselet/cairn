import os

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class AssetsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "assets"
    verbose_name = _("Assets")

    def ready(self):
        # Register the module's specific lifecycle workflows (essential and
        # support assets). Must run before the server-process early returns
        # below: workflows are needed in every context (tests, management
        # commands, servers).
        from assets import workflows  # noqa: F401

        # Register the supplier CSV bulk importer with the generic import
        # registry. Must run in every context (tests, management commands,
        # servers) so the import URLs resolve.
        from assets import imports  # noqa: F401

        # Only start the SPOF scheduler when running an actual server
        # process. The previous blocklist approach ("everything that is
        # not manage.py is a server") wrongly classified ad-hoc inline
        # scripts as servers, including the `python -c "..."` invocations
        # the Docker entrypoint runs before `migrate` to apply schema
        # fixups. Those scripts called django.setup(), triggered ready(),
        # started the scheduler, which queried tables that were still
        # missing the columns the about-to-run migrations would add.
        # Switch to an explicit allowlist of server processes so this
        # cannot happen again.
        import sys

        if "pytest" in sys.modules or "test" in sys.argv:
            return

        proc = sys.argv[0] if sys.argv else ""
        server_binaries = ("uvicorn", "gunicorn", "daphne", "hypercorn")
        is_server = any(proc.endswith(name) for name in server_binaries)
        is_runserver = proc.endswith("manage.py") and "runserver" in sys.argv
        if not (is_server or is_runserver):
            return

        if os.environ.get("RUN_MAIN", "true") == "true":
            from assets.services.spof_scheduler import start_spof_scheduler

            start_spof_scheduler()
