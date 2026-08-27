# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
from django.urls import path

from .workflow_views import WorkflowTransitionView

app_name = "workflow"

urlpatterns = [
    path(
        "<str:app_label>/<str:model>/<uuid:pk>/transition/",
        WorkflowTransitionView.as_view(),
        name="transition",
    ),
]
