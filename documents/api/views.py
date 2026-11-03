# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""DRF viewsets for module 7 (documents), mounted at ``/api/v1/documents/``.

Rules stated once for the whole file :

**Two permission features.** ``documents.policy`` governs documents and their
versions (a version is governed by its document's permissions, as its
``workflow_perm_namespace`` says); ``documents.acknowledgement`` governs
campaigns and the reading of their rows (README §4).

**A state change is a transition.** No view writes ``workflow_state``. The
``/transition/`` endpoint comes from ``LifecycleAPIMixin`` and goes through
each model's ``transition_to(enforce_permission=True)``, which locks the
document, checks the gates (RG-DOC-03, -06, -09, -14) and applies the side
effects (supersession, approval stamps, campaign launch and closure) in one
transaction. A gate refusal is a ``DomainRefusalError`` whose translated
detail reaches the client as a 400; a refused permission is a 403.

**Tenancy.** Policies and campaigns carry their own ``scopes``; versions and
acknowledgement rows inherit theirs through the model's
``scope_parent_lookup`` (RG-DOC-22), which ``ScopeFilterAPIMixin`` resolves.
A user always reads their own acknowledgement rows, whatever their scopes and
permissions.

**Acknowledgement rows are write-once.** The router publishes no create,
update or delete for them : rows are created by a campaign launch or "Add
newcomers", and change only through ``acknowledge`` (the addressee, RG-DOC-17)
or ``excuse`` (RG-DOC-19).
"""

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import BooleanField, Case, ExpressionWrapper, IntegerField, Prefetch, Q, Value, When
from django.db.models.deletion import ProtectedError
from django.utils.translation import gettext_lazy as _
from rest_framework import mixins, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import APIException, PermissionDenied
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.response import Response

from accounts.api.mixins import BatchCreateMixin, HistoryAPIMixin, LifecycleAPIMixin, ScopeFilterAPIMixin
from accounts.api.permissions import ModulePermission
from core.lifecycle import LifecycleError, LifecycleProtectedError, TransitionNotAllowedError
from core.scoping import filter_queryset_by_scopes
from core.transition_messages import transition_error_detail
from documents.constants import POLICY_RETIRED, VERSION_IN_FORCE, AcknowledgementChannel, AcknowledgementStatus
from documents.models import AcknowledgementCampaign, Policy, PolicyAcknowledgement, PolicyVersion

from .filters import AcknowledgementCampaignFilter, PolicyAcknowledgementFilter, PolicyFilter, PolicyVersionFilter
from .serializers import (
    AcknowledgementCampaignListSerializer,
    AcknowledgementCampaignSerializer,
    PolicyAcknowledgementSerializer,
    PolicyListSerializer,
    PolicySerializer,
    PolicyVersionListSerializer,
    PolicyVersionSerializer,
)

#: The two bumps the "New version" action accepts (RG-DOC-05). Argument values
#: of the API, not lifecycle states.
VERSION_BUMPS = ("minor", "major")


class Conflict(APIException):
    """409 : the payload is fine, the register refuses the write (a step that
    is not deletable, a row still referenced)."""

    status_code = status.HTTP_409_CONFLICT
    default_detail = _("This element cannot be changed in its current lifecycle state.")
    default_code = "conflict"


def _validation_error(exc):
    if hasattr(exc, "message_dict"):
        return serializers.ValidationError(exc.message_dict)
    return serializers.ValidationError({"non_field_errors": list(exc.messages)})


def _domain_response(exc):
    """A lifecycle / domain refusal as a response : 403 for a refused
    permission, 400 with the model's own translated reason otherwise."""
    if isinstance(exc, TransitionNotAllowedError):
        raise PermissionDenied(transition_error_detail(exc))
    return Response({"detail": transition_error_detail(exc)}, status=status.HTTP_400_BAD_REQUEST)


def _versions_without_bytes():
    """Versions with the PDF bytes deferred and their presence annotated, so a
    list never loads every attached PDF to answer ``has_pdf``."""
    return PolicyVersion.objects.defer("file_content").annotate(
        _has_pdf=ExpressionWrapper(Q(file_content__isnull=False), output_field=BooleanField()),
    )


