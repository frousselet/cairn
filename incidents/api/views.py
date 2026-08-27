# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""DRF viewsets for module 6 (incidents).

Four rules govern this file and are stated once here rather than repeated in
thirteen docstrings :

**One permission base, six features.** Every viewset extends
:class:`_IncidentViewSet`, which fixes ``permission_module = "incidents"`` and
the shared ``custom_action_map``, following the newest module precedent
(``trust_center/api/views.py`` ``_ManagedViewSet``). No other app's
``ModulePermission`` subclass is imported : borrowing ``ContextPermission``
would borrow another domain's vocabulary for no benefit. The module is capped
at exactly six features - ``incident``, ``event``, ``response_plan``,
``evidence``, ``notification``, ``review`` - and the child entities are gated
by their parent's feature (RG-INC-39).

**A state change is a transition.** No view here ever writes
``workflow_state``. The lifecycle endpoint comes from ``LifecycleAPIMixin`` and
routes through ``transition_to(enforce_permission=True)``, which is where the
gates, the stamps and the immutable ``LifecycleEvent`` live. The four entities
that run no lifecycle simply do not mix it in, so no ``transition/`` route is
generated for them.

**Tenancy is declared, not assumed.** Every viewset over a non-``ScopedModel``
child sets ``scope_parent_lookup``, and :meth:`_IncidentViewSet.__init_subclass__`
refuses at import time any viewset whose model resolves to no scope path while
claiming to be scope filtered - and any viewset claiming exemption over a model
that does resolve one. The two catalogue viewsets state
``scope_filtered = False`` explicitly, so the choice reads as a decision in
review instead of an oversight.

**Append-only is enforced at the routing layer.** The three ledgers restrict
``http_method_names`` so no ``PUT``, ``PATCH`` or ``DELETE`` route answers at
all, with the single documented exception of the narrow completion ``PATCH`` on
a filing, which records the recipient's answer through the model's own
``record_outcome()``.
"""

from urllib.parse import quote

from django.core.exceptions import ImproperlyConfigured
from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import Http404, HttpResponse
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import APIException, PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.api.mixins import (
    BatchCreateMixin,
    HistoryAPIMixin,
    LifecycleAPIMixin,
    ScopeFilterAPIMixin,
)
from accounts.api.permissions import ModulePermission
from core.lifecycle import (
    LifecycleError,
    LifecycleProtectedError,
    TransitionNotAllowedError,
)
from core.transition_messages import transition_error_detail
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
from incidents.models.evidence import (
    VERIFICATION_MATCH,
    VERIFICATION_MISMATCH,
)

from .filters import (
    EvidenceCustodyEventFilter,
    IncidentEvidenceFilter,
    IncidentFilter,
    IncidentNotificationFilter,
    IncidentResponseActionFilter,
    IncidentResponsePlanFilter,
    IncidentTimelineEntryFilter,
    NotificationFilingFilter,
    PersonalDataBreachFilter,
    PostIncidentReviewFilter,
    ReportingAuthorityFilter,
    ReportingObligationTemplateFilter,
    SecurityEventFilter,
)
from .serializers import (
    EvidenceCustodyEventSerializer,
    IncidentEvidenceListSerializer,
    IncidentEvidenceSerializer,
    IncidentListSerializer,
    IncidentNotificationListSerializer,
    IncidentNotificationSerializer,
    IncidentResponseActionSerializer,
    IncidentResponsePlanListSerializer,
    IncidentResponsePlanSerializer,
    IncidentSerializer,
    IncidentTimelineEntrySerializer,
    NotificationFilingSerializer,
    PersonalDataBreachListSerializer,
    PersonalDataBreachSerializer,
    PostIncidentReviewListSerializer,
    PostIncidentReviewSerializer,
    ReportingAuthorityListSerializer,
    ReportingAuthoritySerializer,
    ReportingObligationTemplateListSerializer,
    ReportingObligationTemplateSerializer,
    SecurityEventListSerializer,
    SecurityEventSerializer,
)

#: The two append-only ledgers answer ``GET`` and ``POST`` and nothing else.
APPEND_ONLY_METHODS = ["get", "post", "head", "options"]

#: A filing adds exactly one ``PATCH``, for the three completion fields.
FILING_METHODS = ["get", "post", "patch", "head", "options"]

#: What a promotion may produce. Written here rather than derived from a step
#: code : these are argument values of the API, not lifecycle states.
PROMOTION_INCIDENT = "incident"
PROMOTION_VULNERABILITY = "vulnerability"


# --- Shared machinery --------------------------------------------------------


class Conflict(APIException):
    """409 : the row exists but its governance refuses the write.

    Distinct from a 400 on purpose. A validation error says *the payload is
    wrong*; this says *the payload is fine and the register will not accept it*
    - a sealed evidence item, an append-only ledger, an element whose step is
    not deletable. A client can fix the first by editing the request and can
    never fix the second.
    """

    status_code = status.HTTP_409_CONFLICT
    default_detail = _(
        "This element cannot be changed in its current lifecycle state."
    )
    default_code = "conflict"


def _attachment_disposition(filename):
    """Build a safe ``Content-Disposition`` value (no header injection)."""
    safe = (
        "".join(ch for ch in (filename or "") if ch not in '"\\\r\n').strip()
        or "download"
    )
    return f"attachment; filename=\"{safe}\"; filename*=UTF-8''{quote(safe)}"


def _validation_error(exc):
    """Translate a Django ``ValidationError`` into DRF's 400 shape."""
    if hasattr(exc, "message_dict"):
        return serializers.ValidationError(exc.message_dict)
    return serializers.ValidationError({"non_field_errors": list(exc.messages)})


