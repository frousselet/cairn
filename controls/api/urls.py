# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""REST routes of module 8 under /api/v1/controls/ (README §5).

Registered flat : a test is filtered by its control (``?control_id=<uuid>``)
and a run by its test (``?test_id=<uuid>``) rather than nested under them, so
every record keeps one stable URL. Evidence files have no route here : they
are uploaded through the web form and listed, metadata only, on their run.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r"controls", views.ControlViewSet)
router.register(r"tests", views.ControlTestViewSet)
router.register(r"runs", views.ControlTestRunViewSet)

app_name = "controls-api"

urlpatterns = [
    path("", include(router.urls)),
]
