# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""DRF serializers for module 6 (incidents).

Three rules govern this whole file and are worth stating once rather than
repeating in thirteen docstrings :

**`workflow_state` is never writable.** Every lifecycle entity exposes it as
``status = CharField(source="workflow_state", read_only=True)`` and nothing
else. A state change is a transition, routed through ``transition_to()``, which
is where the gates, the stamps and the immutable ``LifecycleEvent`` live. A
serializer that let a client PATCH the column would bypass all three at once.

**Write-once fields are `read_only`, not merely guarded.** The models refuse the
write in ``save()`` too, and that guard is the real one. Declaring the field
read-only here is what turns a 500 from a model-level ``ValidationError`` into
a field that simply is not part of the API contract, and it is what stops a
generated client from offering the write at all.

**File payloads never appear.** ``IncidentEvidence.file`` and the two
``proof_file_content`` columns are absent from every serializer, list and
detail alike : the bytes are reachable only through the dedicated
permission-checked and scope-checked download actions.

Foreign-key display companions (``owner_name``, ``incident_reference``,
``authority_name``) are read-only fields backed by a model ``@property``. The
properties already exist on the models ; nothing here invents one.
"""

import copy

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.settings import api_settings

from incidents.constants import NotificationRegime
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
from incidents.models.evidence import EVIDENCE_ACQUISITION_FIELDS
from incidents.models.notification import (
    FILING_COMPLETION_FIELDS,
    NOTIFICATION_FILED_FROZEN_FIELDS,
    ObligationSource,
)


# --- Shared behaviour --------------------------------------------------------


class _CleanedModelSerializer(serializers.ModelSerializer):
    """Run the model's own ``clean()`` as part of serializer validation.

    ``ModelSerializer`` does not call ``full_clean()``, so every cross-field
    rule a model states in ``clean()`` - the two incident clocks, the custody
    ledger's monotonicity, the Art. 34(3) justification, the obligation's
    deadline coherence - would hold on the web form and be silently absent from
    the API. The rules are declared once on the model and enforced identically
    on all three write surfaces by running them here.

    The instance is built in memory from the non-M2M validated data (an unsaved
    model cannot hold a many-to-many), so nothing is written and no query is
    issued beyond the ones ``clean()`` performs itself.
    """

    def validate(self, attrs):
        attrs = super().validate(attrs)
        candidate = self._instance_for_clean(attrs)
        try:
            candidate.clean()
            # `clean()` alone is not the whole model contract : a conditional
            # UniqueConstraint is checked by `validate_constraints()`, which
            # ModelSerializer never calls either. Without it a duplicate row
            # reaches the database and surfaces as a 500 IntegrityError while
            # the same payload is refused cleanly by the form and by MCP.
            candidate.validate_constraints()
        except DjangoValidationError as exc:
            raise serializers.ValidationError(_drf_errors(exc)) from exc
        return attrs

    def _instance_for_clean(self, attrs):
        model = self.Meta.model
        many_to_many = {field.name for field in model._meta.many_to_many}
        data = {key: value for key, value in attrs.items() if key not in many_to_many}
        instance = _edited_instance(self)
        if instance is None:
            return model(**data)
        # A shallow copy so the rules are evaluated against the row as it would
        # be after the write, without mutating the instance the view still
        # holds if validation then fails.
        candidate = copy.copy(instance)
        for key, value in data.items():
            setattr(candidate, key, value)
        return candidate


def _drf_errors(exc):
    """Translate a Django ``ValidationError`` into DRF's error shape."""
    if hasattr(exc, "message_dict"):
        errors = dict(exc.message_dict)
        non_field = errors.pop("__all__", None)
        if non_field:
            errors[api_settings.NON_FIELD_ERRORS_KEY] = non_field
        return errors
    return {api_settings.NON_FIELD_ERRORS_KEY: list(exc.messages)}


def _edited_instance(serializer):
    """The single row this serializer is updating, or ``None``.

    ``many=True`` builds the child serializer by passing it every argument the
    parent got (DRF's ``BaseSerializer.many_init``), so a child rendering a
    list carries the **queryset** as its ``instance``. Any hook that reasons
    about "the row being updated" - the conditional freezes below - has to
    establish that there is one before touching an attribute on it.
    """
    instance = serializer.instance
    return instance if isinstance(instance, models.Model) else None


def _freeze(serializer, *field_names):
    """Make already-bound fields read-only for this serializer instance.

    Used for the conditionally frozen sets : the acquisition metadata of a
    sealed evidence item, the transmitted content of a filed obligation, and
    the parent link of a child row that inherits its parent's tenancy.
    """
    for name in field_names:
        field = serializer.fields.get(name)
        if field is not None:
            field.read_only = True
            field.required = False


