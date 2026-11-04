# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""DRF viewsets for module 8 (controls), mounted at ``/api/v1/controls/``.

Rules stated once for the whole file :

**Two permission features.** ``controls.control`` governs controls (and the
"create from requirements" action); ``controls.test`` governs tests, runs and
the "raise a finding" action, which needs ``controls.test.approve`` (README §4).

**A state change is a transition.** No view writes ``workflow_state``. The
``/transition/`` endpoint comes from ``LifecycleAPIMixin`` and goes through each
model's ``transition_to(enforce_permission=True)`` with the authenticated user
as the actor, so the gates (RG-CTL-06, -10), the segregation of duties
(RG-CTL-11 : a run's performer cannot validate it, superusers included) and the
recomputations (RG-CTL-12) hold on this surface exactly as on the stepper. A
gate refusal reaches the client as a 400 with the model's translated reason; a
refused permission is a 403.

**Tenancy.** Controls carry their own ``scopes``; tests and runs inherit
theirs through ``scope_parent_lookup`` (RG-CTL-19), which
``ScopeFilterAPIMixin`` resolves. Out-of-scope rows are 404.
"""

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Count, Min, Prefetch, Q
from django.db.models.deletion import ProtectedError
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import APIException, PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.api.mixins import BatchCreateMixin, HistoryAPIMixin, LifecycleAPIMixin, ScopeFilterAPIMixin
from accounts.api.permissions import ModulePermission
from compliance.constants import FindingType
from compliance.models import Finding, Framework
from controls.constants import TEST_ACTIVE
from controls.models import Control, ControlTest, ControlTestEvidence, ControlTestRun
from controls.services import create_controls_from_requirements
from core.lifecycle import LifecycleError, LifecycleProtectedError, TransitionNotAllowedError
from core.transition_messages import transition_error_detail

from .filters import ControlFilter, ControlTestFilter, ControlTestRunFilter
from .serializers import (
    ControlListSerializer,
    ControlSerializer,
    ControlTestListSerializer,
    ControlTestRunListSerializer,
    ControlTestRunSerializer,
    ControlTestSerializer,
    scoped_for,
)


#: RG-CTL-16 : a failed or partial run is a nonconformity or an observation;
#: improvement opportunities and strengths are not raised from a test.
RAISABLE_FINDING_TYPES = (
    FindingType.MAJOR_NON_CONFORMITY,
    FindingType.MINOR_NON_CONFORMITY,
    FindingType.OBSERVATION,
)


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
    """403 for a refused permission, 400 with the model's reason otherwise."""
    if isinstance(exc, TransitionNotAllowedError):
        raise PermissionDenied(transition_error_detail(exc))
    return Response({"detail": transition_error_detail(exc)}, status=status.HTTP_400_BAD_REQUEST)


def _id_list(value, name):
    """A list of ids from a request body, or ``None`` when absent."""
    if value in (None, ""):
        return None
    if not isinstance(value, list):
        raise serializers.ValidationError({name: [_("Expected a list of identifiers.")]})
    return [str(item) for item in value]


class _ControlsViewSet(viewsets.ModelViewSet):
    """The shared base : module permission, created-by stamp, governed writes."""

    permission_classes = [IsAuthenticated, ModulePermission]
    permission_module = "controls"
    custom_action_map = {
        "transition": "update",
        "batch_create": "create",
        "history": "read",
    }

    def _guarded_save(self, serializer, **kwargs):
        """Save, turning each governance refusal into its own status code
        instead of a 500 : the models refuse a frozen run (RG-CTL-09) and a
        run on an inactive test in ``save()``, and that guard is the real one."""
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
        except DjangoValidationError as exc:
            raise _validation_error(exc) from exc


# --- Control -----------------------------------------------------------------


class ControlViewSet(BatchCreateMixin, ScopeFilterAPIMixin, LifecycleAPIMixin, HistoryAPIMixin, _ControlsViewSet):
    """The register of controls : identity, links, derived effectiveness."""

    queryset = (
        Control.objects.select_related("owner")
        .prefetch_related(
            "scopes", "tags", "requirements", "risks", "treatment_plans", "pacs_measures",
            "support_assets", "objectives", "policies",
        )
        .annotate(
            _next_test_due=Min("tests__next_due_date", filter=Q(tests__workflow_state=TEST_ACTIVE)),
            _requirement_count=Count("requirements", distinct=True),
        )
        # An aggregated queryset drops Meta.ordering : restate it for stable pages.
        .order_by("reference")
    )
    filterset_class = ControlFilter
    permission_feature = "control"
    search_fields = ["reference", "name", "description"]
    ordering_fields = [
        "reference", "name", "theme", "nature", "automation", "effectiveness", "workflow_state",
        "implemented_on", "created_at", "updated_at",
    ]
    custom_action_map = {**_ControlsViewSet.custom_action_map, "from_requirements": "create"}

    def get_serializer_class(self):
        if self.action == "list":
            return ControlListSerializer
        return ControlSerializer

    @action(detail=False, methods=["post"], url_path="from-requirements")
    def from_requirements(self, request, **kwargs):
        """Draft one control per uncovered applicable requirement (RG-CTL-05).

        Body : ``{"framework_id": "<uuid>", "requirement_ids": [...],
        "scope_ids": [...]}``; only ``framework_id`` is required. Without
        ``requirement_ids`` every requirement of the framework is considered;
        without ``scope_ids`` the controls take the framework's scopes.
        Requirements already covered by a control (any step) or not applicable
        are skipped and reported. Requires ``controls.control.create`` and the
        framework readable by the caller (``compliance.framework.read`` and
        its scopes).
        """
        user = request.user
        framework_id = request.data.get("framework_id")
        if not framework_id:
            raise serializers.ValidationError({"framework_id": [_("This field is required.")]})
        if not (user.is_superuser or user.has_perm("compliance.framework.read")):
            raise PermissionDenied()
        try:
            framework = scoped_for(user, Framework.objects.all()).get(pk=framework_id)
        except (Framework.DoesNotExist, DjangoValidationError, ValueError) as exc:
            raise serializers.ValidationError({"framework_id": [_("Framework not found.")]}) from exc
        requirement_ids = _id_list(request.data.get("requirement_ids"), "requirement_ids")
        scope_ids = _id_list(request.data.get("scope_ids"), "scope_ids")
        if scope_ids is not None:
            from context.models import Scope

            allowed = set(
                str(pk) for pk in scoped_for(user, Scope.objects.filter(pk__in=scope_ids)).values_list("pk", flat=True)
            )
            unknown = [pk for pk in scope_ids if pk not in allowed]
            if unknown:
                raise serializers.ValidationError({"scope_ids": [_("Unknown scope or outside your scopes.")]})
        try:
            created, skipped = create_controls_from_requirements(
                framework, user, requirement_ids=requirement_ids, scope_ids=scope_ids,
            )
        except DjangoValidationError as exc:
            raise _validation_error(exc) from exc
        context = self.get_serializer_context()
        created = Control.objects.filter(pk__in=[c.pk for c in created]).prefetch_related("scopes")
        return Response(
            {
                "framework_id": str(framework.pk),
                "created": ControlListSerializer(created, many=True, context=context).data,
                "skipped": [
                    {
                        "id": str(requirement.pk),
                        "requirement_number": requirement.requirement_number,
                        "name": requirement.name,
                        "reason": "not_applicable" if not requirement.is_applicable else "already_covered",
                    }
                    for requirement in skipped
                ],
            },
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


# --- ControlTest -------------------------------------------------------------


class ControlTestViewSet(BatchCreateMixin, ScopeFilterAPIMixin, LifecycleAPIMixin, HistoryAPIMixin, _ControlsViewSet):
    """How each control is tested; ``next_due_date`` is derived (RG-CTL-07)."""

    queryset = ControlTest.objects.select_related("control", "tester").prefetch_related("tags").all()
    filterset_class = ControlTestFilter
    permission_feature = "test"
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]
    search_fields = ["reference", "name", "objective", "control__reference", "control__name"]
    ordering_fields = [
        "reference", "name", "method", "frequency_months", "next_due_date", "workflow_state", "created_at",
    ]

    def get_serializer_class(self):
        if self.action == "list":
            return ControlTestListSerializer
        return ControlTestSerializer


# --- ControlTestRun ----------------------------------------------------------


class ControlTestRunViewSet(BatchCreateMixin, ScopeFilterAPIMixin, LifecycleAPIMixin, HistoryAPIMixin, _ControlsViewSet):
    """The runs of every test : frozen once submitted (RG-CTL-09), validated by
    someone other than their performer (RG-CTL-11). Only a draft is deletable."""

    queryset = (
        ControlTestRun.objects.select_related("test__control", "performed_by", "reviewed_by")
        .prefetch_related(
            "tags",
            Prefetch("evidence", queryset=ControlTestEvidence.objects.select_related("uploaded_by")),
            Prefetch("findings", queryset=Finding.objects.only("id", "reference", "finding_type", "control_test_run")),
        )
        .all()
    )
    filterset_class = ControlTestRunFilter
    permission_feature = "test"
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]
    search_fields = ["reference", "observations", "sample_description", "test__reference", "test__name"]
    ordering_fields = ["reference", "performed_on", "result", "workflow_state", "reviewed_at", "created_at"]
    custom_action_map = {**_ControlsViewSet.custom_action_map, "raise_finding": "approve"}

    def get_serializer_class(self):
        if self.action == "list":
            return ControlTestRunListSerializer
        return ControlTestRunSerializer

    @action(detail=True, methods=["post"], url_path="raise-finding")
    def raise_finding(self, request, **kwargs):
        """Raise a finding from a validated partial or failed run (RG-CTL-16).

        Body : ``{"finding_type": "major_nc" | "minor_nc" | "observation",
        "recommendation": "..."}``. Creates a finding with source
        ``control_test``, linked to the run, the run's observations as its
        description, the control's requirements as its related requirements and
        the caller as the person who raised it. Offered once per run : a second
        call is refused. Requires ``controls.test.approve``.
        """
        run = self.get_object()
        finding_type = (request.data.get("finding_type") or "").strip()
        if finding_type not in RAISABLE_FINDING_TYPES:
            raise serializers.ValidationError({
                "finding_type": [_("Choose a valid finding type : major_nc, minor_nc or observation.")],
            })
        recommendation = request.data.get("recommendation") or ""
        try:
            finding = run.raise_finding(request.user, finding_type, recommendation)
        except LifecycleError as exc:
            return _domain_response(exc)
        except DjangoValidationError as exc:
            raise _validation_error(exc) from exc
        from compliance.api.serializers import FindingSerializer

        return Response(
            FindingSerializer(finding, context=self.get_serializer_context()).data,
            status=status.HTTP_201_CREATED,
        )
