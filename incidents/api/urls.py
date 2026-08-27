# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""URL routes for the incidents REST API.

Mounted at ``/api/v1/incidents/`` from ``core/urls.py``. The thirteen
registrations are the module's thirteen concrete entities : nothing is nested
under a parent path, because a child is filtered by its parent
(``?incident=<uuid>``) rather than addressed through it, which keeps every row
citable by one stable URL.

The three append-only entities publish fewer verbs than the router would
normally generate : their viewsets restrict ``http_method_names``, so the
detail route answers ``GET`` only, plus the one completion ``PATCH`` on a
filing.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r"incidents", views.IncidentViewSet)
router.register(r"security-events", views.SecurityEventViewSet)
router.register(r"response-plans", views.IncidentResponsePlanViewSet)
router.register(r"response-actions", views.IncidentResponseActionViewSet)
router.register(r"timeline-entries", views.IncidentTimelineEntryViewSet)
router.register(r"evidence", views.IncidentEvidenceViewSet)
router.register(r"custody-events", views.EvidenceCustodyEventViewSet)
router.register(r"post-incident-reviews", views.PostIncidentReviewViewSet)
router.register(r"reporting-authorities", views.ReportingAuthorityViewSet)
router.register(r"obligation-templates", views.ReportingObligationTemplateViewSet)
router.register(r"notifications", views.IncidentNotificationViewSet)
router.register(r"notification-filings", views.NotificationFilingViewSet)
router.register(r"personal-data-breaches", views.PersonalDataBreachViewSet)

app_name = "incidents-api"

urlpatterns = [
    path("", include(router.urls)),
]
