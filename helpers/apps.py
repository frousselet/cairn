# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
from django.apps import AppConfig


class HelpersConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "helpers"
    verbose_name = "Helpers"