def _model_scope_path(model):
    """The ORM path this model reaches ``context.Scope`` through, or ``None``.

    A local, import-safe echo of ``core.scoping.resolve_scope_lookup`` : it is
    read at class-creation time by :meth:`_IncidentViewSet.__init_subclass__`,
    where the app registry may not be ready to resolve a model by label. The
    ``Scope`` model itself is not a case this module has.
    """
    lookup = getattr(model, "scope_parent_lookup", None)
    if lookup:
        return lookup
    if any(field.name == "scopes" for field in model._meta.many_to_many):
        return "scopes"
    return None


class CreatedByMixin:
    """Stamp the row's author from the request user, never from the payload.

    ``created_by_field`` names the column that carries it, because the three
    append-only ledgers spell it differently and mean the same thing : an
    unattributed chronology line, custody act or filing is not evidence. The
    two entities that carry no such column set it to ``None``.
    """

    created_by_field = "created_by"

    def perform_create(self, serializer):
        field = self.created_by_field
        self._guarded_save(serializer, **({field: self.request.user} if field else {}))


class _IncidentViewSet(viewsets.ModelViewSet):
    """The shared base every viewset in the module extends.

    Identical across all thirteen : a viewset that needs its own actions in the
    permission map **extends** ``custom_action_map`` rather than redefining it,
    so the base can never drift entity by entity.
    """

    permission_classes = [IsAuthenticated, ModulePermission]
    permission_module = "incidents"
    custom_action_map = {
        "transition": "update",
        # `BatchCreateMixin` creates rows, so it consumes `create`. Without
        # this entry `_get_action()` falls through to the HTTP method and a
        # batch POST would be gated on `update` : on the append-only entities
        # that is a codename the entity's spec says no route consumes.
        "batch_create": "create",
    }

    #: Whether this viewset's model is expected to resolve a path to
    #: `context.Scope`. The catalogue entities set it to False explicitly.
    scope_filtered = True

    def __init_subclass__(cls, **kwargs):
        """Refuse, at import time, a viewset whose tenancy does not add up.

        The failure this guards is silent : a child model with no
        ``scope_parent_lookup`` makes ``ScopeFilterAPIMixin`` a no-op, and the
        register is then readable from outside the incident's perimeter with no
        error anywhere. Declaring the exemption is what makes the two catalogue
        viewsets a decision rather than the same oversight.
        """
        super().__init_subclass__(**kwargs)
        queryset = getattr(cls, "queryset", None)
        if queryset is None:
            return
        model = queryset.model
        path = getattr(cls, "scope_parent_lookup", None) or _model_scope_path(model)
        if cls.scope_filtered and path is None:
            raise ImproperlyConfigured(
                f"{cls.__name__} is scope filtered but {model.__name__} resolves "
                "no path to context.Scope : declare scope_parent_lookup, or "
                "scope_filtered = False if the entity is a shared catalogue."
            )
        if not cls.scope_filtered and path is not None:
            raise ImproperlyConfigured(
                f"{cls.__name__} claims no scope filtering, but "
                f"{model.__name__} resolves '{path}' : an entity that carries "
                "tenancy is always filtered by it."
            )

    # --- Write paths, with governance failures given the right status ------

    def _guarded_save(self, serializer, **kwargs):
        """Save, turning each governance refusal into its own status code.

        The models refuse write-once and append-only writes in ``save()``, and
        that guard is the real one. Without this translation a refusal reaches
        the client as a 500 : the payload was valid, the serializer was happy,
        and the register said no.
        """
        try:
            serializer.save(**kwargs)
        except DjangoValidationError as exc:
            raise _validation_error(exc) from exc
        except TransitionNotAllowedError as exc:
            raise PermissionDenied(transition_error_detail(exc)) from exc
        except LifecycleError as exc:
            raise serializers.ValidationError(
                {"non_field_errors": [transition_error_detail(exc)]}
            ) from exc
        except LifecycleProtectedError as exc:
            # Never `str(exc)` in a response body (CodeQL py/stack-trace-exposure).
            raise Conflict() from exc

    def perform_update(self, serializer):
        self._guarded_save(serializer)

    def perform_destroy(self, instance):
        try:
            instance.delete()
        except LifecycleProtectedError as exc:
            raise Conflict(
                _("This element cannot be deleted in its current lifecycle state.")
            ) from exc