class _ParentLockedMixin:
    """Accept the parent link on create, refuse to re-point it on update.

    Every child in this module inherits its scopes from its parent through
    ``scope_parent_lookup``. Re-pointing an existing row at a different parent
    would move it into another perimeter in one PATCH, taking its evidence
    hashes, its filing content or its breach volumes with it, and would strand
    whatever the original parent still refers to. Creation sets it ; nothing
    changes it afterwards.
    """

    parent_field = "incident"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if _edited_instance(self) is not None:
            _freeze(self, self.parent_field)


# --- Incident response plan (A.5.24) ----------------------------------------


class IncidentResponsePlanSerializer(_CleanedModelSerializer):
    status = serializers.CharField(source="workflow_state", read_only=True)
    owner_name = serializers.CharField(read_only=True)
    approved_by_name = serializers.CharField(read_only=True)
    applicable_regime_labels = serializers.ListField(
        child=serializers.CharField(), read_only=True
    )
    is_in_force = serializers.BooleanField(read_only=True)
    is_review_overdue = serializers.BooleanField(read_only=True)
    is_exercise_overdue = serializers.BooleanField(read_only=True)

    class Meta:
        model = IncidentResponsePlan
        fields = [
            "id", "scopes", "reference", "name", "purpose", "procedure",
            "classification_scale", "escalation_matrix", "reporting_channels",
            "evidence_procedure", "lessons_learned_procedure",
            "applicable_regimes", "applicable_regime_labels",
            "owner", "owner_name", "approved_by", "approved_by_name",
            "approved_at", "effective_from", "review_date",
            "last_exercise_date",
            "is_in_force", "is_review_overdue", "is_exercise_overdue",
            "responsible_roles", "linked_requirements",
            "status", "tags", "version",
            "created_by", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "reference", "created_by", "created_at", "updated_at",
            "version",
            # RG-INC-17 : written only by `record_exercise()`, called from the
            # incident closure transition. A hand-typed plan-testing date is
            # worthless as A.5.24 evidence.
            "last_exercise_date",
        ]

    def validate_applicable_regimes(self, value):
        """Refuse a regime code that would silently generate no obligation."""
        if value in (None, ""):
            return []
        if not isinstance(value, list):
            raise serializers.ValidationError(_("Applicable regimes must be a list."))
        valid = set(NotificationRegime.values)
        unknown = [regime for regime in value if regime not in valid]
        if unknown:
            raise serializers.ValidationError(
                _("Unknown notification regimes : %(values)s")
                % {"values": ", ".join(str(item) for item in unknown)}
            )
        return value


class IncidentResponsePlanListSerializer(serializers.ModelSerializer):
    status = serializers.CharField(source="workflow_state", read_only=True)
    owner_name = serializers.CharField(read_only=True)
    is_in_force = serializers.BooleanField(read_only=True)
    is_review_overdue = serializers.BooleanField(read_only=True)
    is_exercise_overdue = serializers.BooleanField(read_only=True)

    class Meta:
        model = IncidentResponsePlan
        fields = [
            "id", "scopes", "reference", "name",
            "owner", "owner_name", "applicable_regimes",
            "effective_from", "review_date", "last_exercise_date",
            "is_in_force", "is_review_overdue", "is_exercise_overdue",
            "status", "created_at",
        ]
        read_only_fields = ["id", "reference", "created_at"]


# --- Security event (A.6.8 intake / A.5.25 assessment) ----------------------


class SecurityEventSerializer(_CleanedModelSerializer):
    status = serializers.CharField(source="workflow_state", read_only=True)
    reporter_name = serializers.CharField(read_only=True)
    assessed_by_name = serializers.CharField(read_only=True)
    incident_reference = serializers.CharField(read_only=True)
    vulnerability_reference = serializers.CharField(read_only=True)
    duplicate_of_reference = serializers.CharField(read_only=True)
    reported_by_supplier_name = serializers.CharField(read_only=True)
    reporting_delay = serializers.DurationField(read_only=True)
    reporting_delay_hours = serializers.FloatField(read_only=True)

    class Meta:
        model = SecurityEvent
        fields = [
            "id", "scopes", "reference", "title", "description",
            "event_class", "category", "detection_source", "source_reference",
            "occurred_at", "detected_at", "reported_at",
            "reporting_delay", "reporting_delay_hours",
            "reporter", "reporter_name", "reporter_label", "is_anonymous",
            "assessed_by", "assessed_by_name", "assessed_at",
            "assessment_notes", "triage_decision",
            "incident", "incident_reference",
            "vulnerability", "vulnerability_reference",
            "duplicate_of", "duplicate_of_reference",
            "reported_by_supplier", "reported_by_supplier_name",
            "affected_essential_assets", "affected_support_assets",
            "affected_sites",
            "status", "tags", "version",
            "created_by", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "reference", "created_by", "created_at", "updated_at",
            "version",
            # Stamped by the `under_assessment` transition (RG-INC-12) : who
            # assessed, and when, is the record the A.5.25 decision rests on.
            "assessed_at", "assessed_by",
            # Mirrors the lifecycle step and is written by the same transition.
            "triage_decision",
            # Promotion is a transition (`promote_to_incident` /
            # `promote_to_vulnerability`), never a field write : both columns
            # are half of a `CheckConstraint` pairing them with the verdict
            # above, so a direct write could only ever break that pair.
            "incident", "vulnerability",
        ]


