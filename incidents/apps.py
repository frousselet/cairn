# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class IncidentsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "incidents"
    verbose_name = _("Incidents")

    def ready(self):
        # Register the module's six lifecycles before any model resolves its
        # own. Omitting this import FAILS SILENTLY : `lifecycle_name_for`
        # checks `name in LIFECYCLE_REGISTRY` and falls back to the default
        # 4-state lifecycle, so every governance gate in the module would
        # quietly disappear with no error anywhere.
        from incidents import lifecycles  # noqa: F401