# --- Incident response plan (A.5.24) -----------------------------------------


class IncidentResponsePlanViewSet(
    BatchCreateMixin,
    ScopeFilterAPIMixin,
    LifecycleAPIMixin,
    HistoryAPIMixin,
    CreatedByMixin,
    _IncidentViewSet,
):
    """The procedure the response runs on, and the register of its exercises."""

    queryset = (
        IncidentResponsePlan.objects.select_related("owner", "approved_by")
        .prefetch_related("scopes", "tags", "responsible_roles")
        .all()
    )
    filterset_class = IncidentResponsePlanFilter
    permission_feature = "response_plan"
    search_fields = ["reference", "name", "purpose"]
    ordering_fields = [
        "reference", "name", "workflow_state", "effective_from",
        "review_date", "last_exercise_date", "created_at",
    ]

    def get_serializer_class(self):
        if self.action == "list":
            return IncidentResponsePlanListSerializer
        return IncidentResponsePlanSerializer


# --- Security event (A.6.8 intake / A.5.25 assessment) -----------------------


class SecurityEventViewSet(
    BatchCreateMixin,
    ScopeFilterAPIMixin,
    LifecycleAPIMixin,
    HistoryAPIMixin,
    CreatedByMixin,
    _IncidentViewSet,
):
    """The intake register, and the one act that empties it : promotion."""

    queryset = (
        SecurityEvent.objects.select_related(
            "reporter", "assessed_by", "incident", "vulnerability",
            "duplicate_of", "reported_by_supplier",
        )
        .prefetch_related("scopes", "tags")
        .all()
    )
    filterset_class = SecurityEventFilter
    permission_feature = "event"
    search_fields = ["reference", "title", "description", "source_reference"]
    ordering_fields = [
        "reference", "title", "event_class", "category", "workflow_state",
        "occurred_at", "detected_at", "reported_at", "assessed_at",
        "created_at",
    ]
    custom_action_map = {**_IncidentViewSet.custom_action_map, "promote": "update"}

    def get_serializer_class(self):
        if self.action == "list":
            return SecurityEventListSerializer
        return SecurityEventSerializer

    @action(detail=True, methods=["post"], url_path="promote")
    def promote(self, request, **kwargs):
        """Promote an assessed event into an incident or into a weakness.

        One atomic act and not a sequence a client can abandon halfway : the
        model creates the target, declares it through its own lifecycle,
        links it and moves the event on, all inside one transaction. The
        A.5.25 verdict is the transition, so the comment is mandatory and the
        transition's own permission is enforced on top of the create
        permission of whichever register receives the row.

        Nothing carried across is overridable here. The values are the event's
        by design, and the created row is a fully editable resource one
        ``PATCH`` away on its own endpoint, where its own validation applies.
        """
        event = self.get_object()
        target = (request.data.get("target") or PROMOTION_INCIDENT).strip()
        comment = (request.data.get("comment") or "").strip()

        if target not in (PROMOTION_INCIDENT, PROMOTION_VULNERABILITY):
            return Response(
                {"target": [_("Promote to 'incident' or to 'vulnerability'.")]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not comment:
            return Response(
                {
                    "comment": [
                        _(
                            "A comment is required : promotion is the assessment "
                            "verdict, and the transition records why it was "
                            "reached."
                        )
                    ]
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        required_perm = (
            "incidents.incident.create"
            if target == PROMOTION_INCIDENT
            else "risks.vulnerability.create"
        )
        if not request.user.is_superuser and not request.user.has_perm(required_perm):
            raise PermissionDenied(
                _("You do not have permission to create the promoted element.")
            )

        try:
            if target == PROMOTION_INCIDENT:
                created = event.promote_to_incident(
                    request.user, comment, enforce_permission=True
                )
            else:
                created = event.promote_to_vulnerability(
                    request.user, comment, enforce_permission=True
                )
        except TransitionNotAllowedError as exc:
            return Response(
                {"detail": transition_error_detail(exc)},
                status=status.HTTP_403_FORBIDDEN,
            )
        except LifecycleError as exc:
            return Response(
                {"detail": transition_error_detail(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except DjangoValidationError as exc:
            raise _validation_error(exc) from exc

        event.refresh_from_db()
        payload = {"event": self.get_serializer(event).data}
        if target == PROMOTION_INCIDENT:
            payload["incident"] = IncidentSerializer(
                created, context=self.get_serializer_context()
            ).data
        else:
            payload["vulnerability"] = {
                "id": str(created.pk),
                "reference": getattr(created, "reference", None),
                "name": getattr(created, "name", ""),
                "status": created.workflow_state,
            }
        return Response(payload, status=status.HTTP_201_CREATED)


# --- Incident (A.5.26) -------------------------------------------------------


class IncidentViewSet(
    BatchCreateMixin,
    ScopeFilterAPIMixin,
    LifecycleAPIMixin,
    HistoryAPIMixin,
    CreatedByMixin,
    _IncidentViewSet,
):
    """The register itself. Every phase timestamp on it is a transition stamp."""

    queryset = (
        Incident.objects.select_related(
            "incident_manager", "reporter", "response_plan", "origin_supplier",
            "parent_incident",
        )
        .prefetch_related("scopes", "tags")
        .all()
    )
    filterset_class = IncidentFilter
    permission_feature = "incident"
    search_fields = ["reference", "title", "summary", "description"]
    ordering_fields = [
        "reference", "title", "severity", "initial_severity", "category",
        "workflow_state", "occurred_at", "detected_at", "awareness_at",
        "declared_at", "closed_at", "created_at",
    ]

    def get_serializer_class(self):
        if self.action == "list":
            return IncidentListSerializer
        return IncidentSerializer


# --- Chronology (append-only) ------------------------------------------------


class IncidentTimelineEntryViewSet(
    BatchCreateMixin,
    ScopeFilterAPIMixin,
    HistoryAPIMixin,
    CreatedByMixin,
    _IncidentViewSet,
):
    """Create, list and retrieve. There is no fourth verb.

    ``IncidentTimelineEntry.save()`` refuses every post-insert write and
    ``delete()`` refuses outright, so ``http_method_names`` withholds the
    routes rather than letting the router publish three endpoints that can only
    ever fail. A factual error is corrected by appending an entry that
    supersedes the wrong one.
    """

    queryset = IncidentTimelineEntry.objects.select_related(
        "incident", "author", "related_action", "related_evidence",
        "superseded_entry",
    ).all()
    serializer_class = IncidentTimelineEntrySerializer
    filterset_class = IncidentTimelineEntryFilter
    permission_feature = "incident"
    scope_parent_lookup = "incident__scopes"
    created_by_field = "author"
    http_method_names = APPEND_ONLY_METHODS
    search_fields = ["summary", "detail", "incident__reference", "incident__title"]
    ordering_fields = ["occurred_at", "recorded_at", "entry_type", "created_at"]

    def _get_batch_create_kwargs(self, request):
        # `BatchCreateMixin` sits ahead of every base in the MRO, so the author
        # stamp has to be declared here to reach the batch path too.
        return {self.created_by_field: request.user}


# --- Response actions --------------------------------------------------------


class IncidentResponseActionViewSet(
    BatchCreateMixin,
    ScopeFilterAPIMixin,
    HistoryAPIMixin,
    CreatedByMixin,
    _IncidentViewSet,
):
    """Full CRUD, no ``transition/`` route : the row runs no lifecycle.

    Its ``status`` is a genuine model column and the one place in the module
    where a writable ``status`` is correct rather than a bug. Governance is the
    parent incident's, which is also where the tenancy comes from.
    """

    queryset = IncidentResponseAction.objects.select_related(
        "incident", "owner", "performed_by"
    ).all()
    serializer_class = IncidentResponseActionSerializer
    filterset_class = IncidentResponseActionFilter
    permission_feature = "incident"
    scope_parent_lookup = "incident__scopes"
    #: `ReferenceGeneratorMixin`, not `BaseModel` : there is no `created_by`.
    created_by_field = None
    search_fields = ["reference", "title", "description", "incident__reference"]
    ordering_fields = [
        "reference", "title", "action_type", "status", "due_at",
        "started_at", "completed_at", "created_at",
    ]


# --- Evidence (A.5.28) -------------------------------------------------------


class IncidentEvidenceViewSet(
    BatchCreateMixin,
    ScopeFilterAPIMixin,
    LifecycleAPIMixin,
    HistoryAPIMixin,
    CreatedByMixin,
    _IncidentViewSet,
):
    """The evidence register, its artefacts and their re-measurement.

    The ``file`` payload appears in no serializer : the bytes are reachable
    only through :meth:`download`, which resolves the row through the scoped
    queryset and checks ``incidents.evidence.read`` like every other read.
    """

    queryset = IncidentEvidence.objects.select_related(
        "incident", "collected_by", "source_support_asset",
        "destruction_authorised_by",
    ).prefetch_related("tags").all()
    filterset_class = IncidentEvidenceFilter
    permission_feature = "evidence"
    scope_parent_lookup = "incident__scopes"
    search_fields = [
        "reference", "title", "description", "storage_location",
        "original_filename", "content_hash",
    ]
    ordering_fields = [
        "reference", "title", "evidence_type", "workflow_state",
        "collected_at", "sealed_at", "last_integrity_check_at",
        "retention_until", "created_at",
    ]
    custom_action_map = {
        **_IncidentViewSet.custom_action_map,
        "verify_integrity": "update",
        "download": "read",
    }

    def get_serializer_class(self):
        if self.action == "list":
            return IncidentEvidenceListSerializer
        return IncidentEvidenceSerializer

    @action(detail=True, methods=["get"], url_path="download")
    def download(self, request, **kwargs):
        """Stream the stored artefact, scope- and permission-checked.

        Never a raw media URL : an artefact carries the incident's TLP caveat,
        and a guessable path would put a TLP:RED item one URL away from anyone.
        A row registered by reference and a destroyed one both hold no bytes
        and are a 404 here, which is the same answer the register gives.
        """
        item = self.get_object()
        if not item.has_file:
            raise Http404()
        try:
            handle = item.file.open("rb")
        except (FileNotFoundError, OSError):
            # The register may legitimately outlive its media volume. A missing
            # artefact is a 404, never a traceback naming the storage path.
            raise Http404() from None
        with handle:
            data = handle.read()
        response = HttpResponse(data, content_type="application/octet-stream")
        response["Content-Disposition"] = _attachment_disposition(
            item.original_filename or f"{item.reference}.bin"
        )
        return response

    @action(detail=True, methods=["post"], url_path="verify-integrity")
    def verify_integrity(self, request, **kwargs):
        """Re-measure the artefact, append the ledger row, return the verdict.

        Not a lifecycle transition : verification does not move the item, it
        records a measurement. The three-way outcome is the model's, verbatim
        and never collapsed into two : a mismatch is a claim about the
        artefact, an unreadable one is a claim about the infrastructure, and an
        auditor has to be able to tell them apart.
        """
        item = self.get_object()
        notes = (request.data.get("notes") or "").strip()
        outcome = item.verify_integrity(request.user, notes=notes)
        if outcome == VERIFICATION_MATCH:
            detail = _("Integrity verified : the artefact matches its recorded digest.")
        elif outcome == VERIFICATION_MISMATCH:
            detail = _(
                "Integrity check failed : the artefact no longer matches its "
                "recorded digest."
            )
        else:
            detail = _(
                "Integrity could not be verified : the artefact could not be "
                "read. Check its storage location."
            )
        item.refresh_from_db()
        return Response(
            {
                "outcome": outcome,
                "detail": detail,
                "evidence": self.get_serializer(item).data,
            }
        )


# --- Chain of custody (append-only) ------------------------------------------


class EvidenceCustodyEventViewSet(
    BatchCreateMixin,
    ScopeFilterAPIMixin,
    HistoryAPIMixin,
    CreatedByMixin,
    _IncidentViewSet,
):
    """Create, list and retrieve. The ledger is append-only at the router.

    Appending is ``incidents.evidence.update`` and not ``.create`` : recording
    a handling act maintains the evidence item, it does not create a new
    governed object. ``.delete`` and ``.approve`` are consumed by no route
    here.
    """

    queryset = EvidenceCustodyEvent.objects.select_related(
        "evidence", "evidence__incident", "actor"
    ).all()
    serializer_class = EvidenceCustodyEventSerializer
    filterset_class = EvidenceCustodyEventFilter
    permission_feature = "evidence"
    scope_parent_lookup = "evidence__incident__scopes"
    created_by_field = "actor"
    http_method_names = APPEND_ONLY_METHODS
    custom_action_map = {
        **_IncidentViewSet.custom_action_map,
        "create": "update",
        "batch_create": "update",
    }
    search_fields = [
        "counterparty", "counterparty_organisation", "location", "notes",
        "evidence__reference",
    ]
    ordering_fields = ["occurred_at", "recorded_at", "action"]

    def _get_batch_create_kwargs(self, request):
        # See `IncidentTimelineEntryViewSet._get_batch_create_kwargs`.
        return {self.created_by_field: request.user}


# --- Post-incident review (A.5.27 / clause 10.2) -----------------------------


class PostIncidentReviewViewSet(
    BatchCreateMixin,
    ScopeFilterAPIMixin,
    LifecycleAPIMixin,
    HistoryAPIMixin,
    CreatedByMixin,
    _IncidentViewSet,
):
    """The lessons-learned record. Its tenancy is the incident's, re-synced."""

    queryset = (
        PostIncidentReview.objects.select_related(
            "incident", "response_plan", "facilitator", "effectiveness_reviewed_by"
        )
        .prefetch_related("scopes", "tags", "participants")
        .all()
    )
    filterset_class = PostIncidentReviewFilter
    permission_feature = "review"
    search_fields = [
        "reference", "root_cause", "what_went_well", "what_failed",
        "incident__reference", "incident__title",
    ]
    ordering_fields = [
        "reference", "workflow_state", "scheduled_date", "held_at",
        "effectiveness_review_date", "effectiveness_reviewed_at", "created_at",
    ]

    def get_serializer_class(self):
        if self.action == "list":
            return PostIncidentReviewListSerializer
        return PostIncidentReviewSerializer


# --- Regulatory catalogue ----------------------------------------------------


class ReportingAuthorityViewSet(
    BatchCreateMixin,
    ScopeFilterAPIMixin,
    LifecycleAPIMixin,
    HistoryAPIMixin,
    CreatedByMixin,
    _IncidentViewSet,
):
    """The catalogue of the bodies filings go to.

    ``scope_filtered = False`` is stated rather than left implicit : the CNIL is
    the CNIL for every scope of the ISMS, so the row carries neither ``scopes``
    nor a parent, and the exemption is a decision a reviewer can see. Gated by
    ``incidents.response_plan.*`` : the catalogue is part of the procedure.
    """

    queryset = ReportingAuthority.objects.prefetch_related("tags").all()
    filterset_class = ReportingAuthorityFilter
    permission_feature = "response_plan"
    scope_filtered = False
    search_fields = ["reference", "name", "short_name", "jurisdiction_country"]
    ordering_fields = [
        "reference", "name", "short_name", "authority_type", "primary_regime",
        "jurisdiction_country", "workflow_state", "created_at",
    ]

    def get_serializer_class(self):
        if self.action == "list":
            return ReportingAuthorityListSerializer
        return ReportingAuthoritySerializer


class ReportingObligationTemplateViewSet(
    BatchCreateMixin,
    ScopeFilterAPIMixin,
    LifecycleAPIMixin,
    HistoryAPIMixin,
    CreatedByMixin,
    _IncidentViewSet,
):
    """The rules that decide which obligations an incident raises.

    Same deliberate tenancy exemption as the authority catalogue, and the same
    permission feature : editing the rule set is editing the procedure.
    """

    queryset = (
        ReportingObligationTemplate.objects.select_related("authority")
        .prefetch_related("tags")
        .all()
    )
    filterset_class = ReportingObligationTemplateFilter
    permission_feature = "response_plan"
    scope_filtered = False
    search_fields = ["reference", "name", "legal_reference", "authority__name"]
    ordering_fields = [
        "reference", "name", "regime", "recipient_kind", "clock_hours",
        "min_severity", "order", "workflow_state", "created_at",
    ]

    def get_serializer_class(self):
        if self.action == "list":
            return ReportingObligationTemplateListSerializer
        return ReportingObligationTemplateSerializer


# --- Notification obligations ------------------------------------------------


class IncidentNotificationViewSet(
    BatchCreateMixin,
    ScopeFilterAPIMixin,
    LifecycleAPIMixin,
    HistoryAPIMixin,
    CreatedByMixin,
    _IncidentViewSet,
):
    """What is owed, to whom, by when : the module's highest-value read.

    The clock is derived and the decision is a transition, so neither is
    writable here. What this viewset adds is the two answers an operator
    actually needs at 3 a.m. : the proof of what was filed, and the list of
    what is late.
    """

    queryset = (
        IncidentNotification.objects.select_related(
            "incident", "authority", "template", "recipient_stakeholder",
            "recipient_supplier", "decided_by", "sent_by", "depends_on",
        )
        .prefetch_related("tags")
        .all()
    )
    filterset_class = IncidentNotificationFilter
    permission_feature = "notification"
    scope_parent_lookup = "incident__scopes"
    search_fields = [
        "reference", "obligation_reference", "recipient_name",
        "incident__reference", "incident__title",
    ]
    ordering_fields = [
        "reference", "regime", "recipient_kind", "workflow_state", "decision",
        "anchor_at", "due_at", "sent_at", "first_submitted_at", "created_at",
    ]
    custom_action_map = {
        **_IncidentViewSet.custom_action_map,
        "proof": "read",
        "overdue": "read",
    }

    def get_serializer_class(self):
        if self.action in ("list", "overdue"):
            return IncidentNotificationListSerializer
        return IncidentNotificationSerializer

    @action(detail=False, methods=["get"], url_path="overdue")
    def overdue(self, request, **kwargs):
        """Every duty past its deadline with no filing recorded.

        The *are we late* question in one call. Derived, never stored : the
        answer is right the instant the clock runs out and there is no overdue
        column to fall out of date (RG-INC-28). The definition is the
        filterset's own ``overdue`` method rather than a second copy of it
        here, so the endpoint and ``?overdue=true`` can never disagree, and no
        step code is written down on either path.

        Every other filter, the search and the ordering still apply, so *what
        is late under NIS2 in this scope* is one request.
        """
        queryset = self.filter_queryset(self.get_queryset())
        queryset = self.filterset_class(
            data={"overdue": "true"}, queryset=queryset, request=request
        ).qs
        if not request.query_params.get("ordering"):
            # The soonest breached is the one being asked about.
            queryset = queryset.order_by("due_at")

        page = self.paginate_queryset(queryset)
        if page is not None:
            return self.get_paginated_response(
                self.get_serializer(page, many=True).data
            )
        return Response(self.get_serializer(queryset, many=True).data)

    @action(detail=True, methods=["get"], url_path="proof")
    def proof(self, request, **kwargs):
        """Stream the obligation's proof of filing, scope- and permission-checked.

        ``proof_file_content`` appears in no list and no detail payload : the
        bytes are only ever served here.
        """
        obligation = self.get_object()
        data = obligation.get_proof_bytes()
        if not data:
            raise Http404()
        response = HttpResponse(data, content_type="application/octet-stream")
        response["Content-Disposition"] = _attachment_disposition(
            obligation.proof_filename_display or f"{obligation.reference}.bin"
        )
        return response


# --- Filings (append-only, with one narrow completion) -----------------------


class _FilingWriteSerializer(NotificationFilingSerializer):
    """Record a filing through the obligation, on both write paths.

    ``IncidentNotification.record_filing()`` is the module's single
    implementation of what recording a transmission means : the **first**
    filing on an obligation stamps ``sent_at``, ``sent_by``,
    ``first_submitted_at`` and ``late_by``, moves the obligation to its sent
    step, starts any dependent clock and narrates the act in the incident's
    chronology, all in one transaction. A plain insert would leave a filing on
    the record next to an obligation still counting itself overdue.

    It is done in ``create()`` rather than in the viewset's
    ``perform_create()`` because ``BatchCreateMixin`` calls ``save()`` itself :
    put here, the single POST and the batch POST discharge the obligation the
    same way.
    """

    def create(self, validated_data):
        data = dict(validated_data)
        obligation = data.pop("notification")
        user = data.pop("submitted_by", None)
        outcome = data.pop("outcome", None)
        acknowledged_at = data.pop("acknowledged_at", None)
        source = getattr(self, "initial_data", None) or {}

        filing = obligation.record_filing(
            user,
            submitted_at=data.get("submitted_at"),
            channel=data.get("channel") or None,
            subject=data.get("subject", ""),
            content=data.get("content"),
            recipient_name=data.get("recipient_name", ""),
            external_reference=data.get("external_reference", "") or "",
            is_correction=data.get("is_correction", False),
            supersedes=data.get("supersedes"),
            comment=(source.get("comment") or None),
        )
        if filing is None:
            # A first filing inserts through the transition's side effect; read
            # it back rather than assume, so the response always carries a row.
            filing = obligation.filings.order_by("-submitted_at", "-created_at").first()
        if filing is not None and (outcome is not None or acknowledged_at is not None):
            # The recipient answered in the same breath as the transmission was
            # recorded. Still the model's one completion path.
            filing.record_outcome(outcome=outcome, acknowledged_at=acknowledged_at)
        return filing


class NotificationFilingViewSet(
    BatchCreateMixin,
    ScopeFilterAPIMixin,
    HistoryAPIMixin,
    CreatedByMixin,
    _IncidentViewSet,
):
    """Create, list, retrieve, and exactly one completion ``PATCH``.

    No ``PUT`` and no ``DELETE`` route is generated at all : what an
    organisation told a regulator is never rewritten, and a correction is a new
    filing. The ``PATCH`` accepts only ``outcome``, ``acknowledged_at`` and
    ``external_reference``, and the serializer rejects every other key with a
    400 rather than ignoring it.

    Every action is gated on ``incidents.notification.*``, and recording a
    filing is deliberately an ``update`` on the obligation rather than a
    ``create`` : a filing is not an independent object, it is the discharge of
    a duty that already exists (RG-INC-26).
    """

    queryset = NotificationFiling.objects.select_related(
        "notification", "notification__incident", "submitted_by", "supersedes"
    ).all()
    serializer_class = NotificationFilingSerializer
    filterset_class = NotificationFilingFilter
    permission_feature = "notification"
    scope_parent_lookup = "notification__incident__scopes"
    created_by_field = "submitted_by"
    http_method_names = FILING_METHODS
    custom_action_map = {
        **_IncidentViewSet.custom_action_map,
        "create": "update",
        "batch_create": "update",
        "proof": "read",
    }
    search_fields = [
        "reference", "subject", "recipient_name", "external_reference",
        "notification__reference",
    ]
    ordering_fields = ["reference", "submitted_at", "outcome", "created_at"]

    def get_serializer_class(self):
        if self.action in ("create", "batch_create"):
            return _FilingWriteSerializer
        return NotificationFilingSerializer

    def _get_batch_create_kwargs(self, request):
        # See `IncidentTimelineEntryViewSet._get_batch_create_kwargs`.
        return {self.created_by_field: request.user}

    def perform_update(self, serializer):
        """Complete the filing through the model's one completion path.

        The serializer has already frozen everything else and refused any other
        key, so what arrives here is at most the recipient's answer. Writing it
        through ``record_outcome()`` keeps the web form, this route and the MCP
        tool on one implementation of what may be written after a filing.
        """
        filing = serializer.instance
        data = serializer.validated_data
        try:
            filing.record_outcome(
                outcome=data.get("outcome"),
                acknowledged_at=data.get("acknowledged_at"),
                external_reference=data.get("external_reference"),
            )
        except DjangoValidationError as exc:
            raise _validation_error(exc) from exc
        except LifecycleProtectedError as exc:
            raise Conflict(
                _(
                    "This filing has already been completed. Record a further "
                    "answer as a new filing."
                )
            ) from exc

    @action(detail=True, methods=["get"], url_path="proof")
    def proof(self, request, **kwargs):
        """Stream a filing's proof document, scope- and permission-checked."""
        filing = self.get_object()
        data = filing.get_proof_bytes()
        if not data:
            raise Http404()
        response = HttpResponse(data, content_type="application/octet-stream")
        response["Content-Disposition"] = _attachment_disposition(
            filing.proof_filename or f"{filing.reference}.bin"
        )
        return response


# --- Personal data breach (GDPR Art. 33 / 34) --------------------------------


class PersonalDataBreachViewSet(
    BatchCreateMixin,
    ScopeFilterAPIMixin,
    LifecycleAPIMixin,
    HistoryAPIMixin,
    CreatedByMixin,
    _IncidentViewSet,
):
    """The GDPR qualification of an incident : one row, reached by transition.

    Gated by ``incidents.notification.*`` : qualifying a breach is deciding
    what must be notified, and the module has no seventh feature.
    """

    queryset = (
        PersonalDataBreach.objects.select_related(
            "incident", "lead_authority", "controller_supplier", "qualified_by"
        )
        .prefetch_related("tags")
        .all()
    )
    filterset_class = PersonalDataBreachFilter
    permission_feature = "notification"
    scope_parent_lookup = "incident__scopes"
    search_fields = [
        "reference", "nature", "likely_consequences", "register_entry_reference",
        "incident__reference", "incident__title",
    ]
    ordering_fields = [
        "reference", "controller_role", "workflow_state",
        "approximate_data_subjects", "approximate_records", "qualified_at",
        "created_at",
    ]

    def get_serializer_class(self):
        if self.action == "list":
            return PersonalDataBreachListSerializer
        return PersonalDataBreachSerializer