class SecurityEventListSerializer(serializers.ModelSerializer):
    status = serializers.CharField(source="workflow_state", read_only=True)
    reporter_name = serializers.CharField(read_only=True)
    incident_reference = serializers.CharField(read_only=True)
    reporting_delay_hours = serializers.FloatField(read_only=True)

    class Meta:
        model = SecurityEvent
        fields = [
            "id", "scopes", "reference", "title",
            "event_class", "category", "detection_source",
            "detected_at", "reported_at", "reporting_delay_hours",
            "is_anonymous", "reporter", "reporter_name",
            "triage_decision", "incident", "incident_reference",
            "status", "created_at",
        ]
        read_only_fields = ["id", "reference", "created_at"]


# --- Incident (A.5.26) -------------------------------------------------------


#: Written by `Incident._stamp_transition()` and by nothing else (RG-INC-12,
#: G-08). Write-once in both directions : a set stamp is never rewritten, and
#: only the matching reopen edge clears it.
INCIDENT_PHASE_STAMP_FIELDS = (
    "declared_at",
    "triaged_at",
    "contained_at",
    "eradicated_at",
    "recovered_at",
    "closed_at",
)


class IncidentSerializer(_CleanedModelSerializer):
    status = serializers.CharField(source="workflow_state", read_only=True)
    response_plan_name = serializers.CharField(read_only=True)
    reporter_name = serializers.CharField(read_only=True)
    incident_manager_name = serializers.CharField(read_only=True)
    origin_supplier_name = serializers.CharField(read_only=True)
    parent_incident_reference = serializers.CharField(read_only=True)
    awareness_gap = serializers.DurationField(read_only=True)
    time_to_contain = serializers.DurationField(read_only=True)
    time_to_recover = serializers.DurationField(read_only=True)
    severity_raised_since_triage = serializers.BooleanField(read_only=True)

    class Meta:
        model = Incident
        fields = [
            "id", "scopes", "reference", "title", "summary", "description",
            "category", "severity", "initial_severity",
            "severity_raised_since_triage",
            "detection_source", "is_exercise", "tlp",
            "confidentiality_impact", "integrity_impact", "availability_impact",
            "personal_data_involved",
            "occurred_at", "detected_at", "awareness_at",
            "awareness_justification", "awareness_gap",
            "declared_at", "triaged_at", "contained_at", "eradicated_at",
            "recovered_at", "closed_at",
            "time_to_contain", "time_to_recover",
            "outage_duration", "estimated_cost", "no_obligation_justification",
            "is_significant", "significance_determined_at",
            "significance_justification",
            "cross_border_impact", "cross_border_justification",
            "suspected_malicious", "suspected_malicious_justification",
            "response_plan", "response_plan_name",
            "reporter", "reporter_name",
            "incident_manager", "incident_manager_name",
            "parent_incident", "parent_incident_reference",
            "origin_supplier", "origin_supplier_name",
            "affected_suppliers", "affected_essential_assets",
            "affected_support_assets", "affected_sites", "affected_activities",
            "threats", "exploited_vulnerabilities", "realised_risks",
            "linked_requirements",
            "status", "tags", "version",
            "created_by", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "reference", "created_by", "created_at", "updated_at",
            "version",
            # Copied once by the triage transition, so severity drift after
            # triage reads as a difference between two columns rather than as a
            # history diff nobody opens.
            "initial_severity",
            *INCIDENT_PHASE_STAMP_FIELDS,
        ]


class IncidentListSerializer(serializers.ModelSerializer):
    status = serializers.CharField(source="workflow_state", read_only=True)
    incident_manager_name = serializers.CharField(read_only=True)
    reporter_name = serializers.CharField(read_only=True)
    origin_supplier_name = serializers.CharField(read_only=True)

    class Meta:
        model = Incident
        fields = [
            "id", "scopes", "reference", "title",
            "category", "severity", "initial_severity",
            "detection_source", "is_exercise", "tlp",
            "personal_data_involved", "is_significant",
            "occurred_at", "detected_at", "awareness_at", "closed_at",
            "incident_manager", "incident_manager_name",
            "reporter", "reporter_name",
            "origin_supplier", "origin_supplier_name",
            "status", "created_at",
        ]
        read_only_fields = ["id", "reference", "created_at"]


# --- Chronology (append-only) ------------------------------------------------


