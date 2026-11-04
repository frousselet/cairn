# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""URL contract of module 8 (controls). Route names are fixed : notifications,
search, the calendar, the kanban and the reverse cards rely on them."""

from django.urls import path

from controls import views

app_name = "controls"

urlpatterns = [
    path("", views.ControlListView.as_view(), name="control-list"),
    path("create/", views.ControlCreateView.as_view(), name="control-create"),
    path("from-requirements/", views.ControlFromRequirementsView.as_view(), name="control-from-requirements"),
    path("<uuid:pk>/", views.ControlDetailView.as_view(), name="control-detail"),
    path("<uuid:pk>/edit/", views.ControlUpdateView.as_view(), name="control-update"),
    path("<uuid:pk>/delete/", views.ControlDeleteView.as_view(), name="control-delete"),
    path("<uuid:control_pk>/tests/create/", views.ControlTestCreateView.as_view(), name="controltest-create"),
    path("tests/", views.ControlTestListView.as_view(), name="controltest-list"),
    path("tests/<uuid:pk>/", views.ControlTestDetailView.as_view(), name="controltest-detail"),
    path("tests/<uuid:pk>/edit/", views.ControlTestUpdateView.as_view(), name="controltest-update"),
    path("tests/<uuid:pk>/delete/", views.ControlTestDeleteView.as_view(), name="controltest-delete"),
    path("tests/<uuid:test_pk>/runs/create/", views.ControlTestRunCreateView.as_view(), name="controltestrun-create"),
    path("runs/<uuid:pk>/", views.ControlTestRunDetailView.as_view(), name="controltestrun-detail"),
    path("runs/<uuid:pk>/edit/", views.ControlTestRunUpdateView.as_view(), name="controltestrun-update"),
    path("runs/<uuid:pk>/delete/", views.ControlTestRunDeleteView.as_view(), name="controltestrun-delete"),
    path("runs/<uuid:pk>/raise-finding/", views.RaiseFindingView.as_view(), name="controltestrun-raise-finding"),
    path("runs/<uuid:pk>/evidence/upload/", views.EvidenceUploadView.as_view(), name="evidence-upload"),
    path("evidence/<uuid:pk>/download/", views.EvidenceDownloadView.as_view(), name="evidence-download"),
    path("evidence/<uuid:pk>/delete/", views.EvidenceDeleteView.as_view(), name="evidence-delete"),
]
