from django.urls import path

from . import admin_views

app_name = "trust_center_manage"

urlpatterns = [
    path("", admin_views.ManageHubView.as_view(), name="hub"),
    path("settings/", admin_views.SettingsView.as_view(), name="settings"),
    path("requests/", admin_views.DocumentRequestListView.as_view(), name="request-list"),
    path(
        "requests/<uuid:pk>/",
        admin_views.DocumentRequestDetailView.as_view(),
        name="request-detail",
    ),
    path(
        "requests/<uuid:pk>/transition/",
        admin_views.DocumentRequestTransitionView.as_view(),
        name="request-transition",
    ),
    path("<str:entity>/add/", admin_views.EntityCreateView.as_view(), name="create"),
    path("<str:entity>/<uuid:pk>/", admin_views.EntityDetailView.as_view(), name="detail"),
    path("<str:entity>/<uuid:pk>/edit/", admin_views.EntityUpdateView.as_view(), name="update"),
    path(
        "<str:entity>/<uuid:pk>/delete/",
        admin_views.EntityDeleteView.as_view(),
        name="delete",
    ),
]
