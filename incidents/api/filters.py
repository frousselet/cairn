# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""FilterSets for module 6 (incidents).

Two conventions, both inherited from the existing modules :

- ``status`` is the public alias of ``workflow_state``, declared as a
  ``CharFilter`` beside the ``Meta.fields`` entry so both spellings answer.
  Neither is a write path : filtering by a step and moving to one are different
  acts, and only the second goes through ``transition_to()``.
- Related ids are exposed under the bare relation name (``incident``,
  ``owner``, ``scope``), which is what ``assets``, ``risks`` and ``compliance``
  already do.

Where a filter needs to reason about *governance* rather than about data - is
this plan in force, is this template usable, is this obligation still open - it
reads the lifecycle's step metadata through ``reportable_states()`` or through
the registered lifecycle's archived steps. No step code is written down here.
"""

from datetime import timedelta

import django_filters
from django.db.models import Q
from django.utils import timezone

from core.lifecycle import reportable_states, resolve_lifecycle
from incidents.constants import (
    CustodyAction,
    EventTriageDecision,
    NotificationDecision,
    ResponseActionStatus,
)
from incidents.models import (
    EvidenceCustodyEvent,
    Incident,
    IncidentEvidence,
    IncidentNotification,
    IncidentResponseAction,
    IncidentResponsePlan,
    IncidentTimelineEntry,
    NotificationFiling,
    PersonalDataBreach,
    PostIncidentReview,
    ReportingAuthority,
    ReportingObligationTemplate,
    SecurityEvent,
)
from incidents.models.response_plan import EXERCISE_STALE_AFTER_DAYS


def _terminal_states(model):
    """Step codes of a model's terminal / archived steps.

    Read off the registered lifecycle rather than written down : "the duty is
    no longer open" is governance metadata, and a lifecycle edited in the
    admin must not leave a stale literal behind in a filter.
    """
    return [step.code for step in resolve_lifecycle(model).archived_steps]


def _open_obligations():
    """Obligations whose clock is still running and unanswered by a filing."""
    return Q(due_at__isnull=False, sent_at__isnull=True) & ~Q(
        workflow_state__in=_terminal_states(IncidentNotification)
    )


# --- Incident response plan --------------------------------------------------


class IncidentResponsePlanFilter(django_filters.FilterSet):
    status = django_filters.CharFilter(field_name="workflow_state")
    scope = django_filters.UUIDFilter(field_name="scopes__id")
    owner = django_filters.UUIDFilter(field_name="owner_id")
    approved_by = django_filters.UUIDFilter(field_name="approved_by_id")
    responsible_role = django_filters.UUIDFilter(field_name="responsible_roles__id")
    linked_requirement = django_filters.UUIDFilter(
        field_name="linked_requirements__id"
    )
    review_before = django_filters.DateFilter(
        field_name="review_date", lookup_expr="lte"
    )
    review_after = django_filters.DateFilter(
        field_name="review_date", lookup_expr="gte"
    )
    effective_before = django_filters.DateFilter(
        field_name="effective_from", lookup_expr="lte"
    )
    effective_after = django_filters.DateFilter(
        field_name="effective_from", lookup_expr="gte"
    )
    in_force = django_filters.BooleanFilter(method="filter_in_force")
    review_overdue = django_filters.BooleanFilter(method="filter_review_overdue")
    exercise_overdue = django_filters.BooleanFilter(method="filter_exercise_overdue")

    class Meta:
        model = IncidentResponsePlan
        fields = {
            "workflow_state": ["exact"],
        }

    def filter_in_force(self, queryset, name, value):
        """*In force* is exactly *counts in reports* on the core lifecycle."""
        states = reportable_states(IncidentResponsePlan)
        if value:
            return queryset.filter(workflow_state__in=states)
        return queryset.exclude(workflow_state__in=states)

    def filter_review_overdue(self, queryset, name, value):
        today = timezone.localdate()
        overdue = Q(review_date__isnull=False, review_date__lt=today)
        return queryset.filter(overdue) if value else queryset.exclude(overdue)

    def filter_exercise_overdue(self, queryset, name, value):
        """A.5.24 : a plan in force that has gone a year without a test.

        Never exercised is the worst case, not an exempt one, so a null
        ``last_exercise_date`` matches.
        """
        stale_before = timezone.localdate() - timedelta(days=EXERCISE_STALE_AFTER_DAYS)
        overdue = Q(workflow_state__in=reportable_states(IncidentResponsePlan)) & (
            Q(last_exercise_date__isnull=True)
            | Q(last_exercise_date__lt=stale_before)
        )
        return queryset.filter(overdue) if value else queryset.exclude(overdue)


# --- Security event ----------------------------------------------------------


class SecurityEventFilter(django_filters.FilterSet):
    status = django_filters.CharFilter(field_name="workflow_state")
    scope = django_filters.UUIDFilter(field_name="scopes__id")
    reporter = django_filters.UUIDFilter(field_name="reporter_id")
    assessed_by = django_filters.UUIDFilter(field_name="assessed_by_id")
    reported_by_supplier = django_filters.UUIDFilter(
        field_name="reported_by_supplier_id"
    )
    incident = django_filters.UUIDFilter(field_name="incident_id")
    vulnerability = django_filters.UUIDFilter(field_name="vulnerability_id")
    duplicate_of = django_filters.UUIDFilter(field_name="duplicate_of_id")
    support_asset = django_filters.UUIDFilter(
        field_name="affected_support_assets__id"
    )
    essential_asset = django_filters.UUIDFilter(
        field_name="affected_essential_assets__id"
    )
    site = django_filters.UUIDFilter(field_name="affected_sites__id")
    reported_after = django_filters.DateTimeFilter(
        field_name="reported_at", lookup_expr="gte"
    )
    reported_before = django_filters.DateTimeFilter(
        field_name="reported_at", lookup_expr="lte"
    )
    detected_after = django_filters.DateTimeFilter(
        field_name="detected_at", lookup_expr="gte"
    )
    detected_before = django_filters.DateTimeFilter(
        field_name="detected_at", lookup_expr="lte"
    )
    undecided = django_filters.BooleanFilter(method="filter_undecided")
    promoted = django_filters.BooleanFilter(method="filter_promoted")

    class Meta:
        model = SecurityEvent
        fields = {
            "workflow_state": ["exact"],
            "event_class": ["exact"],
            "category": ["exact"],
            "triage_decision": ["exact"],
            "detection_source": ["exact"],
            "is_anonymous": ["exact"],
        }

    def filter_undecided(self, queryset, name, value):
        """Reports nobody has ruled on yet.

        There is deliberately no ``pending`` member of the decision enum : an
        undecided event is one carrying no verdict at all, so the blank is the
        query.
        """
        if value:
            return queryset.filter(triage_decision="")
        return queryset.exclude(triage_decision="")

    def filter_promoted(self, queryset, name, value):
        """Events that became an incident or a registered weakness."""
        promoted = Q(
            triage_decision__in=[
                EventTriageDecision.INCIDENT,
                EventTriageDecision.WEAKNESS,
            ]
        )
        return queryset.filter(promoted) if value else queryset.exclude(promoted)


# --- Incident ----------------------------------------------------------------


class IncidentFilter(django_filters.FilterSet):
    status = django_filters.CharFilter(field_name="workflow_state")
    scope = django_filters.UUIDFilter(field_name="scopes__id")
    incident_manager = django_filters.UUIDFilter(field_name="incident_manager_id")
    reporter = django_filters.UUIDFilter(field_name="reporter_id")
    origin_supplier = django_filters.UUIDFilter(field_name="origin_supplier_id")
    response_plan = django_filters.UUIDFilter(field_name="response_plan_id")
    parent_incident = django_filters.UUIDFilter(field_name="parent_incident_id")
    affected_supplier = django_filters.UUIDFilter(field_name="affected_suppliers__id")
    essential_asset = django_filters.UUIDFilter(
        field_name="affected_essential_assets__id"
    )
    support_asset = django_filters.UUIDFilter(
        field_name="affected_support_assets__id"
    )
    site = django_filters.UUIDFilter(field_name="affected_sites__id")
    activity = django_filters.UUIDFilter(field_name="affected_activities__id")
    threat = django_filters.UUIDFilter(field_name="threats__id")
    exploited_vulnerability = django_filters.UUIDFilter(
        field_name="exploited_vulnerabilities__id"
    )
    realised_risk = django_filters.UUIDFilter(field_name="realised_risks__id")
    linked_requirement = django_filters.UUIDFilter(
        field_name="linked_requirements__id"
    )
    detected_after = django_filters.DateTimeFilter(
        field_name="detected_at", lookup_expr="gte"
    )
    detected_before = django_filters.DateTimeFilter(
        field_name="detected_at", lookup_expr="lte"
    )
    awareness_after = django_filters.DateTimeFilter(
        field_name="awareness_at", lookup_expr="gte"
    )
    awareness_before = django_filters.DateTimeFilter(
        field_name="awareness_at", lookup_expr="lte"
    )
    occurred_after = django_filters.DateTimeFilter(
        field_name="occurred_at", lookup_expr="gte"
    )
    occurred_before = django_filters.DateTimeFilter(
        field_name="occurred_at", lookup_expr="lte"
    )
    closed_after = django_filters.DateTimeFilter(
        field_name="closed_at", lookup_expr="gte"
    )
    closed_before = django_filters.DateTimeFilter(
        field_name="closed_at", lookup_expr="lte"
    )
    has_overdue_notifications = django_filters.BooleanFilter(
        method="filter_has_overdue_notifications"
    )
    has_unsealed_evidence = django_filters.BooleanFilter(
        method="filter_has_unsealed_evidence"
    )
    has_undecided_notifications = django_filters.BooleanFilter(
        method="filter_has_undecided_notifications"
    )
    has_failed_integrity_check = django_filters.BooleanFilter(
        method="filter_has_failed_integrity_check"
    )

    class Meta:
        model = Incident
        fields = {
            "workflow_state": ["exact"],
            "severity": ["exact"],
            "initial_severity": ["exact"],
            "category": ["exact"],
            "detection_source": ["exact"],
            "tlp": ["exact"],
            "is_exercise": ["exact"],
            "personal_data_involved": ["exact"],
            "confidentiality_impact": ["exact"],
            "integrity_impact": ["exact"],
            "availability_impact": ["exact"],
            "is_significant": ["exact"],
            "cross_border_impact": ["exact"],
            "suspected_malicious": ["exact"],
        }

    def _by_related(self, queryset, condition, value):
        """Include or exclude incidents by a condition on a child collection.

        ``exclude()`` on a reverse relation drops a row as soon as **one**
        child matches, which is the wrong answer for "has no overdue
        obligation" : the exclusion is therefore expressed as a subquery over
        the matching ids so an incident with one late and one filed obligation
        is counted late, and only an incident with none at all is excluded.
        """
        if value:
            return queryset.filter(condition).distinct()
        return queryset.exclude(
            pk__in=queryset.model.objects.filter(condition).values("pk")
        )

    def filter_has_overdue_notifications(self, queryset, name, value):
        """The *are we late* question, asked of the incident register."""
        condition = Q(
            notifications__due_at__lt=timezone.now(),
            notifications__sent_at__isnull=True,
        ) & ~Q(
            notifications__workflow_state__in=_terminal_states(IncidentNotification)
        )
        return self._by_related(queryset, condition, value)

    def filter_has_undecided_notifications(self, queryset, name, value):
        """Obligations nobody has ruled on : the Art. 33(1) omission risk."""
        condition = Q(notifications__decision=NotificationDecision.UNDECIDED) & ~Q(
            notifications__workflow_state__in=_terminal_states(IncidentNotification)
        )
        return self._by_related(queryset, condition, value)

    def filter_has_unsealed_evidence(self, queryset, name, value):
        condition = Q(evidence_items__sealed_at__isnull=True)
        return self._by_related(queryset, condition, value)

    def filter_has_failed_integrity_check(self, queryset, name, value):
        """An artefact whose last conclusive verification recorded a break."""
        condition = Q(evidence_items__last_integrity_check_ok=False)
        return self._by_related(queryset, condition, value)

    @property
    def qs(self):
        # The blast-radius joins are many-to-many and duplicate rows.
        return super().qs.distinct()


# --- Chronology --------------------------------------------------------------


class IncidentTimelineEntryFilter(django_filters.FilterSet):
    incident = django_filters.UUIDFilter(field_name="incident_id")
    author = django_filters.UUIDFilter(field_name="author_id")
    related_action = django_filters.UUIDFilter(field_name="related_action_id")
    related_evidence = django_filters.UUIDFilter(field_name="related_evidence_id")
    superseded_entry = django_filters.UUIDFilter(field_name="superseded_entry_id")
    scope = django_filters.UUIDFilter(field_name="incident__scopes__id")
    occurred_after = django_filters.DateTimeFilter(
        field_name="occurred_at", lookup_expr="gte"
    )
    occurred_before = django_filters.DateTimeFilter(
        field_name="occurred_at", lookup_expr="lte"
    )
    is_superseded = django_filters.BooleanFilter(method="filter_is_superseded")

    class Meta:
        model = IncidentTimelineEntry
        fields = {
            "entry_type": ["exact"],
            "source": ["exact"],
            "is_evidence": ["exact"],
        }

    def filter_is_superseded(self, queryset, name, value):
        """Entries a later correction has restated. Never hidden, only marked."""
        return queryset.filter(corrections__isnull=not value).distinct()


# --- Response actions --------------------------------------------------------


class IncidentResponseActionFilter(django_filters.FilterSet):
    incident = django_filters.UUIDFilter(field_name="incident_id")
    owner = django_filters.UUIDFilter(field_name="owner_id")
    performed_by = django_filters.UUIDFilter(field_name="performed_by_id")
    scope = django_filters.UUIDFilter(field_name="incident__scopes__id")
    due_before = django_filters.DateTimeFilter(field_name="due_at", lookup_expr="lte")
    due_after = django_filters.DateTimeFilter(field_name="due_at", lookup_expr="gte")
    completed_after = django_filters.DateTimeFilter(
        field_name="completed_at", lookup_expr="gte"
    )
    completed_before = django_filters.DateTimeFilter(
        field_name="completed_at", lookup_expr="lte"
    )
    overdue = django_filters.BooleanFilter(method="filter_overdue")
    open = django_filters.BooleanFilter(method="filter_open")

    class Meta:
        model = IncidentResponseAction
        fields = {
            "action_type": ["exact"],
            "status": ["exact"],
            "effectiveness": ["exact"],
        }

    #: The row answers none of the governance helpers - it runs no lifecycle -
    #: so "still open" is expressed with the `ResponseActionStatus` constants
    #: and never with a bare string (RG-INC-37).
    _TERMINAL = [ResponseActionStatus.DONE, ResponseActionStatus.CANCELLED]

    def filter_overdue(self, queryset, name, value):
        overdue = Q(due_at__isnull=False, due_at__lt=timezone.now()) & ~Q(
            status__in=self._TERMINAL
        )
        return queryset.filter(overdue) if value else queryset.exclude(overdue)

    def filter_open(self, queryset, name, value):
        if value:
            return queryset.exclude(status__in=self._TERMINAL)
        return queryset.filter(status__in=self._TERMINAL)


# --- Evidence and its chain of custody ---------------------------------------


class IncidentEvidenceFilter(django_filters.FilterSet):
    status = django_filters.CharFilter(field_name="workflow_state")
    incident = django_filters.UUIDFilter(field_name="incident_id")
    scope = django_filters.UUIDFilter(field_name="incident__scopes__id")
    collected_by = django_filters.UUIDFilter(field_name="collected_by_id")
    source_support_asset = django_filters.UUIDFilter(
        field_name="source_support_asset_id"
    )
    collected_after = django_filters.DateTimeFilter(
        field_name="collected_at", lookup_expr="gte"
    )
    collected_before = django_filters.DateTimeFilter(
        field_name="collected_at", lookup_expr="lte"
    )
    retention_before = django_filters.DateFilter(
        field_name="retention_until", lookup_expr="lte"
    )
    retention_after = django_filters.DateFilter(
        field_name="retention_until", lookup_expr="gte"
    )
    last_check_before = django_filters.DateTimeFilter(
        field_name="last_integrity_check_at", lookup_expr="lte"
    )
    sealed = django_filters.BooleanFilter(
        field_name="sealed_at", lookup_expr="isnull", exclude=True
    )
    never_verified = django_filters.BooleanFilter(
        field_name="last_integrity_check_at", lookup_expr="isnull"
    )
    has_file = django_filters.BooleanFilter(method="filter_has_file")
    retention_expired = django_filters.BooleanFilter(method="filter_retention_expired")
    destroyable = django_filters.BooleanFilter(method="filter_destroyable")

    class Meta:
        model = IncidentEvidence
        fields = {
            "workflow_state": ["exact"],
            "evidence_type": ["exact"],
            "hash_algorithm": ["exact"],
            "tlp": ["exact"],
            # The disposal-review question, and the one an inspector asks
            # first : what is currently preserved under legal hold.
            "legal_hold": ["exact"],
            "last_integrity_check_ok": ["exact"],
        }

    def filter_has_file(self, queryset, name, value):
        """Artefacts Cairn holds, as against those registered by reference."""
        held = Q(file__isnull=False) & ~Q(file="")
        return queryset.filter(held) if value else queryset.exclude(held)

    def filter_retention_expired(self, queryset, name, value):
        expired = Q(
            retention_until__isnull=False,
            retention_until__lt=timezone.localdate(),
        )
        return queryset.filter(expired) if value else queryset.exclude(expired)

    def filter_destroyable(self, queryset, name, value):
        """Mirrors ``IncidentEvidence.is_destroyable`` : the data half of GE-04.

        A permission to destroy and never an instruction : the transition and
        its gate are what actually destroy anything.
        """
        destroyable = Q(legal_hold=False) & Q(
            retention_until__isnull=False,
            retention_until__lt=timezone.localdate(),
        )
        return queryset.filter(destroyable) if value else queryset.exclude(destroyable)


class EvidenceCustodyEventFilter(django_filters.FilterSet):
    evidence = django_filters.UUIDFilter(field_name="evidence_id")
    incident = django_filters.UUIDFilter(field_name="evidence__incident_id")
    scope = django_filters.UUIDFilter(field_name="evidence__incident__scopes__id")
    actor = django_filters.UUIDFilter(field_name="actor_id")
    occurred_after = django_filters.DateTimeFilter(
        field_name="occurred_at", lookup_expr="gte"
    )
    occurred_before = django_filters.DateTimeFilter(
        field_name="occurred_at", lookup_expr="lte"
    )
    is_verification = django_filters.BooleanFilter(method="filter_is_verification")

    class Meta:
        model = EvidenceCustodyEvent
        fields = {
            "action": ["exact"],
            "source": ["exact"],
            # Three-valued on purpose : an empty verdict is "no verification
            # concluded", which is not the same claim as a mismatch.
            "integrity_ok": ["exact"],
        }

    def filter_is_verification(self, queryset, name, value):
        if value:
            return queryset.filter(action=CustodyAction.INTEGRITY_VERIFIED)
        return queryset.exclude(action=CustodyAction.INTEGRITY_VERIFIED)


# --- Post-incident review ----------------------------------------------------


class PostIncidentReviewFilter(django_filters.FilterSet):
    status = django_filters.CharFilter(field_name="workflow_state")
    incident = django_filters.UUIDFilter(field_name="incident_id")
    scope = django_filters.UUIDFilter(field_name="scopes__id")
    facilitator = django_filters.UUIDFilter(field_name="facilitator_id")
    participant = django_filters.UUIDFilter(field_name="participants__id")
    response_plan = django_filters.UUIDFilter(field_name="response_plan_id")
    effectiveness_reviewed_by = django_filters.UUIDFilter(
        field_name="effectiveness_reviewed_by_id"
    )
    raised_finding = django_filters.UUIDFilter(field_name="raised_findings__id")
    corrective_action_plan = django_filters.UUIDFilter(
        field_name="corrective_action_plans__id"
    )
    identified_risk = django_filters.UUIDFilter(field_name="identified_risks__id")
    scheduled_after = django_filters.DateFilter(
        field_name="scheduled_date", lookup_expr="gte"
    )
    scheduled_before = django_filters.DateFilter(
        field_name="scheduled_date", lookup_expr="lte"
    )
    effectiveness_review_before = django_filters.DateFilter(
        field_name="effectiveness_review_date", lookup_expr="lte"
    )
    effectiveness_review_after = django_filters.DateFilter(
        field_name="effectiveness_review_date", lookup_expr="gte"
    )
    effectiveness_overdue = django_filters.BooleanFilter(
        method="filter_effectiveness_overdue"
    )

    class Meta:
        model = PostIncidentReview
        fields = {
            "workflow_state": ["exact"],
            "root_cause_method": ["exact"],
            "recurrence_likelihood": ["exact"],
            "effectiveness_verdict": ["exact"],
            "risk_reassessment_required": ["exact"],
            "response_plan_update_required": ["exact"],
            "training_required": ["exact"],
            "similar_incidents_checked": ["exact"],
        }

    def filter_effectiveness_overdue(self, queryset, name, value):
        """An open clause 10.2 d) obligation nobody has answered.

        Expressed as *the verification date has passed and no verification has
        been stamped*, on a review that has not reached a terminal step. That
        is the fact the auditor asks about, and stating it this way keeps the
        filter free of any step code : the stamp is written by the
        effectiveness-verification transition and by nothing else, so its
        absence is exactly "not yet verified".
        """
        overdue = Q(
            effectiveness_review_date__isnull=False,
            effectiveness_review_date__lt=timezone.localdate(),
            effectiveness_reviewed_at__isnull=True,
        ) & ~Q(workflow_state__in=_terminal_states(PostIncidentReview))
        return queryset.filter(overdue) if value else queryset.exclude(overdue)

    @property
    def qs(self):
        # `participant` and the three outward-link filters join many-to-many.
        return super().qs.distinct()


# --- Regulatory catalogue ----------------------------------------------------


class ReportingAuthorityFilter(django_filters.FilterSet):
    status = django_filters.CharFilter(field_name="workflow_state")
    jurisdiction_country = django_filters.CharFilter(lookup_expr="iexact")
    usable = django_filters.BooleanFilter(method="filter_usable")

    class Meta:
        model = ReportingAuthority
        fields = {
            "workflow_state": ["exact"],
            "authority_type": ["exact"],
            "primary_regime": ["exact"],
            "notification_language": ["exact"],
        }

    def filter_usable(self, queryset, name, value):
        """Authorities trustworthy enough to generate obligations from."""
        states = reportable_states(ReportingAuthority)
        if value:
            return queryset.filter(workflow_state__in=states)
        return queryset.exclude(workflow_state__in=states)


class ReportingObligationTemplateFilter(django_filters.FilterSet):
    status = django_filters.CharFilter(field_name="workflow_state")
    authority = django_filters.UUIDFilter(field_name="authority_id")
    jurisdiction_country = django_filters.CharFilter(lookup_expr="iexact")
    in_force = django_filters.BooleanFilter(method="filter_in_force")

    class Meta:
        model = ReportingObligationTemplate
        fields = {
            "workflow_state": ["exact"],
            "regime": ["exact"],
            "recipient_kind": ["exact"],
            "clock_anchor": ["exact"],
            "clock_hours": ["exact"],
            "depends_on_regime": ["exact"],
            "min_severity": ["exact"],
            "no_fixed_deadline": ["exact"],
            "requires_significant": ["exact"],
            "requires_personal_data": ["exact"],
            "requires_high_risk": ["exact"],
            "requires_cross_border": ["exact"],
        }

    def filter_in_force(self, queryset, name, value):
        """RG-INC-30 : the templates obligation generation may actually fire."""
        states = reportable_states(ReportingObligationTemplate)
        if value:
            return queryset.filter(workflow_state__in=states)
        return queryset.exclude(workflow_state__in=states)


# --- Notification obligations and their filings ------------------------------


class IncidentNotificationFilter(django_filters.FilterSet):
    status = django_filters.CharFilter(field_name="workflow_state")
    incident = django_filters.UUIDFilter(field_name="incident_id")
    scope = django_filters.UUIDFilter(field_name="incident__scopes__id")
    authority = django_filters.UUIDFilter(field_name="authority_id")
    template = django_filters.UUIDFilter(field_name="template_id")
    depends_on = django_filters.UUIDFilter(field_name="depends_on_id")
    recipient_stakeholder = django_filters.UUIDFilter(
        field_name="recipient_stakeholder_id"
    )
    recipient_supplier = django_filters.UUIDFilter(field_name="recipient_supplier_id")
    incident_severity = django_filters.CharFilter(field_name="incident__severity")
    due_before = django_filters.DateTimeFilter(field_name="due_at", lookup_expr="lte")
    due_after = django_filters.DateTimeFilter(field_name="due_at", lookup_expr="gte")
    sent_after = django_filters.DateTimeFilter(
        field_name="sent_at", lookup_expr="gte"
    )
    sent_before = django_filters.DateTimeFilter(
        field_name="sent_at", lookup_expr="lte"
    )
    overdue = django_filters.BooleanFilter(method="filter_overdue")
    undecided = django_filters.BooleanFilter(method="filter_undecided")
    filed = django_filters.BooleanFilter(
        field_name="first_submitted_at", lookup_expr="isnull", exclude=True
    )
    was_filed_late = django_filters.BooleanFilter(
        field_name="late_by", lookup_expr="isnull", exclude=True
    )
    due_within_hours = django_filters.NumberFilter(method="filter_due_within_hours")

    class Meta:
        model = IncidentNotification
        fields = {
            "workflow_state": ["exact"],
            "regime": ["exact"],
            "recipient_kind": ["exact"],
            "decision": ["exact"],
            "clock_anchor": ["exact"],
            "channel": ["exact"],
            "source": ["exact"],
            "no_fixed_deadline": ["exact"],
        }

    def filter_overdue(self, queryset, name, value):
        """The deadline has passed with no filing recorded.

        Always derived, never stored : there is no overdue column to fall out
        of date the instant the clock runs out (RG-INC-28). An obligation in a
        terminal step is never late : the duty is closed.
        """
        overdue = Q(due_at__lt=timezone.now()) & _open_obligations()
        return queryset.filter(overdue) if value else queryset.exclude(overdue)

    def filter_undecided(self, queryset, name, value):
        """Obligations nobody has ruled on. Visible, never absent."""
        if value:
            return queryset.filter(decision=NotificationDecision.UNDECIDED)
        return queryset.exclude(decision=NotificationDecision.UNDECIDED)

    def filter_due_within_hours(self, queryset, name, value):
        """The *due in 24 h* rail : still open, and the clock nearly out."""
        if value in (None, ""):
            return queryset
        horizon = timezone.now() + timedelta(hours=float(value))
        return queryset.filter(Q(due_at__lte=horizon) & _open_obligations())


class NotificationFilingFilter(django_filters.FilterSet):
    notification = django_filters.UUIDFilter(field_name="notification_id")
    incident = django_filters.UUIDFilter(field_name="notification__incident_id")
    scope = django_filters.UUIDFilter(
        field_name="notification__incident__scopes__id"
    )
    regime = django_filters.CharFilter(field_name="notification__regime")
    submitted_by = django_filters.UUIDFilter(field_name="submitted_by_id")
    supersedes = django_filters.UUIDFilter(field_name="supersedes_id")
    submitted_after = django_filters.DateTimeFilter(
        field_name="submitted_at", lookup_expr="gte"
    )
    submitted_before = django_filters.DateTimeFilter(
        field_name="submitted_at", lookup_expr="lte"
    )
    acknowledged = django_filters.BooleanFilter(
        field_name="acknowledged_at", lookup_expr="isnull", exclude=True
    )
    is_superseded = django_filters.BooleanFilter(method="filter_is_superseded")

    class Meta:
        model = NotificationFiling
        fields = {
            "channel": ["exact"],
            "outcome": ["exact"],
            "is_correction": ["exact"],
            "was_late": ["exact"],
        }

    def filter_is_superseded(self, queryset, name, value):
        """Derived from the reverse relation, never from a stored outcome."""
        return queryset.filter(superseded_by__isnull=not value).distinct()


# --- Personal data breach ----------------------------------------------------


class PersonalDataBreachFilter(django_filters.FilterSet):
    status = django_filters.CharFilter(field_name="workflow_state")
    incident = django_filters.UUIDFilter(field_name="incident_id")
    scope = django_filters.UUIDFilter(field_name="incident__scopes__id")
    lead_authority = django_filters.UUIDFilter(field_name="lead_authority_id")
    controller_supplier = django_filters.UUIDFilter(
        field_name="controller_supplier_id"
    )
    qualified_by = django_filters.UUIDFilter(field_name="qualified_by_id")
    qualified_after = django_filters.DateTimeFilter(
        field_name="qualified_at", lookup_expr="gte"
    )
    qualified_before = django_filters.DateTimeFilter(
        field_name="qualified_at", lookup_expr="lte"
    )
    min_data_subjects = django_filters.NumberFilter(
        field_name="approximate_data_subjects", lookup_expr="gte"
    )

    class Meta:
        model = PersonalDataBreach
        fields = {
            "workflow_state": ["exact"],
            "controller_role": ["exact"],
            # Three-valued : a null Art. 34 determination is "not decided yet"
            # and must never read as a recorded no.
            "high_risk_to_rights": ["exact"],
            "special_categories": ["exact"],
            "article_34_exemption": ["exact"],
            "cross_border_eu": ["exact"],
            "volume_is_estimate": ["exact"],
        }
