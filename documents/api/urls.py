# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""URL routes for the documents REST API, mounted at ``/api/v1/documents/``
from ``core/urls.py`` (README §5).

Registered flat : a version is filtered by its document
(``?policy_id=<uuid>``) and a row by its campaign (``?campaign_id=<uuid>``)
rather than nested under them, so every record keeps one stable URL. The
acknowledgement rows publish no create, update or delete route (RG-DOC-16).
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r"policies", views.PolicyViewSet)
router.register(r"policy-versions", views.PolicyVersionViewSet)
router.register(r"acknowledgement-campaigns", views.AcknowledgementCampaignViewSet)
router.register(r"acknowledgements", views.PolicyAcknowledgementViewSet)

app_name = "documents-api"

urlpatterns = [
    path("", include(router.urls)),
]