class IncidentTimelineEntrySerializer(_ParentLockedMixin, _CleanedModelSerializer):
    """One appended line of an incident's chronology.

    Every field is effectively create-only : ``IncidentTimelineEntry.save()``
    refuses any write against an existing row and ``delete()`` refuses outright,
    so the viewset exposes create, list and retrieve and nothing else. A factual
    error is fixed by appending a ``correction`` that names the entry it
    supersedes and states why.
    """

    incident_reference = serializers.CharField(read_only=True)
    author_name = serializers.CharField(read_only=True)
    related_action_reference = serializers.CharField(read_only=True)
    related_evidence_reference = serializers.CharField(read_only=True)
    is_superseded = serializers.BooleanField(read_only=True)
    recording_delay = serializers.DurationField(read_only=True)

    class Meta:
        model = IncidentTimelineEntry
        fields = [
            "id", "incident", "incident_reference",
            "occurred_at", "recorded_at", "recording_delay",
            "entry_type", "summary", "detail", "source",
            "author", "author_name",
            "related_action", "related_action_reference",
            "related_evidence", "related_evidence_reference",
            "superseded_entry", "correction_reason", "is_superseded",
            "is_evidence", "version", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "recorded_at", "created_at", "updated_at", "version",
            # Stamped from the request user : an unattributed line in an
            # incident chronology is not evidence, and a client must not be able
            # to sign one in somebody else's name.
            "author",
            # Provenance, not data. `lifecycle` and `system` mean the platform
            # appended the line; a client claiming either would forge the one
            # signal that distinguishes an automatic entry from a typed one.
            "source",
        ]


# --- Response actions (the one writable `status` in the module) --------------


class IncidentResponseActionSerializer(_ParentLockedMixin, _CleanedModelSerializer):
    """One operational step of the response.

    The only entity in the module whose ``status`` is a genuine model field
    rather than a read-only alias of ``workflow_state`` : the row runs no
    lifecycle and follows its parent incident's governance, so moving it from
    planned to done during a live incident is a plain field write by design.
    """

    incident_reference = serializers.CharField(read_only=True)
    owner_name = serializers.CharField(read_only=True)
    performed_by_name = serializers.CharField(read_only=True)
    is_terminal = serializers.BooleanField(read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)
    execution_duration = serializers.DurationField(read_only=True)

    class Meta:
        model = IncidentResponseAction
        fields = [
            "id", "incident", "incident_reference", "reference",
            "action_type", "title", "description", "status",
            "owner", "owner_name", "performed_by", "performed_by_name",
            "due_at", "started_at", "completed_at", "execution_duration",
            "is_overdue", "is_terminal",
            "outcome", "effectiveness",
            "version", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "reference", "created_at", "updated_at", "version",
        ]


# --- Evidence (A.5.28) -------------------------------------------------------


