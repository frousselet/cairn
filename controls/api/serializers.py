# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""DRF serializers for module 8 (controls).

Rules that hold across the file :

**`workflow_state` is never writable.** Every entity exposes it as
``status = CharField(source="workflow_state", read_only=True)``; a state change
is a transition through the model's ``transition_to()`` (RG-CTL-02, -06, -10,
-11, -12 live there).

**Derived values are read-only.** ``effectiveness`` / ``effectiveness_updated_at``
(RG-CTL-14), ``next_due_date`` / ``activated_on`` (RG-CTL-07), ``reviewed_by`` /
``reviewed_at`` (RG-CTL-11) and every evidence attribute (RG-CTL-13) are written
by the domain, never by a client.

**Links are governed.** Each relation of a control only accepts targets within
the caller's scopes and in a linkable lifecycle step, plus the ones already
linked (RG-CTL-04, ``linkable_or_linked()``), so a client cannot attach a
control to a risk of another perimeter or to a retired document by guessing a
UUID.

**A frozen run is refused, not ignored.** From ``in_review`` on, a run's
content is frozen (RG-CTL-09) : a ``PATCH`` that would change it is answered
with a 400 carrying the model's own message.

**Evidence bytes never appear.** The run lists its evidence with ``file_name``,
``size``, ``sha256`` and ``download_url`` (the permission-checked, scope-filtered
download view); files are uploaded through the web form only (README §5).
"""

import copy

from django.apps import apps
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import models
from django.db.models import Q
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.settings import api_settings

from core.lifecycle import linkable_or_linked
from core.scoping import filter_queryset_by_scopes
from controls.models import Control, ControlTest, ControlTestRun
from controls.models.control_test_run import FROZEN_FIELDS

#: Every relation of a control (README §1.3) : the serializer field, the target
#: model, and the explicit scope path for targets whose model declares none
#: (``None`` lets ``core.scoping`` resolve it from the model).
CONTROL_RELATIONS = (
    ("requirements", "compliance.Requirement", None),
    ("risks", "risks.Risk", "assessment__scopes"),
    ("treatment_plans", "risks.RiskTreatmentPlan", "risk__assessment__scopes"),
    ("pacs_measures", "risks.PACSMeasure", "summary__assessment__scopes"),
    ("support_assets", "assets.SupportAsset", None),
    ("objectives", "context.Objective", None),
    ("policies", "documents.Policy", None),
)

#: RG-CTL-09 : the run fields a client can write that freeze on submission
#: (the model's ``FROZEN_FIELDS`` minus the ``_id`` suffix of the relations).
RUN_FROZEN_API_FIELDS = tuple(name[:-3] if name.endswith("_id") else name for name in FROZEN_FIELDS)

RUN_FROZEN_MESSAGE = _("A submitted test run is frozen : its content can no longer be changed.")


# --- Shared behaviour --------------------------------------------------------


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
    """The single row being updated, or ``None`` (a list render passes the
    queryset as ``instance``)."""
    instance = serializer.instance
    return instance if isinstance(instance, models.Model) else None


def _request_user(serializer):
    request = serializer.context.get("request")
    return getattr(request, "user", None)


def scoped_for(user, queryset, explicit=None):
    """Restrict ``queryset`` to what ``user`` may see (scope tenancy)."""
    if user is None or not user.is_authenticated or user.is_superuser:
        return queryset
    scope_ids = user.get_allowed_scope_ids()
    if scope_ids is None:
        return queryset
    return filter_queryset_by_scopes(queryset, scope_ids, explicit=explicit)


def _user_name(user):
    return user.display_name if user is not None else ""


class _CleanedModelSerializer(serializers.ModelSerializer):
    """Run the model's own ``clean()`` during validation.

    ``ModelSerializer`` does not call it, so the future implementation date
    (RG-CTL-02), the run period (RG-CTL-10) and the active-test rule
    (RG-CTL-09) would reach ``save()`` as an exception rather than a field
    error. The candidate is built in memory from the non-M2M data.
    """

    def validate(self, attrs):
        attrs = super().validate(attrs)
        candidate = self._instance_for_clean(attrs)
        try:
            candidate.clean()
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
        candidate = copy.copy(instance)
        for key, value in data.items():
            setattr(candidate, key, value)
        return candidate


# --- Control -----------------------------------------------------------------


class _ControlFieldsMixin(serializers.Serializer):
    status = serializers.CharField(source="workflow_state", read_only=True)
    owner_name = serializers.SerializerMethodField()
    next_test_due = serializers.SerializerMethodField()
    is_test_overdue = serializers.SerializerMethodField()
    is_effectiveness_stale = serializers.SerializerMethodField()

    def get_owner_name(self, obj):
        return _user_name(obj.owner)

    def _next_due(self, obj):
        # The list queryset annotates it; a single object reads the property.
        if hasattr(obj, "_next_test_due"):
            return obj._next_test_due
        return obj.next_test_due

    def get_next_test_due(self, obj):
        due = self._next_due(obj)
        return due.isoformat() if due else None

    def get_is_test_overdue(self, obj):
        from django.utils import timezone

        due = self._next_due(obj)
        return due is not None and due < timezone.localdate()

    def get_is_effectiveness_stale(self, obj):
        from controls.constants import ControlEffectiveness

        return self.get_is_test_overdue(obj) and obj.effectiveness != ControlEffectiveness.NOT_TESTED


class ControlSerializer(_ControlFieldsMixin, _CleanedModelSerializer):
    class Meta:
        model = Control
        fields = [
            "id", "scopes", "reference", "name", "description", "theme", "nature", "automation",
            "owner", "owner_name", "implemented_on",
            "effectiveness", "effectiveness_updated_at", "next_test_due", "is_test_overdue",
            "is_effectiveness_stale",
            "requirements", "risks", "treatment_plans", "pacs_measures", "support_assets",
            "objectives", "policies",
            "status", "tags", "version", "created_by", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "reference", "version", "created_by", "created_at", "updated_at",
            # RG-CTL-14 : derived from the validated runs, never declared.
            "effectiveness", "effectiveness_updated_at",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        user = _request_user(self)
        instance = _edited_instance(self)
        scopes = self.fields.get("scopes")
        if scopes is not None and not scopes.read_only:
            # The caller's own scopes, plus those the control already carries
            # (a co-owned control keeps the perimeter the caller cannot see).
            scope_model = apps.get_model("context", "Scope")
            allowed = Q(pk__in=scoped_for(user, scope_model.objects.all()).values("pk"))
            if instance is not None:
                allowed |= Q(pk__in=instance.scopes.values("pk"))
            scopes.child_relation.queryset = scope_model.objects.filter(allowed)
        for name, label, lookup in CONTROL_RELATIONS:
            field = self.fields.get(name)
            if field is None or field.read_only:
                continue
            target = apps.get_model(label)
            linked = getattr(instance, name).all() if instance is not None else None
            field.child_relation.queryset = scoped_for(
                user, linkable_or_linked(target.objects.all(), linked), explicit=lookup,
            )


class ControlListSerializer(_ControlFieldsMixin, serializers.ModelSerializer):
    requirement_count = serializers.SerializerMethodField()

    class Meta:
        model = Control
        fields = [
            "id", "scopes", "reference", "name", "theme", "nature", "automation",
            "owner", "owner_name", "implemented_on", "effectiveness", "next_test_due",
            "is_test_overdue", "is_effectiveness_stale", "requirement_count", "status", "created_at",
        ]
        read_only_fields = fields

    def get_requirement_count(self, obj):
        annotated = getattr(obj, "_requirement_count", None)
        return annotated if annotated is not None else obj.requirements.count()


# --- ControlTest -------------------------------------------------------------


class ControlTestSerializer(_CleanedModelSerializer):
    status = serializers.CharField(source="workflow_state", read_only=True)
    control_reference = serializers.CharField(source="control.reference", read_only=True)
    control_name = serializers.CharField(source="control.name", read_only=True)
    tester_name = serializers.SerializerMethodField()
    is_overdue = serializers.BooleanField(read_only=True)
    latest_result = serializers.SerializerMethodField()

    class Meta:
        model = ControlTest
        fields = [
            "id", "reference", "control", "control_reference", "control_name", "name", "objective",
            "method", "procedure", "acceptance_criteria", "frequency_months", "tester", "tester_name",
            "first_due_date", "next_due_date", "activated_on", "is_overdue", "latest_result",
            "status", "tags", "version", "created_by", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "reference", "version", "created_by", "created_at", "updated_at",
            # RG-CTL-07 : derived and stamped by the domain.
            "next_due_date", "activated_on",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        field = self.fields.get("control")
        if field is None or field.read_only:
            return
        # The parent of a test, not a link : a proposed control takes tests
        # (activation waits for it to be planned, RG-CTL-06); a retired one is
        # refused in ``validate``.
        field.queryset = scoped_for(_request_user(self), Control.objects.all())

    def validate(self, attrs):
        instance = _edited_instance(self)
        control = attrs.get("control")
        moved = control is not None and (instance is None or control.pk != instance.control_id)
        if moved and control.is_retired:
            raise serializers.ValidationError({"control": [_("A retired control takes no new test.")]})
        if moved and instance is not None and instance.runs.exists():
            raise serializers.ValidationError({"control": [_("A test that has runs cannot move to another control.")]})
        return super().validate(attrs)

    def get_tester_name(self, obj):
        return _user_name(obj.tester)

    def get_latest_result(self, obj):
        return obj.latest_result


class ControlTestListSerializer(ControlTestSerializer):
    class Meta(ControlTestSerializer.Meta):
        fields = [
            "id", "reference", "control", "control_reference", "control_name", "name", "method",
            "frequency_months", "tester", "tester_name", "next_due_date", "is_overdue",
            "latest_result", "status", "created_at",
        ]
        read_only_fields = fields


# --- ControlTestRun ----------------------------------------------------------


def evidence_payload(item):
    """One evidence row as every surface lists it : metadata, never the file."""
    return {
        "id": str(item.pk),
        "file_name": item.original_filename,
        "size": item.size,
        "sha256": item.sha256,
        "description": item.description,
        "uploaded_by": str(item.uploaded_by_id) if item.uploaded_by_id else None,
        "uploaded_by_name": _user_name(item.uploaded_by),
        "uploaded_at": item.uploaded_at.isoformat() if item.uploaded_at else None,
        "download_url": reverse("controls:evidence-download", kwargs={"pk": item.pk}),
    }


def raised_finding_payload(run):
    """The finding raised from ``run`` (RG-CTL-16), or ``None``."""
    finding = next(iter(run.findings.all()), None)
    if finding is None:
        return None
    return {"id": str(finding.pk), "reference": finding.reference, "finding_type": finding.finding_type}


class ControlTestRunSerializer(_CleanedModelSerializer):
    status = serializers.CharField(source="workflow_state", read_only=True)
    test_reference = serializers.CharField(source="test.reference", read_only=True)
    test_name = serializers.CharField(source="test.name", read_only=True)
    control = serializers.UUIDField(source="test.control_id", read_only=True)
    control_reference = serializers.CharField(source="test.control.reference", read_only=True)
    performed_by_name = serializers.SerializerMethodField()
    reviewed_by_name = serializers.SerializerMethodField()
    is_frozen = serializers.BooleanField(read_only=True)
    needs_finding = serializers.SerializerMethodField()
    finding = serializers.SerializerMethodField()
    evidence = serializers.SerializerMethodField()

    class Meta:
        model = ControlTestRun
        fields = [
            "id", "reference", "test", "test_reference", "test_name", "control", "control_reference",
            "performed_by", "performed_by_name", "performed_on", "period_start", "period_end",
            "sample_description", "result", "observations",
            "reviewed_by", "reviewed_by_name", "reviewed_at", "is_frozen", "needs_finding", "finding",
            "evidence", "status", "tags", "version", "created_by", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "reference", "version", "created_by", "created_at", "updated_at",
            # RG-CTL-11 : stamped by the validation transition.
            "reviewed_by", "reviewed_at",
        ]
        extra_kwargs = {
            # Defaults to the test's tester, else the caller (control-test-run.md).
            "performed_by": {"required": False},
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        field = self.fields.get("test")
        if field is None:
            return
        if _edited_instance(self) is not None:
            # Moving a run to another test would move its evidence into another
            # control's record and perimeter.
            field.read_only = True
            field.required = False
        else:
            field.queryset = scoped_for(_request_user(self), ControlTest.objects.select_related("control"))

    def validate(self, attrs):
        instance = _edited_instance(self)
        if instance is not None and instance.is_frozen:
            errors = {
                name: [RUN_FROZEN_MESSAGE]
                for name in RUN_FROZEN_API_FIELDS
                if name in attrs and attrs[name] != getattr(instance, name)
            }
            if errors:
                raise serializers.ValidationError(errors)
        return super().validate(attrs)

    def create(self, validated_data):
        if not validated_data.get("performed_by"):
            test = validated_data["test"]
            validated_data["performed_by"] = test.tester or _request_user(self)
        return super().create(validated_data)

    def get_performed_by_name(self, obj):
        return _user_name(obj.performed_by)

    def get_reviewed_by_name(self, obj):
        return _user_name(obj.reviewed_by)

    def get_needs_finding(self, obj):
        return obj.needs_finding

    def get_finding(self, obj):
        return raised_finding_payload(obj)

    def get_evidence(self, obj):
        return [evidence_payload(item) for item in obj.evidence.all()]


class ControlTestRunListSerializer(ControlTestRunSerializer):
    class Meta(ControlTestRunSerializer.Meta):
        fields = [
            "id", "reference", "test", "test_reference", "test_name", "control", "control_reference",
            "performed_by", "performed_by_name", "performed_on", "result", "reviewed_by",
            "reviewed_by_name", "reviewed_at", "is_frozen", "status", "created_at",
        ]
        read_only_fields = fields