class _DocumentsViewSet(viewsets.ModelViewSet):
    """The shared base : module permission, created-by stamp, governed writes."""

    permission_classes = [IsAuthenticated, ModulePermission]
    permission_module = "documents"
    custom_action_map = {
        "transition": "update",
        "batch_create": "create",
        "history": "read",
    }

    def _guarded_save(self, serializer, **kwargs):
        """Save, turning each governance refusal into its own status code
        instead of a 500 (the models refuse frozen and write-once changes in
        ``save()``, and that guard is the real one)."""
        try:
            return serializer.save(**kwargs)
        except DjangoValidationError as exc:
            raise _validation_error(exc) from exc
        except TransitionNotAllowedError as exc:
            raise PermissionDenied(transition_error_detail(exc)) from exc
        except LifecycleError as exc:
            raise serializers.ValidationError({"non_field_errors": [transition_error_detail(exc)]}) from exc

    def perform_create(self, serializer):
        self._guarded_save(serializer, created_by=self.request.user)

    def perform_update(self, serializer):
        self._guarded_save(serializer)

    def perform_destroy(self, instance):
        try:
            instance.delete()
        except LifecycleProtectedError as exc:
            # Never `str(exc)` in a response body (CodeQL py/stack-trace-exposure).
            raise Conflict(_("This element cannot be deleted in its current lifecycle state.")) from exc
        except ProtectedError as exc:
            raise Conflict(_("This element is still referenced and cannot be deleted.")) from exc


# --- Policy (the document) ---------------------------------------------------


