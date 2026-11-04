# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""Web views of module 8 (controls). Placeholder until the UI lands."""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404
from django.views import View


class _Pending(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        raise Http404


ControlListView = ControlCreateView = ControlFromRequirementsView = ControlDetailView = _Pending
ControlUpdateView = ControlDeleteView = _Pending
ControlTestCreateView = ControlTestListView = ControlTestDetailView = ControlTestUpdateView = _Pending
ControlTestDeleteView = _Pending
ControlTestRunCreateView = ControlTestRunDetailView = ControlTestRunUpdateView = ControlTestRunDeleteView = _Pending
RaiseFindingView = EvidenceUploadView = EvidenceDownloadView = EvidenceDeleteView = _Pending
