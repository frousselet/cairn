# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
from django.urls import path

from core import lifecycle_admin_views as views

app_name = "core"

urlpatterns = [
    path("", views.LifecycleDefinitionListView.as_view(), name="lifecycle-list"),
    path("<slug:name>/", views.LifecycleDefinitionUpdateView.as_view(), name="lifecycle-edit"),
    path("<slug:name>/reset/", views.LifecycleDefinitionResetView.as_view(), name="lifecycle-reset"),
]
