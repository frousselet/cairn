from django.urls import path

from . import public_views

app_name = "trust_center_public_api"

urlpatterns = [
    path("", public_views.TrustCenterPublicView.as_view(), name="overview"),
    path(
        "certifications/",
        public_views.PublicCertificationListView.as_view(),
        name="certifications",
    ),
    path(
        "subprocessors/",
        public_views.PublicSubprocessorListView.as_view(),
        name="subprocessors",
    ),
    path("measures/", public_views.PublicMeasureListView.as_view(), name="measures"),
    path("documents/", public_views.PublicDocumentListView.as_view(), name="documents"),
]
