# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""DRF serializers for module 7 (documents).

Four rules hold across the file :

**`workflow_state` is never writable.** Every lifecycle entity exposes it as
``status = CharField(source="workflow_state", read_only=True)``. A state change
is a transition, routed through the model's ``transition_to()``, where the
gates, the approval and supersession stamps and the recorded
``LifecycleEvent`` live.

**Stamps are read-only.** ``approved_by`` / ``approved_at`` (RG-DOC-07),
``superseded_at`` / ``superseded_by`` (RG-DOC-01), ``next_review_date`` /
``last_reviewed_*`` (RG-DOC-11 / RG-DOC-13), ``launched_at`` / ``closed_at``
and every field of an acknowledgement row (RG-DOC-16) are written by the
domain, never by a client.

**The PDF bytes never appear.** ``file_content`` is in no serializer
(RG-DOC-04); a client gets ``has_pdf``, ``pdf_sha256`` (to check a downloaded
copy against the approved one) and ``document_url``, the permission-checked
and scope-filtered download view. The PDF is uploaded through the web form
only, so ``file_name`` is read-only here too.

**A frozen field is refused, not ignored.** From ``in_review`` onward a
version's content is frozen (RG-DOC-02). A ``PUT`` / ``PATCH`` that changes
``content``, ``version_label`` or ``change_summary`` on a submitted version is
answered with a 400 naming the field, so a client that believes it corrected
an approved text is told that it did not. The same holds for a launched
campaign's target version, statement and audience (RG-DOC-15).
"""

import copy

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.settings import api_settings

from core.scoping import filter_queryset_by_scopes
from documents.constants import CAMPAIGN_DRAFT, AcknowledgementStatus
from documents.models import AcknowledgementCampaign, Policy, PolicyAcknowledgement, PolicyVersion

#: RG-DOC-02 : the version fields a client can write that freeze on submission.
#: ``file_content`` / ``file_name`` / ``file_sha256`` freeze too, but no
#: serializer writes them at all.
VERSION_FROZEN_API_FIELDS = ("content", "version_label", "change_summary")

#: RG-DOC-15 : what a launched campaign can no longer change. The audience is
#: resolved once at launch; the target version and the statement are what each
#: addressee confirms.
CAMPAIGN_FROZEN_API_FIELDS = ("policy_version", "statement", "audience_users", "audience_groups", "audience_roles")


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
    """The single row this serializer is updating, or ``None`` (a list render
    passes the queryset as ``instance``)."""
    instance = serializer.instance
    return instance if isinstance(instance, models.Model) else None


def _request_user(serializer):
    request = serializer.context.get("request")
    return getattr(request, "user", None)


def _scoped(serializer, queryset):
    """Restrict a related-field queryset to what the caller may see.

    Without it a client could attach a version to a document outside its
    perimeter, or launch a campaign on such a version, by guessing a UUID.
    """
    user = _request_user(serializer)
    if user is None or not user.is_authenticated or user.is_superuser:
        return queryset
    scope_ids = user.get_allowed_scope_ids()
    if scope_ids is None:
        return queryset
    return filter_queryset_by_scopes(queryset, scope_ids)


def _user_name(user):
    return user.display_name if user is not None else ""


class _CleanedModelSerializer(serializers.ModelSerializer):
    """Run the model's own ``clean()`` and constraints during validation.

    ``ModelSerializer`` calls neither ``full_clean()`` nor
    ``validate_constraints()``, so the parent cycle check (RG-DOC-10), the
    future effective date (RG-DOC-07) and the unique version label per
    document (RG-DOC-05) would hold on the web form and reach the database as
    a 500 here. The candidate is built in memory from the non-M2M data.
    """

    def validate(self, attrs):
        attrs = super().validate(attrs)
        candidate = self._instance_for_clean(attrs)
        try:
            candidate.clean()
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
        candidate = copy.copy(instance)
        for key, value in data.items():
            setattr(candidate, key, value)
        return candidate


def _refuse_frozen_changes(instance, attrs, field_names, message):
    """400 on every frozen field the payload would change.

    A key sent with the stored value is not a change (a client replaying a
    ``GET`` payload in a ``PUT`` is not refused for the fields it left alone).
    """
    errors = {}
    for name in field_names:
        if name not in attrs:
            continue
        current = getattr(instance, name)
        proposed = attrs[name]
        if hasattr(current, "all"):
            current = {obj.pk for obj in current.all()}
            proposed = {obj.pk for obj in proposed or []}
        if proposed != current:
            errors[name] = [message]
    if errors:
        raise serializers.ValidationError(errors)


def _version_summary(version):
    if version is None:
        return None
    return {
        "id": str(version.pk),
        "reference": version.reference,
        "version_label": version.version_label,
        "effective_from": version.effective_from.isoformat() if version.effective_from else None,
        "approved_at": version.approved_at.isoformat() if version.approved_at else None,
    }


# --- Policy (the document) ---------------------------------------------------


class _PolicyFieldsMixin(serializers.Serializer):
    status = serializers.CharField(source="workflow_state", read_only=True)
    owner_name = serializers.SerializerMethodField()
    is_review_overdue = serializers.BooleanField(read_only=True)
    version_in_force = serializers.SerializerMethodField()

    def get_owner_name(self, obj):
        return _user_name(obj.owner)

    def get_version_in_force(self, obj):
        """The version in force, from the prefetch when the viewset made one."""
        prefetched = getattr(obj, "_in_force", None)
        # Only a list render trusts the prefetch : a single object may just
        # have been transitioned (retiring supersedes its version in force).
        if prefetched is not None and self.parent is not None:
            return _version_summary(prefetched[0] if prefetched else None)
        return _version_summary(obj.version_in_force)


class PolicySerializer(_PolicyFieldsMixin, _CleanedModelSerializer):
    approver_name = serializers.SerializerMethodField()
    parent_reference = serializers.SerializerMethodField()
    last_reviewed_by_name = serializers.SerializerMethodField()

    class Meta:
        model = Policy
        fields = [
            "id", "scopes", "reference", "title", "document_type", "summary", "classification",
            "parent", "parent_reference", "owner", "owner_name", "approver", "approver_name",
            "review_frequency_months", "next_review_override", "next_review_date",
            "last_reviewed_at", "last_reviewed_by", "last_reviewed_by_name", "is_review_overdue",
            "version_in_force", "linked_requirements", "applies_to_roles",
            "status", "tags", "version", "created_by", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "reference", "version", "created_by", "created_at", "updated_at",
            # RG-DOC-11 / RG-DOC-13 : derived or stamped by the domain.
            "next_review_date", "last_reviewed_at", "last_reviewed_by",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        field = self.fields.get("parent")
        if field is not None and not field.read_only:
            field.queryset = _scoped(self, Policy.objects.all())

    def get_approver_name(self, obj):
        return _user_name(obj.approver)

    def get_parent_reference(self, obj):
        return obj.parent.reference if obj.parent_id else None

    def get_last_reviewed_by_name(self, obj):
        return _user_name(obj.last_reviewed_by)


class PolicyListSerializer(_PolicyFieldsMixin, serializers.ModelSerializer):
    class Meta:
        model = Policy
        fields = [
            "id", "scopes", "reference", "title", "document_type", "classification", "parent",
            "owner", "owner_name", "review_frequency_months", "next_review_date", "is_review_overdue",
            "version_in_force", "status", "created_at",
        ]
        read_only_fields = fields


# --- PolicyVersion -----------------------------------------------------------


class PolicyVersionSerializer(_CleanedModelSerializer):
    status = serializers.CharField(source="workflow_state", read_only=True)
    policy_reference = serializers.CharField(source="policy.reference", read_only=True)
    policy_title = serializers.CharField(source="policy.title", read_only=True)
    has_pdf = serializers.SerializerMethodField()
    pdf_sha256 = serializers.CharField(source="file_sha256", read_only=True)
    document_url = serializers.SerializerMethodField()
    is_frozen = serializers.BooleanField(read_only=True)
    approved_by_name = serializers.SerializerMethodField()
    superseded_by_reference = serializers.SerializerMethodField()

    class Meta:
        model = PolicyVersion
        fields = [
            "id", "reference", "policy", "policy_reference", "policy_title",
            "version_label", "content", "change_summary",
            "has_pdf", "file_name", "pdf_sha256", "document_url",
            "approved_by", "approved_by_name", "approved_at", "effective_from",
            "superseded_at", "superseded_by", "superseded_by_reference",
            "is_frozen", "status", "tags", "version", "created_by", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "reference", "version", "created_by", "created_at", "updated_at",
            # The PDF is uploaded through the web form only (README §5).
            "file_name",
            # RG-DOC-07 / RG-DOC-01 : stamped by the transitions.
            "approved_by", "approved_at", "superseded_at", "superseded_by",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        field = self.fields.get("policy")
        if field is None:
            return
        if _edited_instance(self) is not None:
            # Re-pointing a version at another document would move its approved
            # text into another document's record and perimeter.
            field.read_only = True
            field.required = False
        else:
            field.queryset = _scoped(self, Policy.objects.all())

    def validate(self, attrs):
        instance = _edited_instance(self)
        if instance is not None and instance.is_frozen:
            _refuse_frozen_changes(
                instance, attrs, VERSION_FROZEN_API_FIELDS,
                _("A submitted version is frozen : its content can no longer be changed."),
            )
        return super().validate(attrs)

    def get_has_pdf(self, obj):
        annotated = getattr(obj, "_has_pdf", None)
        return bool(annotated) if annotated is not None else obj.has_pdf

    def get_document_url(self, obj):
        if not self.get_has_pdf(obj):
            return None
        return reverse("documents:policyversion-pdf", kwargs={"pk": obj.pk})

    def get_approved_by_name(self, obj):
        return _user_name(obj.approved_by)

    def get_superseded_by_reference(self, obj):
        return obj.superseded_by.reference if obj.superseded_by_id else None


class PolicyVersionListSerializer(PolicyVersionSerializer):
    class Meta(PolicyVersionSerializer.Meta):
        fields = [
            "id", "reference", "policy", "policy_reference", "policy_title", "version_label",
            "change_summary", "has_pdf", "pdf_sha256", "document_url",
            "approved_by", "approved_by_name", "approved_at", "effective_from",
            "superseded_at", "superseded_by", "status", "created_at",
        ]


# --- AcknowledgementCampaign -------------------------------------------------


class AcknowledgementCampaignSerializer(_CleanedModelSerializer):
    status = serializers.CharField(source="workflow_state", read_only=True)
    policy_id = serializers.UUIDField(source="policy_version.policy_id", read_only=True)
    policy_title = serializers.CharField(source="policy_version.policy.title", read_only=True)
    policy_version_reference = serializers.CharField(source="policy_version.reference", read_only=True)
    version_label = serializers.CharField(source="policy_version.version_label", read_only=True)
    counts = serializers.DictField(child=serializers.IntegerField(), read_only=True)
    completion_rate = serializers.IntegerField(read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)

    class Meta:
        model = AcknowledgementCampaign
        fields = [
            "id", "scopes", "reference", "name", "policy_version", "policy_version_reference",
            "policy_id", "policy_title", "version_label", "message", "statement", "due_date",
            "launched_at", "closed_at", "audience_users", "audience_groups", "audience_roles",
            "counts", "completion_rate", "is_overdue",
            "status", "tags", "version", "created_by", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "reference", "version", "created_by", "created_at", "updated_at",
            "launched_at", "closed_at",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        field = self.fields.get("policy_version")
        if field is not None and not field.read_only:
            field.queryset = _scoped(self, PolicyVersion.objects.defer("file_content"))

    def validate(self, attrs):
        instance = _edited_instance(self)
        if instance is not None and instance.workflow_state != CAMPAIGN_DRAFT:
            _refuse_frozen_changes(
                instance, attrs, CAMPAIGN_FROZEN_API_FIELDS,
                _("A launched campaign keeps the version, statement and audience it was launched with."),
            )
        return super().validate(attrs)

    def create(self, validated_data):
        """A campaign defaults to its document's scopes (acknowledgement-campaign.md)."""
        scopes_given = bool(validated_data.get("scopes"))
        campaign = super().create(validated_data)
        if not scopes_given:
            campaign.scopes.set(campaign.policy_version.policy.scopes.all())
        return campaign


