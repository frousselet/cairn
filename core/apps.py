# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
import sys
from pathlib import Path

from django.apps import AppConfig
from django.conf import settings

#: Management commands that serve or collect the interface, and therefore need
#: the front-end libraries on disk. Every other command (migrate, shell, tests…)
#: must stay offline-safe, so it never triggers a download.
COMMANDS_NEEDING_ASSETS = {"runserver", "collectstatic"}


def _is_serving(argv):
    """Whether this process is about to serve or collect the interface.

    A direct install is started either through ``manage.py runserver`` or
    through an ASGI/WSGI runner (uvicorn, gunicorn, daphne) that imports
    ``core.asgi`` : the runner has no management command to inspect, so anything
    that is not ``manage.py`` counts as serving.
    """
    if not argv:
        return False
    entry = Path(argv[0]).name
    if entry in {"manage.py", "django-admin", "django-admin.py"}:
        return len(argv) > 1 and argv[1] in COMMANDS_NEEDING_ASSETS
    # A test runner drives the app without serving it, and must not hit the network.
    if entry.startswith("pytest") or entry == "py.test":
        return False
    return True


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"

    def ready(self):
        import core.lifecycle_seed  # noqa: F401  (post_migrate lifecycle sync)
        import core.signals  # noqa: F401

        self._mirror_frontend_libraries()

    def _mirror_frontend_libraries(self):
        """Fetch the front-end libraries on the first launch of a direct install.

        Docker images carry them already (the build runs ``vendor_assets``), and
        every later start finds the files in place, so this is a no-op cost of
        one stat per file. Never fatal : an unreachable mirror degrades the
        interface, it does not stop the instance from booting.
        """
        if not getattr(settings, "VENDOR_ASSETS_AUTO_DOWNLOAD", True):
            return
        if not _is_serving(sys.argv):
            return

        from core.vendoring import ensure_present

        ensure_present(log=lambda message: print(message, file=sys.stderr))
