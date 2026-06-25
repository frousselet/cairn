from django.urls import path

from . import views
from . import management_review_views as mrv

app_name = "reports"

urlpatterns = [
    path("", views.ReportListView.as_view(), name="report-list"),
    path("soa/create/", views.SoaReportCreateView.as_view(), name="soa-create"),
    path("audit/create/", views.AuditReportCreateView.as_view(), name="audit-report-create"),
    # Legacy one-shot management review export (kept for backward compatibility)
    path(
        "management-review/create/",
        views.ManagementReviewCreateView.as_view(),
        name="management-review-create",
    ),
    # Persistent management review workflow (ISO 27001:2022 clause 9.3)
    path(
        "management-reviews/",
        mrv.ManagementReviewListView.as_view(),
        name="management-review-list",
    ),
    path(
        "management-reviews/table-body/",
        mrv.ManagementReviewTableBodyView.as_view(),
        name="management-review-table-body",
    ),
    path(
        "management-reviews/new/",
        mrv.ManagementReviewCreateView.as_view(),
        name="management-review-new",
    ),
    path(
        "management-reviews/<uuid:pk>/",
        mrv.ManagementReviewDetailView.as_view(),
        name="management-review-detail",
    ),
    path(
        "management-reviews/<uuid:pk>/edit/",
        mrv.ManagementReviewUpdateView.as_view(),
        name="management-review-edit",
    ),
    path(
        "management-reviews/<uuid:pk>/delete/",
        mrv.ManagementReviewDeleteView.as_view(),
        name="management-review-delete",
    ),
    path(
        "management-reviews/<uuid:pk>/transition/",
        mrv.ManagementReviewTransitionView.as_view(),
        name="management-review-transition",
    ),
    path(
        "management-reviews/<uuid:pk>/export/<str:fmt>/",
        mrv.ManagementReviewExportView.as_view(),
        name="management-review-export",
    ),
    path(
        "management-reviews/<uuid:pk>/comment/",
        mrv.ManagementReviewCommentCreateView.as_view(),
        name="management-review-comment-create",
    ),
    path(
        "management-reviews/<uuid:pk>/decisions/new/",
        mrv.DecisionCreateView.as_view(),
        name="decision-create",
    ),
    path(
        "decisions/<uuid:pk>/",
        mrv.DecisionDetailView.as_view(),
        name="decision-detail",
    ),
    path(
        "decisions/<uuid:pk>/edit/",
        mrv.DecisionUpdateView.as_view(),
        name="decision-edit",
    ),
    path(
        "decisions/<uuid:pk>/delete/",
        mrv.DecisionDeleteView.as_view(),
        name="decision-delete",
    ),
    path(
        "decisions/<uuid:pk>/promote/",
        mrv.DecisionPromoteView.as_view(),
        name="decision-promote",
    ),
    path(
        "management-reviews/<uuid:pk>/isms-changes/new/",
        mrv.IsmsChangeCreateView.as_view(),
        name="isms-change-create",
    ),
    path(
        "isms-changes/<uuid:pk>/edit/",
        mrv.IsmsChangeUpdateView.as_view(),
        name="isms-change-edit",
    ),
    path(
        "isms-changes/<uuid:pk>/delete/",
        mrv.IsmsChangeDeleteView.as_view(),
        name="isms-change-delete",
    ),
    path(
        "participants/<uuid:pk>/sign/",
        mrv.ParticipantSignatureView.as_view(),
        name="participant-sign",
    ),
    # Legacy download and delete
    path("<uuid:pk>/download/", views.ReportDownloadView.as_view(), name="report-download"),
    path("<uuid:pk>/delete/", views.ReportDeleteView.as_view(), name="report-delete"),
]
