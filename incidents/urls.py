# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""Web URL patterns for module 6 (incidents), mounted at ``/incidents/``.

Three shapes of route live here:

- **Registers**, each with its ``table-body/`` twin for the HTMX refresh of
  ``#item-table-body``. The incident register is the module root : there is no
  redirecting dashboard entry, because the register *is* the landing page.
- **Children of an incident**, created under their parent's path
  (``<uuid:incident_pk>/...``) and edited under their own flat path, so an edit
  route cannot be pointed at another incident's child.
- **No transition routes at all.** Every state change in this module posts to
  the generic ``workflow:transition`` endpoint from the lifecycle stepper. The
  gates, the phase stamps, the generated obligations and the appended ledger
  rows all live in each model's ``transition_to()``, which that endpoint calls,
  so a per-transition view here could only duplicate them or bypass them.
"""

from django.urls import path

from . import views

app_name = "incidents"

urlpatterns = [
    # ── Incident register ──────────────────────────────────
    path("", views.IncidentListView.as_view(), name="incident-list"),
    path("table-body/", views.IncidentTableBodyView.as_view(), name="incident-table-body"),
    path("create/", views.IncidentCreateView.as_view(), name="incident-create"),

    # ── Security events (A.6.8 intake) ─────────────────────
    path("events/", views.SecurityEventListView.as_view(), name="event-list"),
    path("events/table-body/", views.SecurityEventTableBodyView.as_view(), name="event-table-body"),
    path("events/create/", views.SecurityEventCreateView.as_view(), name="event-create"),
    path("events/<uuid:pk>/", views.SecurityEventDetailView.as_view(), name="event-detail"),
    path("events/<uuid:pk>/edit/", views.SecurityEventUpdateView.as_view(), name="event-update"),
    path("events/<uuid:pk>/delete/", views.SecurityEventDeleteView.as_view(), name="event-delete"),

    # ── Response plans (A.5.24) ────────────────────────────
    path("response-plans/", views.ResponsePlanListView.as_view(), name="response-plan-list"),
    path("response-plans/table-body/", views.ResponsePlanTableBodyView.as_view(), name="response-plan-table-body"),
    path("response-plans/create/", views.ResponsePlanCreateView.as_view(), name="response-plan-create"),
    path("response-plans/<uuid:pk>/", views.ResponsePlanDetailView.as_view(), name="response-plan-detail"),
    path("response-plans/<uuid:pk>/edit/", views.ResponsePlanUpdateView.as_view(), name="response-plan-update"),
    path("response-plans/<uuid:pk>/delete/", views.ResponsePlanDeleteView.as_view(), name="response-plan-delete"),

    # ── Obligations due (cross-cutting register) ───────────
    path("notifications/", views.NotificationListView.as_view(), name="notification-list"),
    path("notifications/table-body/", views.NotificationTableBodyView.as_view(), name="notification-table-body"),
    path("notifications/<uuid:pk>/", views.NotificationDetailView.as_view(), name="notification-detail"),
    path("notifications/<uuid:pk>/edit/", views.NotificationUpdateView.as_view(), name="notification-update"),
    path("notifications/<uuid:pk>/delete/", views.NotificationDeleteView.as_view(), name="notification-delete"),
    path("notifications/<uuid:pk>/proof/", views.NotificationProofDownloadView.as_view(), name="notification-proof"),
    # Filings : append-only, plus the narrow completion control and the proof.
    path("notifications/<uuid:pk>/filings/", views.FilingsPartialView.as_view(), name="notification-filings"),
    path("notifications/<uuid:notification_pk>/filings/create/", views.FilingCreateView.as_view(), name="filing-create"),
    path("filings/<uuid:pk>/outcome/", views.FilingOutcomeView.as_view(), name="filing-outcome"),
    path("filings/<uuid:pk>/proof/", views.FilingProofDownloadView.as_view(), name="filing-proof"),

    # ── Evidence (A.5.28) ──────────────────────────────────
    path("evidence/<uuid:pk>/", views.EvidenceDetailView.as_view(), name="evidence-detail"),
    path("evidence/<uuid:pk>/edit/", views.EvidenceUpdateView.as_view(), name="evidence-update"),
    path("evidence/<uuid:pk>/delete/", views.EvidenceDeleteView.as_view(), name="evidence-delete"),
    path("evidence/<uuid:pk>/file/", views.EvidenceFileDownloadView.as_view(), name="evidence-file"),
    path("evidence/<uuid:pk>/verify/", views.EvidenceVerifyIntegrityView.as_view(), name="evidence-verify"),
    # Chain of custody : append-only.
    path("evidence/<uuid:pk>/custody/", views.CustodyEventsPartialView.as_view(), name="custody-events"),
    path("evidence/<uuid:evidence_pk>/custody/create/", views.CustodyEventCreateView.as_view(), name="custody-event-create"),

    # ── Post-incident reviews (A.5.27) ─────────────────────
    path("post-incident-reviews/<uuid:pk>/", views.PostIncidentReviewDetailView.as_view(), name="review-detail"),
    path("post-incident-reviews/<uuid:pk>/edit/", views.PostIncidentReviewUpdateView.as_view(), name="review-update"),
    path("post-incident-reviews/<uuid:pk>/delete/", views.PostIncidentReviewDeleteView.as_view(), name="review-delete"),

    # ── Personal data qualification (GDPR) ─────────────────
    # No register of its own : a breach is always a qualification *of* an
    # incident, and a second list would invite the two to drift.
    path("personal-data-breaches/<uuid:pk>/", views.PersonalDataBreachDetailView.as_view(), name="breach-detail"),
    path("personal-data-breaches/<uuid:pk>/edit/", views.PersonalDataBreachUpdateView.as_view(), name="breach-update"),
    path("personal-data-breaches/<uuid:pk>/delete/", views.PersonalDataBreachDeleteView.as_view(), name="breach-delete"),

    # ── Regulatory catalogue (configuration area) ──────────
    path("reporting-authorities/", views.ReportingAuthorityListView.as_view(), name="reporting-authority-list"),
    path("reporting-authorities/table-body/", views.ReportingAuthorityTableBodyView.as_view(), name="reporting-authority-table-body"),
    path("reporting-authorities/create/", views.ReportingAuthorityCreateView.as_view(), name="reporting-authority-create"),
    path("reporting-authorities/<uuid:pk>/", views.ReportingAuthorityDetailView.as_view(), name="reporting-authority-detail"),
    path("reporting-authorities/<uuid:pk>/edit/", views.ReportingAuthorityUpdateView.as_view(), name="reporting-authority-update"),
    path("reporting-authorities/<uuid:pk>/delete/", views.ReportingAuthorityDeleteView.as_view(), name="reporting-authority-delete"),
    path("obligation-templates/", views.ObligationTemplateListView.as_view(), name="obligation-template-list"),
    path("obligation-templates/table-body/", views.ObligationTemplateTableBodyView.as_view(), name="obligation-template-table-body"),
    path("obligation-templates/create/", views.ObligationTemplateCreateView.as_view(), name="obligation-template-create"),
    path("obligation-templates/<uuid:pk>/", views.ObligationTemplateDetailView.as_view(), name="obligation-template-detail"),
    path("obligation-templates/<uuid:pk>/edit/", views.ObligationTemplateUpdateView.as_view(), name="obligation-template-update"),
    path("obligation-templates/<uuid:pk>/delete/", views.ObligationTemplateDeleteView.as_view(), name="obligation-template-delete"),

    # ── Incident detail, and its children ──────────────────
    # Declared last so every literal prefix above is matched first. `<uuid:pk>`
    # cannot swallow "events" or "evidence", but keeping the catch-all shape at
    # the end is what stops a future prefix from being shadowed silently.
    path("<uuid:pk>/", views.IncidentDetailView.as_view(), name="incident-detail"),
    path("<uuid:pk>/edit/", views.IncidentUpdateView.as_view(), name="incident-update"),
    path("<uuid:pk>/delete/", views.IncidentDeleteView.as_view(), name="incident-delete"),
    # Chronology : append-only, so create and the card partial, and nothing else.
    path("<uuid:pk>/timeline/", views.TimelineEntriesPartialView.as_view(), name="timeline-entries"),
    path("<uuid:incident_pk>/timeline/create/", views.TimelineEntryCreateView.as_view(), name="timeline-entry-create"),
    # Response actions.
    path("<uuid:pk>/response-actions/", views.ResponseActionsPartialView.as_view(), name="response-actions"),
    path("<uuid:incident_pk>/response-actions/create/", views.ResponseActionCreateView.as_view(), name="response-action-create"),
    # Flat paths, like evidence and notifications : an edit route nested under
    # an incident pk could be aimed at another incident's child.
    path("response-actions/<uuid:pk>/edit/", views.ResponseActionUpdateView.as_view(), name="response-action-update"),
    path("response-actions/<uuid:pk>/delete/", views.ResponseActionDeleteView.as_view(), name="response-action-delete"),
    # Evidence, notifications, the review and the qualification are created
    # from the incident page and edited under their own paths above.
    path("<uuid:incident_pk>/evidence/create/", views.EvidenceCreateView.as_view(), name="evidence-create"),
    path("<uuid:incident_pk>/notifications/create/", views.NotificationCreateView.as_view(), name="notification-create"),
    path("<uuid:incident_pk>/post-incident-review/create/", views.PostIncidentReviewCreateView.as_view(), name="review-create"),
    path("<uuid:incident_pk>/personal-data-breach/create/", views.PersonalDataBreachCreateView.as_view(), name="breach-create"),
]
