# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""FilterSets for module 8 (controls), README §5.

``status`` is the public alias of ``workflow_state``. Related ids are exposed
under the ``<relation>_id`` spelling of the spec. "Overdue" is derived, never a
lifecycle step (RG-CTL-07) : an active test whose next due date has passed,
read through ``reportable_states()`` rather than a step code written down
(RG-CTL-17).
"""

import django_filters
from django.db.models import Exists, OuterRef, Q
from django.utils import timezone

from controls.constants import ControlAutomation, ControlEffectiveness, ControlNature, ControlTheme, RunResult
from controls.models import Control, ControlTest, ControlTestRun
from core.lifecycle import reportable_states


def overdue_tests_q(prefix=""):
    """RG-CTL-07 : an active test with a passed next due date."""
    return Q(**{
        f"{prefix}workflow_state__in": reportable_states(ControlTest),
        f"{prefix}next_due_date__isnull": False,
        f"{prefix}next_due_date__lt": timezone.localdate(),
    })


def filter_controls_test_overdue(queryset, value):
    """RG-CTL-15 : controls with (``True``) or without any overdue active test."""
    overdue = Exists(ControlTest.objects.filter(overdue_tests_q(), control=OuterRef("pk")))
    return queryset.filter(overdue) if value else queryset.exclude(overdue)


class ControlFilter(django_filters.FilterSet):
    status = django_filters.CharFilter(field_name="workflow_state")
    theme = django_filters.ChoiceFilter(choices=ControlTheme.choices)
    nature = django_filters.ChoiceFilter(choices=ControlNature.choices)
    automation = django_filters.ChoiceFilter(choices=ControlAutomation.choices)
    effectiveness = django_filters.ChoiceFilter(choices=ControlEffectiveness.choices)
    owner_id = django_filters.UUIDFilter(field_name="owner_id")
    scope_id = django_filters.UUIDFilter(field_name="scopes__id", distinct=True)
    requirement_id = django_filters.UUIDFilter(field_name="requirements__id", distinct=True)
    risk_id = django_filters.UUIDFilter(field_name="risks__id", distinct=True)
    treatment_plan_id = django_filters.UUIDFilter(field_name="treatment_plans__id", distinct=True)
    pacs_measure_id = django_filters.UUIDFilter(field_name="pacs_measures__id", distinct=True)
    support_asset_id = django_filters.UUIDFilter(field_name="support_assets__id", distinct=True)
    objective_id = django_filters.UUIDFilter(field_name="objectives__id", distinct=True)
    policy_id = django_filters.UUIDFilter(field_name="policies__id", distinct=True)
    framework_id = django_filters.UUIDFilter(field_name="requirements__framework_id", distinct=True)
    test_overdue = django_filters.BooleanFilter(method="filter_test_overdue")

    class Meta:
        model = Control
        fields = {"workflow_state": ["exact"]}

    def filter_test_overdue(self, queryset, name, value):
        return filter_controls_test_overdue(queryset, value)


class ControlTestFilter(django_filters.FilterSet):
    status = django_filters.CharFilter(field_name="workflow_state")
    control_id = django_filters.UUIDFilter(field_name="control_id")
    tester_id = django_filters.UUIDFilter(field_name="tester_id")
    method = django_filters.CharFilter(field_name="method")
    due_before = django_filters.DateFilter(field_name="next_due_date", lookup_expr="lte")
    due_after = django_filters.DateFilter(field_name="next_due_date", lookup_expr="gte")
    overdue = django_filters.BooleanFilter(method="filter_overdue")

    class Meta:
        model = ControlTest
        fields = {"workflow_state": ["exact"]}

    def filter_overdue(self, queryset, name, value):
        return queryset.filter(overdue_tests_q()) if value else queryset.exclude(overdue_tests_q())


class ControlTestRunFilter(django_filters.FilterSet):
    status = django_filters.CharFilter(field_name="workflow_state")
    test_id = django_filters.UUIDFilter(field_name="test_id")
    control_id = django_filters.UUIDFilter(field_name="test__control_id")
    result = django_filters.ChoiceFilter(choices=RunResult.choices)
    performed_by_id = django_filters.UUIDFilter(field_name="performed_by_id")
    reviewed_by_id = django_filters.UUIDFilter(field_name="reviewed_by_id")
    performed_before = django_filters.DateFilter(field_name="performed_on", lookup_expr="lte")
    performed_after = django_filters.DateFilter(field_name="performed_on", lookup_expr="gte")

    class Meta:
        model = ControlTestRun
        fields = {"workflow_state": ["exact"]}
