from django.urls import include, path

from . import views

app_name = "trust_center"

urlpatterns = [
    path("", views.TrustCenterLandingView.as_view(), name="landing"),
    path("custom.css", views.TrustCenterCustomCSSView.as_view(), name="custom-css"),
    path(
        "documents/<uuid:pk>/download/",
        views.TrustCenterPublicDocumentDownloadView.as_view(),
        name="document-download",
    ),
    path(
        "documents/<uuid:pk>/request/",
        views.DocumentRequestCreateView.as_view(),
        name="document-request",
    ),
    path(
        "documents/download/<str:token>/",
        views.TrustCenterGatedDownloadView.as_view(),
        name="gated-download",
    ),
    path("api/", include("trust_center.api.public_urls")),
]
