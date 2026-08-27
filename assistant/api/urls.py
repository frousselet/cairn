# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r"feedback", views.AssistantFeedbackViewSet, basename="assistant-feedback")

urlpatterns = [
    path("ask/", views.AskAssistantApiView.as_view(), name="assistant-api-ask"),
    path("", include(router.urls)),
]