class IncidentEvidenceSerializer(_ParentLockedMixin, _CleanedModelSerializer):
    """One item of the evidence register.

    The ``file`` payload is deliberately absent from the field list : the bytes
    are reachable only through the ``download`` action, which checks
    ``incidents.evidence.read`` and the caller's scopes through
    ``incident__scopes``. The list exposes ``has_file``, ``file_size`` and
    ``original_filename`` so a reader can always tell an artefact Cairn holds
    from one registered by reference.

    Once the item is sealed, the acquisition metadata is frozen : the six
    fields of ``EVIDENCE_ACQUISITION_FIELDS`` become read-only on this
    serializer, matching the guard ``IncidentEvidence.save()`` applies to every
    write path.
    """

    status = serializers.CharField(source="workflow_state", read_only=True)
    incident_reference = serializers.CharField(read_only=True)
    incident_name = serializers.CharField(read_only=True)
    collected_by_name = serializers.CharField(read_only=True)
    source_support_asset_name = serializers.CharField(read_only=True)
    source_support_asset_reference = serializers.CharField(read_only=True)
    destruction_authorised_by_name = serializers.CharField(read_only=True)
    has_file = serializers.BooleanField(read_only=True)
    is_registered_by_reference = serializers.BooleanField(read_only=True)
    is_sealed = serializers.BooleanField(read_only=True)
    retention_expired = serializers.BooleanField(read_only=True)
    is_destroyable = serializers.BooleanField(read_only=True)

    class Meta:
        model = IncidentEvidence
        fields = [
            "id", "incident", "incident_reference", "incident_name",
            "reference", "title", "description", "evidence_type",
            "collected_at", "collected_by", "collected_by_name",
            "collection_method",
            "source_support_asset", "source_support_asset_name",
            "source_support_asset_reference", "source_description",
            "storage_location",
            "original_filename", "file_size",
            "has_file", "is_registered_by_reference",
            "content_hash", "hash_algorithm",
            "sealed_at", "is_sealed",
            "last_integrity_check_at", "last_integrity_check_ok",
            "tlp", "legal_hold",
            "retention_until", "retention_expired", "is_destroyable",
            "admissibility_notes",
            "destruction_authorised_by", "destruction_authorised_by_name",
            "status", "tags", "version",
            "created_by", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "reference", "created_by", "created_at", "updated_at",
            "version",
            # GE-06 / RG-INC-12 : stamped by the sealing, destruction and
            # verification paths, write-once on every surface. A destruction
            # authorisation a client could assert is not an authorisation.
            "sealed_at", "destruction_authorised_by",
            "last_integrity_check_at", "last_integrity_check_ok",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        instance = _edited_instance(self)
        if instance is not None and instance.is_sealed:
            _freeze(self, *EVIDENCE_ACQUISITION_FIELDS)


class IncidentEvidenceListSerializer(serializers.ModelSerializer):
    status = serializers.CharField(source="workflow_state", read_only=True)
    incident_reference = serializers.CharField(read_only=True)
    collected_by_name = serializers.CharField(read_only=True)
    has_file = serializers.BooleanField(read_only=True)
    is_sealed = serializers.BooleanField(read_only=True)
    retention_expired = serializers.BooleanField(read_only=True)

    class Meta:
        model = IncidentEvidence
        fields = [
            "id", "incident", "incident_reference", "reference", "title",
            "evidence_type", "collected_at", "collected_by",
            "collected_by_name",
            "has_file", "file_size", "original_filename", "storage_location",
            "content_hash", "hash_algorithm", "is_sealed", "sealed_at",
            "last_integrity_check_at", "last_integrity_check_ok",
            "tlp", "legal_hold", "retention_until", "retention_expired",
            "status", "created_at",
        ]
        read_only_fields = ["id", "reference", "created_at"]


class EvidenceCustodyEventSerializer(_ParentLockedMixin, _CleanedModelSerializer):
    """One appended handling act on an evidence item.

    Append-only : ``save()`` refuses a write against an existing row and
    ``delete()`` refuses outright, so the viewset is create, list and retrieve
    only. ``clean()`` runs here too, so an API caller can no more append a
    handover to nobody, a verdict with no measurement, or an act that predates
    the last recorded one than a form user can.
    """

    parent_field = "evidence"

    evidence_reference = serializers.CharField(read_only=True)
    evidence_name = serializers.CharField(read_only=True)
    incident_reference = serializers.CharField(read_only=True)
    actor_name = serializers.CharField(read_only=True)
    is_verification = serializers.BooleanField(read_only=True)
    verification_outcome = serializers.CharField(read_only=True)
    recording_delay = serializers.DurationField(read_only=True)

    class Meta:
        model = EvidenceCustodyEvent
        fields = [
            "id", "evidence", "evidence_reference", "evidence_name",
            "incident_reference",
            "action", "occurred_at", "recorded_at", "recording_delay",
            "actor", "actor_name",
            "counterparty", "counterparty_organisation", "location",
            "hash_at_event", "integrity_ok",
            "is_verification", "verification_outcome",
            "notes", "source",
            "version", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "recorded_at", "created_at", "updated_at", "version",
            # Stamped from the request user : a custody act attributed to
            # somebody the caller nominated is a custody act attributed to
            # nobody.
            "actor",
            # Provenance : `lifecycle` means the platform appended the row from
            # a transition, and a client must not be able to claim it.
            "source",
        ]


# --- Post-incident review (A.5.27 / clause 10.2) -----------------------------


class PostIncidentReviewSerializer(_ParentLockedMixin, _CleanedModelSerializer):
    status = serializers.CharField(source="workflow_state", read_only=True)
    incident_reference = serializers.CharField(read_only=True)
    incident_title = serializers.CharField(read_only=True)
    response_plan_name = serializers.CharField(read_only=True)
    facilitator_name = serializers.CharField(read_only=True)
    effectiveness_reviewed_by_name = serializers.CharField(read_only=True)
    is_effectiveness_overdue = serializers.BooleanField(read_only=True)

    class Meta:
        model = PostIncidentReview
        fields = [
            "id", "scopes", "reference",
            "incident", "incident_reference", "incident_title",
            "response_plan", "response_plan_name",
            "scheduled_date", "held_at",
            "facilitator", "facilitator_name", "participants",
            "root_cause_method", "root_cause", "contributing_factors",
            "detection_gap", "containment_assessment",
            "what_went_well", "what_failed",
            "recurrence_likelihood", "similar_incidents_checked",
            "risk_reassessment_required", "response_plan_update_required",
            "training_required",
            "effectiveness_review_date", "is_effectiveness_overdue",
            "effectiveness_reviewed_at",
            "effectiveness_reviewed_by", "effectiveness_reviewed_by_name",
            "effectiveness_verdict", "effectiveness_notes",
            "raised_findings", "corrective_action_plans",
            "failed_controls", "controls_to_strengthen",
            "identified_risks", "identified_vulnerabilities", "isms_changes",
            "status", "tags", "version",
            "created_by", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "reference", "created_by", "created_at", "updated_at",
            "version",
            # RG-INC-12 : `held_at` is stamped by `scheduled -> in_progress`
            # and `effectiveness_reviewed_at` by the effectiveness
            # verification. Both are write-once and survive a send-back loop.
            "held_at", "effectiveness_reviewed_at",
            # RG-INC-31 : the review's tenancy is the incident's, re-synced by
            # `Incident.save()`. A writable copy could only ever drift until the
            # next incident save silently reverted it.
            "scopes",
        ]


class PostIncidentReviewListSerializer(serializers.ModelSerializer):
    status = serializers.CharField(source="workflow_state", read_only=True)
    incident_reference = serializers.CharField(read_only=True)
    incident_title = serializers.CharField(read_only=True)
    facilitator_name = serializers.CharField(read_only=True)
    is_effectiveness_overdue = serializers.BooleanField(read_only=True)

    class Meta:
        model = PostIncidentReview
        fields = [
            "id", "scopes", "reference",
            "incident", "incident_reference", "incident_title",
            "scheduled_date", "held_at",
            "facilitator", "facilitator_name",
            "root_cause_method", "recurrence_likelihood",
            "effectiveness_review_date", "is_effectiveness_overdue",
            "effectiveness_verdict",
            "risk_reassessment_required", "response_plan_update_required",
            "training_required",
            "status", "created_at",
        ]
        read_only_fields = ["id", "reference", "created_at"]


# --- Regulatory catalogue ----------------------------------------------------


class ReportingAuthoritySerializer(_CleanedModelSerializer):
    status = serializers.CharField(source="workflow_state", read_only=True)
    display_name = serializers.CharField(read_only=True)
    default_recipient_kind = serializers.CharField(read_only=True)

    class Meta:
        model = ReportingAuthority
        fields = [
            "id", "reference", "name", "short_name", "display_name",
            "authority_type", "primary_regime", "additional_regimes",
            "jurisdiction_country",
            "portal_url", "contact_email", "contact_phone",
            "notification_language", "procedure",
            "default_recipient_kind",
            "status", "tags", "version",
            "created_by", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "reference", "created_by", "created_at", "updated_at",
            "version",
        ]


class ReportingAuthorityListSerializer(serializers.ModelSerializer):
    status = serializers.CharField(source="workflow_state", read_only=True)
    display_name = serializers.CharField(read_only=True)

    class Meta:
        model = ReportingAuthority
        fields = [
            "id", "reference", "name", "short_name", "display_name",
            "authority_type", "primary_regime", "additional_regimes",
            "jurisdiction_country", "portal_url", "notification_language",
            "status", "created_at",
        ]
        read_only_fields = ["id", "reference", "created_at"]


class ReportingObligationTemplateSerializer(_CleanedModelSerializer):
    status = serializers.CharField(source="workflow_state", read_only=True)
    authority_name = serializers.CharField(read_only=True)
    clock_summary = serializers.CharField(read_only=True)

    class Meta:
        model = ReportingObligationTemplate
        fields = [
            "id", "reference", "name",
            "authority", "authority_name",
            "regime", "recipient_kind", "legal_reference",
            "content_requirements",
            "clock_anchor", "clock_hours", "no_fixed_deadline",
            "depends_on_regime", "clock_summary",
            "jurisdiction_country", "min_severity",
            "requires_significant", "requires_personal_data",
            "requires_high_risk", "requires_cross_border",
            "controller_roles", "applicable_categories",
            "order",
            "status", "tags", "version",
            "created_by", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "reference", "created_by", "created_at", "updated_at",
            "version",
        ]


class ReportingObligationTemplateListSerializer(serializers.ModelSerializer):
    status = serializers.CharField(source="workflow_state", read_only=True)
    authority_name = serializers.CharField(read_only=True)
    clock_summary = serializers.CharField(read_only=True)

    class Meta:
        model = ReportingObligationTemplate
        fields = [
            "id", "reference", "name",
            "authority", "authority_name",
            "regime", "recipient_kind", "legal_reference",
            "clock_anchor", "clock_hours", "no_fixed_deadline",
            "clock_summary", "jurisdiction_country", "min_severity",
            "requires_significant", "requires_personal_data",
            "requires_high_risk", "requires_cross_border",
            "order", "status", "created_at",
        ]
        read_only_fields = ["id", "reference", "created_at"]


# --- Notification obligations and their filings ------------------------------


class IncidentNotificationSerializer(_ParentLockedMixin, _CleanedModelSerializer):
    """One regulatory or contractual obligation arising from an incident.

    ``proof_file_content`` is absent from the field list : the bytes are served
    only by the ``proof`` action, permission-checked and scope-checked.

    Two conditional freezes mirror the model's own guards. Once the obligation
    has been filed (``sent_at`` set), what was transmitted is frozen : an
    amendment is a further filing, never a rewrite. Once a first filing exists,
    the clock stops recomputing for good, which is why ``anchor_at`` and
    ``due_at`` are unconditionally read-only rather than merely frozen : a
    correction of the anchor must never silently un-breach a late record.
    """

    status = serializers.CharField(source="workflow_state", read_only=True)
    incident_reference = serializers.CharField(read_only=True)
    incident_name = serializers.CharField(read_only=True)
    recipient_display = serializers.CharField(read_only=True)
    authority_name = serializers.CharField(read_only=True)
    template_name = serializers.CharField(read_only=True)
    decided_by_name = serializers.CharField(read_only=True)
    sent_by_name = serializers.CharField(read_only=True)
    depends_on_reference = serializers.CharField(read_only=True)
    deadline_bucket = serializers.CharField(read_only=True)
    is_undecided = serializers.BooleanField(read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)
    was_filed_late = serializers.BooleanField(read_only=True)
    has_proof = serializers.BooleanField(read_only=True)
    proof_filename_display = serializers.CharField(read_only=True)

    class Meta:
        model = IncidentNotification
        fields = [
            "id", "incident", "incident_reference", "incident_name",
            "reference",
            "regime", "recipient_kind",
            "recipient_stakeholder", "recipient_supplier", "recipient_name",
            "recipient_key", "recipient_display",
            "authority", "authority_name",
            "template", "template_name",
            "obligation_reference", "content_requirements",
            "clock_anchor", "deadline_hours", "no_fixed_deadline",
            "anchor_at", "due_at", "deadline_bucket",
            "depends_on", "depends_on_reference",
            "decision", "decision_rationale", "is_undecided",
            "decided_by", "decided_by_name", "decided_at",
            "channel", "content",
            "sent_at", "sent_by", "sent_by_name",
            "first_submitted_at", "late_by", "was_filed_late", "is_overdue",
            "acknowledgement_reference", "acknowledged_at",
            "proof_filename", "proof_filename_display", "has_proof",
            "proof_evidence",
            "source",
            "status", "tags", "version",
            "created_by", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "reference", "created_by", "created_at", "updated_at",
            "version",
            # Derived on save from the recipient triple; it backs the
            # uniqueness of an obligation and is never edited.
            "recipient_key",
            # RG-INC-25 : the decision mirrors the lifecycle step and is
            # written by the same transition, with its actor and its timestamp.
            "decision", "decided_by", "decided_at",
            # G-08 : the filing stamps are write-once on every path.
            "sent_at", "sent_by", "first_submitted_at",
            # RG-INC-28 : the frozen lateness verdict. The breach record, which
            # no later correction of the anchor can undo.
            "late_by",
            # Derived by `_recompute_clock()` from the anchor while no filing
            # exists, and frozen from the first filing onward. Never a client
            # value : a writable deadline is a deadline that can be moved after
            # it has been missed.
            "anchor_at", "due_at",
            # The rule the obligation was generated from : set by the generator,
            # not by a caller.
            "template",
            # `auto` marks a generated obligation, which is undeletable and is
            # answered through a decision. A client able to assert it could
            # dress a hand-typed row as evidence that the regime was considered,
            # or relabel a generated one as manual and then delete it.
            "source",
            # Set alongside the proof bytes, which no serializer carries.
            "proof_filename",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        instance = _edited_instance(self)
        if instance is not None and instance.sent_at is not None:
            # G-05 / RG-INC-29 : what left the organisation is not rewritten.
            _freeze(self, *NOTIFICATION_FILED_FROZEN_FIELDS)

    def _instance_for_clean(self, attrs):
        """Refresh the clock before asserting its coherence, as ``save()`` does.

        ``_assert_deadline_consistent()`` reads ``due_at``, which is derived and
        therefore read-only on this serializer. Running the model's own
        recomputation first is what makes the assertion evaluate the deadline
        the row will actually carry instead of an empty one : the alternative
        would be a second implementation of the clock in the API layer, which
        is exactly what the module refuses.
        """
        candidate = super()._instance_for_clean(attrs)
        candidate._recompute_clock(_edited_instance(self))
        return candidate

    def create(self, validated_data):
        """Stamp a hand-created obligation as manual, never as generated.

        Generation is `IncidentNotification.generate_obligations()`, run by the
        triage transition. Anything created through the API is by definition a
        manual addition, and the distinction decides whether the row may later
        be deleted at all.
        """
        validated_data["source"] = ObligationSource.MANUAL
        return super().create(validated_data)


class IncidentNotificationListSerializer(serializers.ModelSerializer):
    status = serializers.CharField(source="workflow_state", read_only=True)
    incident_reference = serializers.CharField(read_only=True)
    recipient_display = serializers.CharField(read_only=True)
    authority_name = serializers.CharField(read_only=True)
    deadline_bucket = serializers.CharField(read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)
    was_filed_late = serializers.BooleanField(read_only=True)

    class Meta:
        model = IncidentNotification
        fields = [
            "id", "incident", "incident_reference", "reference",
            "regime", "recipient_kind", "recipient_display",
            "authority", "authority_name", "obligation_reference",
            "clock_anchor", "anchor_at", "due_at", "deadline_bucket",
            "no_fixed_deadline",
            "decision", "sent_at", "first_submitted_at",
            "late_by", "was_filed_late", "is_overdue",
            "source", "status", "created_at",
        ]
        read_only_fields = ["id", "reference", "created_at"]


class NotificationFilingSerializer(_ParentLockedMixin, _CleanedModelSerializer):
    """One appended record of an actual transmission to a recipient.

    Append-only with exactly one narrow exception : after the insert, the three
    completion fields (``outcome``, ``acknowledged_at``, ``external_reference``)
    may each be written once, because the recipient's answer arrives after the
    transmission. Every other key sent to an update is **rejected with a 400**
    rather than silently ignored, so a client that believes it corrected a
    filing is told that it did not : a correction to what the organisation told
    a regulator is a new filing.
    """

    parent_field = "notification"

    notification_reference = serializers.CharField(read_only=True)
    incident_reference = serializers.CharField(read_only=True)
    regime = serializers.CharField(read_only=True)
    submitted_by_name = serializers.CharField(read_only=True)
    supersedes_reference = serializers.CharField(read_only=True)
    is_superseded = serializers.BooleanField(read_only=True)
    has_proof = serializers.BooleanField(read_only=True)
    recording_delay = serializers.DurationField(read_only=True)

    class Meta:
        model = NotificationFiling
        fields = [
            "id", "notification", "notification_reference",
            "incident_reference", "regime", "reference",
            "submitted_at", "recording_delay",
            "channel", "recipient_name", "subject", "content",
            "external_reference", "outcome", "acknowledged_at",
            "is_correction", "was_late",
            "supersedes", "supersedes_reference", "is_superseded",
            "submitted_by", "submitted_by_name",
            "proof_filename", "has_proof",
            "version", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "reference", "created_at", "updated_at", "version",
            # RG-INC-28 : frozen at the insert from the obligation's deadline
            # and never recomputed. A filing that could declare itself on time
            # would make the lateness column worthless.
            "was_late",
            # Stamped from the request user.
            "submitted_by",
            # Set alongside the proof bytes, which no serializer carries.
            "proof_filename",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if _edited_instance(self) is not None:
            frozen = [
                name
                for name in self.fields
                if name not in FILING_COMPLETION_FIELDS
            ]
            _freeze(self, *frozen)

    def validate(self, attrs):
        attrs = super().validate(attrs)
        if _edited_instance(self) is not None:
            submitted = set(getattr(self, "initial_data", None) or {})
            forbidden = sorted(submitted - set(FILING_COMPLETION_FIELDS))
            if forbidden:
                raise serializers.ValidationError(
                    {
                        name: _(
                            "The filing log is append-only : only the outcome, "
                            "the acknowledgement date and the external "
                            "reference may be completed after the filing. "
                            "Record a correction as a new filing."
                        )
                        for name in forbidden
                    }
                )
        return attrs


# --- Personal data breach (GDPR Art. 33 / 34) --------------------------------


class PersonalDataBreachSerializer(_ParentLockedMixin, _CleanedModelSerializer):
    status = serializers.CharField(source="workflow_state", read_only=True)
    incident_reference = serializers.CharField(read_only=True)
    incident_title = serializers.CharField(read_only=True)
    lead_authority_name = serializers.CharField(read_only=True)
    controller_supplier_name = serializers.CharField(read_only=True)
    qualified_by_name = serializers.CharField(read_only=True)
    acts_as_processor = serializers.BooleanField(read_only=True)
    has_article_33_3_content = serializers.BooleanField(read_only=True)

    class Meta:
        model = PersonalDataBreach
        fields = [
            "id", "incident", "incident_reference", "incident_title",
            "reference",
            "controller_role", "acts_as_processor",
            "controller_supplier", "controller_supplier_name",
            "lead_authority", "lead_authority_name",
            "cross_border_eu",
            "nature", "data_categories", "special_categories",
            "data_subject_categories",
            "approximate_data_subjects", "approximate_records",
            "volume_is_estimate",
            "dpo_contact", "likely_consequences", "measures_taken",
            "has_article_33_3_content",
            "high_risk_to_rights", "high_risk_justification",
            "article_34_exemption", "article_34_exemption_justification",
            "register_entry_reference",
            "qualified_by", "qualified_by_name", "qualified_at",
            "status", "tags", "version",
            "created_by", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "reference", "created_by", "created_at", "updated_at",
            "version",
            # RG-INC-12 / G-05 : the verdict is reached through the `confirm`
            # or `not_a_breach` transition, which stamps who reached it and
            # when. Both are write-once, and a breach ruled out by a client
            # field write would leave none of the evidence Art. 33(1) expects.
            "qualified_by", "qualified_at",
        ]


class PersonalDataBreachListSerializer(serializers.ModelSerializer):
    status = serializers.CharField(source="workflow_state", read_only=True)
    incident_reference = serializers.CharField(read_only=True)
    incident_title = serializers.CharField(read_only=True)
    lead_authority_name = serializers.CharField(read_only=True)

    class Meta:
        model = PersonalDataBreach
        fields = [
            "id", "incident", "incident_reference", "incident_title",
            "reference",
            "controller_role", "lead_authority", "lead_authority_name",
            "cross_border_eu", "special_categories",
            "approximate_data_subjects", "approximate_records",
            "high_risk_to_rights", "article_34_exemption",
            "qualified_at", "status", "created_at",
        ]
        read_only_fields = ["id", "reference", "created_at"]
