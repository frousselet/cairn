# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""Web views of module 7 (documents). Placeholder until the UI lands."""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404
from django.views import View


class _Pending(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        raise Http404


PolicyListView = PolicyTableBodyView = PolicyCreateView = PolicyDetailView = PolicyUpdateView = _Pending
PolicyDeleteView = PolicyRecordReviewView = PolicyNewVersionView = _Pending
PolicyVersionDetailView = PolicyVersionUpdateView = PolicyVersionDeleteView = PolicyVersionPdfView = _Pending
CampaignListView = CampaignTableBodyView = CampaignCreateView = CampaignDetailView = CampaignUpdateView = _Pending
CampaignDeleteView = CampaignAddNewcomersView = AcknowledgementExcuseView = _Pending
AcknowledgeListView = AcknowledgeView = _Pending
