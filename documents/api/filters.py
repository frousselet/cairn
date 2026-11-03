# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""FilterSets for module 7 (documents).

``status`` is the public alias of ``workflow_state`` (filtering by a step and
moving to one are different acts; only the second goes through
``transition_to()``). Related ids are exposed under the ``<relation>_id``
spelling of the spec (README §5), with the bare relation name accepted too.

Where a filter reasons about governance ("overdue for review" applies to an
active document only), it reads the lifecycle's step metadata through
``reportable_states()`` rather than writing a step code down (RG-DOC-20).
"""

import django_filters
from django.db.models import Q
from django.utils import timezone

from core.lifecycle import reportable_states
from documents.constants import AcknowledgementStatus
from documents.models import AcknowledgementCampaign, Policy, PolicyAcknowledgement, PolicyVersion


class PolicyFilter(django_filters.FilterSet):
    status = django_filters.CharFilter(field_name="workflow_state")
    type = django_filters.CharFilter(field_name="document_type")
    document_type = django_filters.CharFilter(field_name="document_type")
    classification = django_filters.CharFilter(field_name="classification")
    owner_id = django_filters.UUIDFilter(field_name="owner_id")
    owner = django_filters.UUIDFilter(field_name="owner_id")
    approver_id = django_filters.UUIDFilter(field_name="approver_id")
    parent_id = django_filters.UUIDFilter(field_name="parent_id")
    parent = django_filters.UUIDFilter(field_name="parent_id")
    scope_id = django_filters.UUIDFilter(field_name="scopes__id")
    scope = django_filters.UUIDFilter(field_name="scopes__id")
    linked_requirement_id = django_filters.UUIDFilter(field_name="linked_requirements__id")
    review_before = django_filters.DateFilter(field_name="next_review_date", lookup_expr="lte")
    review_after = django_filters.DateFilter(field_name="next_review_date", lookup_expr="gte")
    overdue = django_filters.BooleanFilter(method="filter_overdue")

    class Meta:
        model = Policy
        fields = {"workflow_state": ["exact"]}

    def filter_overdue(self, queryset, name, value):
        """RG-DOC-12 : an active document whose next review date has passed."""
        overdue = Q(
            workflow_state__in=reportable_states(Policy),
            next_review_date__isnull=False,
            next_review_date__lt=timezone.localdate(),
        )
        return queryset.filter(overdue) if value else queryset.exclude(overdue)


class PolicyVersionFilter(django_filters.FilterSet):
    status = django_filters.CharFilter(field_name="workflow_state")
    policy_id = django_filters.UUIDFilter(field_name="policy_id")
    policy = django_filters.UUIDFilter(field_name="policy_id")
    approved_by_id = django_filters.UUIDFilter(field_name="approved_by_id")
    effective_before = django_filters.DateFilter(field_name="effective_from", lookup_expr="lte")
    effective_after = django_filters.DateFilter(field_name="effective_from", lookup_expr="gte")

    class Meta:
        model = PolicyVersion
        fields = {"workflow_state": ["exact"], "version_label": ["exact"]}


class AcknowledgementCampaignFilter(django_filters.FilterSet):
    status = django_filters.CharFilter(field_name="workflow_state")
    policy_version_id = django_filters.UUIDFilter(field_name="policy_version_id")
    policy_version = django_filters.UUIDFilter(field_name="policy_version_id")
    policy_id = django_filters.UUIDFilter(field_name="policy_version__policy_id")
    scope_id = django_filters.UUIDFilter(field_name="scopes__id")
    due_before = django_filters.DateFilter(field_name="due_date", lookup_expr="lte")
    due_after = django_filters.DateFilter(field_name="due_date", lookup_expr="gte")

    class Meta:
        model = AcknowledgementCampaign
        fields = {"workflow_state": ["exact"]}


class PolicyAcknowledgementFilter(django_filters.FilterSet):
    status = django_filters.ChoiceFilter(choices=AcknowledgementStatus.choices)
    campaign_id = django_filters.UUIDFilter(field_name="campaign_id")
    campaign = django_filters.UUIDFilter(field_name="campaign_id")
    user_id = django_filters.UUIDFilter(field_name="user_id")
    policy_version_id = django_filters.UUIDFilter(field_name="campaign__policy_version_id")
    policy_id = django_filters.UUIDFilter(field_name="campaign__policy_version__policy_id")
    channel = django_filters.CharFilter(field_name="channel")

    class Meta:
        model = PolicyAcknowledgement
        fields = []
