# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""Web URL patterns for module 7 (documents), mounted at ``/documents/``.

No transition routes : every state change posts to the generic
``workflow:transition`` endpoint from the lifecycle stepper, and the gates and
side effects (supersession, approval stamps, campaign launch / closure) live in
each model's ``transition_to()``.
"""

from django.urls import path

from . import views

app_name = "documents"

urlpatterns = [
    # Documents (Policy)
    path("policies/", views.PolicyListView.as_view(), name="policy-list"),
    path("policies/table-body/", views.PolicyTableBodyView.as_view(), name="policy-table-body"),
    path("policies/create/", views.PolicyCreateView.as_view(), name="policy-create"),
    path("policies/<uuid:pk>/", views.PolicyDetailView.as_view(), name="policy-detail"),
    path("policies/<uuid:pk>/edit/", views.PolicyUpdateView.as_view(), name="policy-update"),
    path("policies/<uuid:pk>/delete/", views.PolicyDeleteView.as_view(), name="policy-delete"),
    path("policies/<uuid:pk>/record-review/", views.PolicyRecordReviewView.as_view(), name="policy-record-review"),
    path("policies/<uuid:pk>/new-version/", views.PolicyNewVersionView.as_view(), name="policy-new-version"),
    # Versions
    path("versions/<uuid:pk>/", views.PolicyVersionDetailView.as_view(), name="policyversion-detail"),
    path("versions/<uuid:pk>/edit/", views.PolicyVersionUpdateView.as_view(), name="policyversion-update"),
    path("versions/<uuid:pk>/delete/", views.PolicyVersionDeleteView.as_view(), name="policyversion-delete"),
    path("versions/<uuid:pk>/pdf/", views.PolicyVersionPdfView.as_view(), name="policyversion-pdf"),
    # Acknowledgement campaigns
    path("campaigns/", views.CampaignListView.as_view(), name="campaign-list"),
    path("campaigns/table-body/", views.CampaignTableBodyView.as_view(), name="campaign-table-body"),
    path("campaigns/create/", views.CampaignCreateView.as_view(), name="campaign-create"),
    path("campaigns/<uuid:pk>/", views.CampaignDetailView.as_view(), name="acknowledgementcampaign-detail"),
    path("campaigns/<uuid:pk>/edit/", views.CampaignUpdateView.as_view(), name="campaign-update"),
    path("campaigns/<uuid:pk>/delete/", views.CampaignDeleteView.as_view(), name="campaign-delete"),
    path("campaigns/<uuid:pk>/add-newcomers/", views.CampaignAddNewcomersView.as_view(), name="campaign-add-newcomers"),
    path("acknowledgements/<uuid:pk>/excuse/", views.AcknowledgementExcuseView.as_view(), name="acknowledgement-excuse"),
    # Personal : what the current user has to acknowledge
    path("acknowledge/", views.AcknowledgeListView.as_view(), name="acknowledge-list"),
    path("acknowledge/<uuid:pk>/", views.AcknowledgeView.as_view(), name="acknowledge"),
]
