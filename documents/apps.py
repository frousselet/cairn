# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class DocumentsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "documents"
    verbose_name = _("Documents")

    def ready(self):
        # Register the module's three lifecycles before any model resolves its
        # own. Omitting this import FAILS SILENTLY : `lifecycle_name_for` falls
        # back to the default 4-state lifecycle, so every gate of the module
        # would disappear with no error (tests assert each model's lifecycle).
        from documents import lifecycles  # noqa: F401