class AcknowledgementCampaignListSerializer(AcknowledgementCampaignSerializer):
    class Meta(AcknowledgementCampaignSerializer.Meta):
        fields = [
            "id", "scopes", "reference", "name", "policy_version", "policy_version_reference",
            "policy_id", "policy_title", "version_label", "due_date", "launched_at", "closed_at",
            "counts", "completion_rate", "is_overdue", "status", "created_at",
        ]


# --- PolicyAcknowledgement (write-once rows, read-only here) -----------------


class PolicyAcknowledgementSerializer(serializers.ModelSerializer):
    """One addressee's row. Every field is read-only : the only write paths
    are the ``acknowledge`` and ``excuse`` actions (RG-DOC-16)."""

    campaign_reference = serializers.CharField(source="campaign.reference", read_only=True)
    campaign_name = serializers.CharField(source="campaign.name", read_only=True)
    campaign_status = serializers.CharField(source="campaign.workflow_state", read_only=True)
    due_date = serializers.DateField(source="campaign.due_date", read_only=True)
    policy_version = serializers.UUIDField(source="campaign.policy_version_id", read_only=True)
    version_label = serializers.CharField(source="campaign.policy_version.version_label", read_only=True)
    policy_id = serializers.UUIDField(source="campaign.policy_version.policy_id", read_only=True)
    policy_reference = serializers.CharField(source="campaign.policy_version.policy.reference", read_only=True)
    policy_title = serializers.CharField(source="campaign.policy_version.policy.title", read_only=True)
    user_name = serializers.SerializerMethodField()
    excused_by_name = serializers.SerializerMethodField()
    statement_to_confirm = serializers.SerializerMethodField()

    class Meta:
        model = PolicyAcknowledgement
        fields = [
            "id", "campaign", "campaign_reference", "campaign_name", "campaign_status", "due_date",
            "policy_version", "version_label", "policy_id", "policy_reference", "policy_title",
            "user", "user_name", "status", "requested_at", "statement_to_confirm",
            "acknowledged_at", "statement", "channel",
            "excused_at", "excused_by", "excused_by_name", "excuse_reason",
        ]
        read_only_fields = fields

    def get_user_name(self, obj):
        return _user_name(obj.user)

    def get_excused_by_name(self, obj):
        return _user_name(obj.excused_by)

    def get_statement_to_confirm(self, obj):
        """The sentence the addressee confirms, while the row is still pending."""
        if obj.status != AcknowledgementStatus.PENDING:
            return None
        return obj.campaign.statement_for()
