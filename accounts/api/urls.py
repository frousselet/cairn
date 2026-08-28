# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from accounts.api import views

router = DefaultRouter()
router.register("users", views.UserViewSet, basename="user")
router.register("groups", views.GroupViewSet, basename="group")
router.register("permissions", views.PermissionViewSet, basename="permission")
router.register("access-logs", views.AccessLogViewSet, basename="access-log")
router.register("notifications", views.NotificationViewSet, basename="notification")
router.register("saved-filters", views.SavedFilterViewSet, basename="saved-filter")

urlpatterns = [
    # Auth endpoints
    path("auth/login/", views.LoginAPIView.as_view(), name="api-login"),
    path("auth/logout/", views.LogoutAPIView.as_view(), name="api-logout"),
    path("auth/me/", views.MeAPIView.as_view(), name="api-me"),
    path("auth/refresh/", views.TokenRefreshAPIView.as_view(), name="api-token-refresh"),

    # Dashboard widget layout (per-user)
    path("dashboard-layout/", views.DashboardLayoutAPIView.as_view(), name="api-dashboard-layout"),

    # Company settings
    path("company-settings/", views.CompanySettingsAPIView.as_view(), name="api-company-settings"),

    # Third-party components the instance is built on
    path("dependencies/", views.DependenciesAPIView.as_view(), name="api-dependencies"),
    path("update-check/", views.UpdateCheckAPIView.as_view(), name="api-update-check"),

    # Resource endpoints
    path("", include(router.urls)),
]