class PolicyViewSet(BatchCreateMixin, ScopeFilterAPIMixin, LifecycleAPIMixin, HistoryAPIMixin, _DocumentsViewSet):
    """The register of governing documents : identity, review cycle, structure."""

    queryset = (
        Policy.objects.select_related("owner", "approver", "parent", "last_reviewed_by")
        .prefetch_related(
            "scopes", "tags", "linked_requirements", "applies_to_roles",
            Prefetch(
                "versions",
                queryset=PolicyVersion.objects.defer("file_content").filter(workflow_state=VERSION_IN_FORCE),
                to_attr="_in_force",
            ),
        )
        .all()
    )
    filterset_class = PolicyFilter
    permission_feature = "policy"
    search_fields = ["reference", "title", "summary"]
    ordering_fields = [
        "reference", "title", "document_type", "classification", "workflow_state",
        "next_review_date", "last_reviewed_at", "created_at", "updated_at",
    ]
    custom_action_map = {
        **_DocumentsViewSet.custom_action_map,
        "record_review": "approve",
        "new_version": "update",
    }

    def get_serializer_class(self):
        if self.action == "list":
            return PolicyListSerializer
        return PolicySerializer

    @action(detail=True, methods=["post"], url_path="record-review")
    def record_review(self, request, **kwargs):
        """Reviewed, no change (RG-DOC-13).

        Stamps ``last_reviewed_at`` / ``last_reviewed_by`` and recomputes the
        next review date, with a history entry carrying the comment. Requires
        ``documents.policy.approve``; only an active document can be reviewed.
        Body : ``{"comment": "..."}`` (optional).
        """
        policy = self.get_object()
        comment = (request.data.get("comment") or "").strip()
        try:
            policy.record_review(request.user, comment)
        except LifecycleError as exc:
            return _domain_response(exc)
        except DjangoValidationError as exc:
            raise _validation_error(exc) from exc
        policy = self.get_queryset().get(pk=policy.pk)
        return Response(PolicySerializer(policy, context=self.get_serializer_context()).data)

    @action(detail=True, methods=["post"], url_path="new-version")
    def new_version(self, request, **kwargs):
        """Draft the next version from the one in force (RG-DOC-05).

        Body : ``{"bump": "minor" | "major"}`` (default ``minor``). Copies the
        in-force content and PDF into a new draft with the next label
        (``1.2 -> 1.3`` or ``2.0``) and an empty change summary. On a document
        with no version yet it drafts ``1.0``. A retired document is a closed
        record and takes no new version.
        """
        policy = self.get_object()
        bump = (request.data.get("bump") or "minor").strip()
        if bump not in VERSION_BUMPS:
            return Response(
                {"bump": [_("Choose 'minor' or 'major'.")]}, status=status.HTTP_400_BAD_REQUEST,
            )
        if policy.workflow_state == POLICY_RETIRED:
            return Response(
                {"detail": _("A retired document is a closed record : re-issue it as a new document.")},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            version = policy.new_version(request.user, bump=bump)
        except LifecycleError as exc:
            return _domain_response(exc)
        except DjangoValidationError as exc:
            raise _validation_error(exc) from exc
        return Response(
            PolicyVersionSerializer(version, context=self.get_serializer_context()).data,
            status=status.HTTP_201_CREATED,
        )


# --- PolicyVersion -----------------------------------------------------------


class PolicyVersionViewSet(BatchCreateMixin, ScopeFilterAPIMixin, LifecycleAPIMixin, HistoryAPIMixin, _DocumentsViewSet):
    """The versions of every document. Content is frozen from ``in_review``
    (RG-DOC-02); only a draft is deletable."""

    queryset = _versions_without_bytes().select_related(
        "policy", "approved_by", "superseded_by", "created_by",
    ).prefetch_related("tags")
    filterset_class = PolicyVersionFilter
    permission_feature = "policy"
    search_fields = ["reference", "version_label", "change_summary", "policy__reference", "policy__title"]
    ordering_fields = ["reference", "version_label", "workflow_state", "approved_at", "effective_from", "created_at"]

    def get_serializer_class(self):
        if self.action == "list":
            return PolicyVersionListSerializer
        return PolicyVersionSerializer


# --- AcknowledgementCampaign -------------------------------------------------


class AcknowledgementCampaignViewSet(
    BatchCreateMixin, ScopeFilterAPIMixin, LifecycleAPIMixin, HistoryAPIMixin, _DocumentsViewSet,
):
    """Requests to an audience to acknowledge one version in force."""

    queryset = (
        AcknowledgementCampaign.objects.select_related("policy_version__policy")
        .defer("policy_version__file_content")
        .prefetch_related("scopes", "tags", "audience_users", "audience_groups", "audience_roles")
        .all()
    )
    filterset_class = AcknowledgementCampaignFilter
    permission_feature = "acknowledgement"
    search_fields = ["reference", "name", "policy_version__policy__title", "policy_version__reference"]
    ordering_fields = ["reference", "name", "workflow_state", "due_date", "launched_at", "closed_at", "created_at"]
    custom_action_map = {**_DocumentsViewSet.custom_action_map, "add_newcomers": "update"}

    def get_serializer_class(self):
        if self.action == "list":
            return AcknowledgementCampaignListSerializer
        return AcknowledgementCampaignSerializer

    @action(detail=True, methods=["post"], url_path="add-newcomers")
    def add_newcomers(self, request, **kwargs):
        """Re-resolve the audience of a running campaign (RG-DOC-15).

        Creates a pending row for every resolved addressee who has none yet
        and notifies them; existing rows are never touched. Recorded in the
        campaign history. Requires ``documents.acknowledgement.update``.
        """
        campaign = self.get_object()
        try:
            rows = campaign.add_newcomers(request.user)
        except LifecycleError as exc:
            return _domain_response(exc)
        except DjangoValidationError as exc:
            raise _validation_error(exc) from exc
        campaign.refresh_from_db()
        return Response({
            "added": len(rows),
            "added_user_ids": [str(row.user_id) for row in rows],
            "campaign": AcknowledgementCampaignSerializer(campaign, context=self.get_serializer_context()).data,
        })


# --- PolicyAcknowledgement ---------------------------------------------------


class AcknowledgementPermission(BasePermission):
    """Reading is open to every authenticated user, on a queryset that only
    holds their own rows plus, with ``documents.acknowledgement.read``, the
    rows of the campaigns they may read. Acknowledging needs no permission
    (RG-DOC-17 : the model refuses anyone but the addressee). Excusing needs
    ``documents.acknowledgement.update``."""

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if getattr(view, "action", None) == "excuse":
            return user.is_superuser or user.has_perm("documents.acknowledgement.update")
        return True


class PolicyAcknowledgementViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """The acknowledgement rows : read, ``mine``, ``acknowledge``, ``excuse``.
    No create, update or delete route exists (RG-DOC-16).

    No ``history/`` route either, for now : the rows are created by
    ``bulk_create`` at launch, which writes no creation record, so the
    unified timeline has no first entry to diff against. The row itself
    carries every stamp (requested, acknowledged / excused, by whom, how).
    """

    serializer_class = PolicyAcknowledgementSerializer
    permission_classes = [AcknowledgementPermission]
    filterset_class = PolicyAcknowledgementFilter
    search_fields = ["user__email", "user__first_name", "user__last_name", "campaign__reference", "campaign__name"]
    ordering_fields = ["status", "requested_at", "acknowledged_at", "excused_at", "campaign__due_date"]
    queryset = PolicyAcknowledgement.objects.select_related(
        "campaign__policy_version__policy", "user", "excused_by",
    ).defer("campaign__policy_version__file_content")

    def _scope_readable(self, qs):
        """Rows of the campaigns the caller may read (permission and scopes)."""
        user = self.request.user
        if user.is_superuser:
            return qs
        if not user.has_perm("documents.acknowledgement.read"):
            return qs.none()
        scope_ids = user.get_allowed_scope_ids()
        if scope_ids is None:
            return qs
        return filter_queryset_by_scopes(qs, scope_ids)

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.is_superuser:
            return qs
        readable = self._scope_readable(PolicyAcknowledgement.objects.all()).values("pk")
        return qs.filter(Q(pk__in=readable) | Q(user=user))

    @action(detail=False, methods=["get"])
    def mine(self, request, **kwargs):
        """The caller's own rows, pending first, then the most recent."""
        qs = self.filter_queryset(
            super().get_queryset().filter(user=request.user)
        ).annotate(
            _pending_first=Case(
                When(status=AcknowledgementStatus.PENDING, then=Value(0)),
                default=Value(1), output_field=IntegerField(),
            ),
        ).order_by("_pending_first", "campaign__due_date", "-requested_at")
        page = self.paginate_queryset(qs)
        if page is not None:
            return self.get_paginated_response(self.get_serializer(page, many=True).data)
        return Response(self.get_serializer(qs, many=True).data)

    @action(detail=True, methods=["post"])
    def acknowledge(self, request, **kwargs):
        """The addressee acknowledges their pending row (RG-DOC-16 / RG-DOC-17).

        Stamps ``acknowledged_at``, snapshots the confirmed statement and
        records the ``api`` channel. Anyone but the addressee, an administrator
        included, is refused with a 400; a row already acknowledged, excused or
        expired, or a closed campaign, is refused too.
        """
        row = self.get_object()
        try:
            row.acknowledge(request.user, channel=AcknowledgementChannel.API)
        except LifecycleError as exc:
            return _domain_response(exc)
        except DjangoValidationError as exc:
            raise _validation_error(exc) from exc
        row.refresh_from_db()
        return Response(self.get_serializer(row).data)

    @action(detail=True, methods=["post"])
    def excuse(self, request, **kwargs):
        """Excuse a pending row with a mandatory reason (RG-DOC-19).

        Body : ``{"reason": "..."}``. Requires
        ``documents.acknowledgement.update`` and the campaign within the
        caller's scopes (being the addressee is not enough to excuse oneself).
        """
        row = self.get_object()
        if not self._scope_readable(PolicyAcknowledgement.objects.filter(pk=row.pk)).exists():
            raise PermissionDenied(_("This acknowledgement is outside your scopes."))
        reason = (request.data.get("reason") or "").strip()
        try:
            row.excuse(request.user, reason)
        except LifecycleError as exc:
            return _domain_response(exc)
        except DjangoValidationError as exc:
            raise _validation_error(exc) from exc
        row.refresh_from_db()
        return Response(self.get_serializer(row).data)
