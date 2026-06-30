"""Standardised element lifecycles (rebuilt from scratch).

A :class:`Lifecycle` is a declarative *schema* for one item type: an ordered set
of :class:`Step` objects (the étapes) plus the :class:`Transition` objects
between them. It is the single, standard way every domain element moves through
its life, and it supersedes :mod:`core.workflow` (entities are migrated onto it
incrementally; the two engines coexist during the transition).

Standardisation contract (the rules this module enforces and exposes):

- **Mandatory bookend steps.** Every lifecycle MUST contain exactly one
  ``DRAFT`` step (the single entry point) and at least one ``ARCHIVED`` step (the
  exit). What sits between is entity-specific.
- **Linear or cyclic.** The transition graph is free-form: a lifecycle may be a
  straight line, a cycle, or a line with an exit step. Returning to an earlier
  step (rework, reactivation) and leaving the archived step (restore) are both
  allowed - nothing here forbids cycles.
- **Free or constrained transitions.** A transition declares its ``source``
  step, or :data:`ANY` to mean "from any state" (e.g. *any -> Archived*). So
  some moves are global while others are only legal from a specific step.
- **Form per transition.** A transition may point at a Django ``Form`` class
  (:attr:`Transition.form_class`); performing the transition then requires the
  form, and its cleaned data is stored on the recorded event.
- **Role / people restriction.** A transition may be restricted to ISO 27001
  roles (by :class:`context.constants.RoleType`) and/or to named users resolved
  from the instance (e.g. its owner). Unrestricted transitions are open to
  anyone with access; superusers always pass.
- **History.** Every performed transition is recorded as a
  :class:`core.models.LifecycleEvent` (actor, from, to, comment, form data,
  timestamp). See :func:`core.lifecycle_service.perform_transition`.

This module is intentionally free of model/database imports at load time (they
are done lazily inside functions) so the schema layer stays unit-testable and
importable from any layer (views, DRF, MCP, reports).
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from enum import Enum

from django.utils.module_loading import import_string
from django.utils.translation import gettext_lazy as _lazy

# --- Step kinds -------------------------------------------------------------

#: Wildcard transition source: the transition is legal "from any state".
ANY = "*"


class StepKind(str, Enum):
    """The role a step plays in the lifecycle.

    ``DRAFT`` and ``ARCHIVED`` are mandatory bookends; ``INTERMEDIATE`` is every
    entity-specific step in between.
    """

    DRAFT = "draft"
    INTERMEDIATE = "intermediate"
    ARCHIVED = "archived"


# --- Declarative structures -------------------------------------------------


@dataclass(frozen=True)
class Step:
    """A single step (étape) in a lifecycle, carrying its governance metadata.

    ``label`` and ``tone`` are excluded from equality so two steps are equal iff
    they share the same code, kind and governance flags. Governance flags drive
    the cross-cutting rules (report / KPI inclusion, linking, deletion) so those
    never hardcode a status value.
    """

    code: str
    label: object = field(compare=False)
    kind: StepKind = StepKind.INTERMEDIATE
    counts_in_reports: bool = False
    linkable: bool = False
    deletable: bool = False
    tone: str = field(default="neutral", compare=False)

    @property
    def is_draft(self) -> bool:
        return self.kind == StepKind.DRAFT

    @property
    def is_archived(self) -> bool:
        return self.kind == StepKind.ARCHIVED


def draft_step(
    code: str = "draft",
    label: object = None,
    *,
    deletable: bool = True,
    tone: str = "neutral",
) -> Step:
    """The canonical mandatory Draft step (the single entry point)."""
    from django.utils.translation import gettext_lazy as _

    return Step(
        code=code,
        label=label if label is not None else _("Draft"),
        kind=StepKind.DRAFT,
        deletable=deletable,
        tone=tone,
    )


def archived_step(
    code: str = "archived",
    label: object = None,
    *,
    tone: str = "muted",
) -> Step:
    """The canonical mandatory Archived step (the exit)."""
    from django.utils.translation import gettext_lazy as _

    return Step(
        code=code,
        label=label if label is not None else _("Archived"),
        kind=StepKind.ARCHIVED,
        counts_in_reports=False,
        linkable=False,
        tone=tone,
    )


@dataclass(frozen=True)
class Transition:
    """A permitted move to a ``target`` step.

    ``source`` is a specific step code, or :data:`ANY` for a "from any state"
    transition. ``form_class`` is an optional Django ``Form`` class (or its
    dotted import path) collected when the transition is performed; its cleaned
    data is stored on the recorded event. ``allowed_roles`` restricts the
    transition to users assigned to an ISO 27001 role of one of those
    :class:`~context.constants.RoleType` values (scoped to the instance);
    ``allowed_users`` is an optional callable ``(instance) -> iterable[user]``
    for dynamic person restriction (e.g. the owner). When both restriction
    fields are empty the transition is open.
    """

    target: str
    source: str = ANY
    label: object = field(default="", compare=False)
    form_class: object = field(default=None, compare=False)
    allowed_roles: tuple = ()
    allowed_users: Callable | None = field(default=None, compare=False)
    requires_comment: bool = False
    # Optional Django-permission suffix (e.g. "approve") required to perform the
    # transition, built against the instance's ``workflow_perm_namespace``. Empty
    # for the common case (gating is by role / open); set by publishing surfaces
    # that keep a per-transition permission (e.g. the trust center).
    permission_action: str = field(default="", compare=False)

    @property
    def from_any(self) -> bool:
        return self.source == ANY

    @property
    def code(self) -> str:
        return f"{self.source}->{self.target}"

    @property
    def is_restricted(self) -> bool:
        return bool(self.allowed_roles) or self.allowed_users is not None

    def get_form_class(self):
        """Resolve ``form_class`` (a class or a dotted path) or ``None``."""
        if self.form_class is None:
            return None
        if isinstance(self.form_class, str):
            return import_string(self.form_class)
        return self.form_class


# --- Errors -----------------------------------------------------------------


class LifecycleError(ValueError):
    """Base error for an invalid lifecycle schema or an invalid transition."""


class UnknownStepError(LifecycleError):
    """A step code does not belong to the lifecycle."""


class IllegalTransitionError(LifecycleError):
    """No transition exists between the two steps."""


class TransitionNotAllowedError(LifecycleError):
    """The user is not permitted to perform the transition."""


class CommentRequiredError(LifecycleError):
    """The transition requires a comment but none was provided."""


class StepProtectedError(Exception):
    """Raised when deleting an element whose current step is not deletable."""


# --- Lifecycle --------------------------------------------------------------


class Lifecycle:
    """A schema: ordered steps plus the transitions between them.

    Invariants (checked at construction):

    - unique step codes;
    - exactly one ``DRAFT`` step (the entry / initial step);
    - at least one ``ARCHIVED`` step (the exit);
    - every transition target is a declared step;
    - every transition source is a declared step or :data:`ANY`.

    The graph is otherwise unconstrained: cycles and transitions leaving the
    archived step (restore) are allowed.
    """

    def __init__(
        self,
        name: str,
        steps: Iterable[Step],
        transitions: Iterable[Transition],
        *,
        layout: str = "line",
    ) -> None:
        self.name = name
        self.steps = tuple(steps)
        self.transitions = tuple(transitions)
        # UI hint: "line" (a connected stepper) or "cycle" (the intermediate
        # steps drawn as an ordered ring with arrows). Bookends (Draft / Archived)
        # are rendered apart in both layouts.
        self.layout = layout
        self._by_code = {s.code: s for s in self.steps}
        self._validate()

    def _validate(self) -> None:
        if not self.steps:
            raise LifecycleError(f"Lifecycle '{self.name}' has no steps.")
        codes = [s.code for s in self.steps]
        if len(codes) != len(set(codes)):
            raise LifecycleError(f"Lifecycle '{self.name}' has duplicate step codes.")
        drafts = [s for s in self.steps if s.kind == StepKind.DRAFT]
        if len(drafts) != 1:
            raise LifecycleError(
                f"Lifecycle '{self.name}' must have exactly one Draft step "
                f"(found {len(drafts)})."
            )
        if not any(s.kind == StepKind.ARCHIVED for s in self.steps):
            raise LifecycleError(
                f"Lifecycle '{self.name}' must have at least one Archived step."
            )
        for t in self.transitions:
            if t.source != ANY and t.source not in self._by_code:
                raise LifecycleError(
                    f"Transition source '{t.source}' is not a step of '{self.name}'."
                )
            if t.target not in self._by_code:
                raise LifecycleError(
                    f"Transition target '{t.target}' is not a step of '{self.name}'."
                )

    # -- lookups -------------------------------------------------------------

    @property
    def initial_step(self) -> Step:
        return next(s for s in self.steps if s.kind == StepKind.DRAFT)

    @property
    def archived_steps(self) -> tuple:
        return tuple(s for s in self.steps if s.kind == StepKind.ARCHIVED)

    def step(self, code: str) -> Step:
        try:
            return self._by_code[code]
        except KeyError:
            raise UnknownStepError(
                f"'{code}' is not a step of lifecycle '{self.name}'."
            ) from None

    def has_step(self, code: str) -> bool:
        return code in self._by_code

    def transitions_from(self, code: str) -> tuple:
        """Every transition legal from ``code`` (specific source + wildcards).

        Self-targeting moves (``target == code``) are excluded so a "from any
        state" transition never offers a no-op back to the current step.
        """
        self.step(code)
        return tuple(
            t
            for t in self.transitions
            if (t.source == code or t.source == ANY) and t.target != code
        )

    def find_transition(self, source: str, target: str) -> Transition | None:
        """The transition ``source -> target``, honouring wildcard sources."""
        explicit = None
        wildcard = None
        for t in self.transitions:
            if t.target != target:
                continue
            if t.source == source:
                explicit = t
            elif t.source == ANY:
                wildcard = t
        return explicit or wildcard

    def _codes_where(self, attr: str) -> frozenset:
        return frozenset(s.code for s in self.steps if getattr(s, attr))

    @property
    def reportable_step_codes(self) -> frozenset:
        return self._codes_where("counts_in_reports")

    @property
    def linkable_step_codes(self) -> frozenset:
        return self._codes_where("linkable")

    @property
    def deletable_step_codes(self) -> frozenset:
        return self._codes_where("deletable")


# --- Registry ---------------------------------------------------------------

LIFECYCLE_REGISTRY: dict[str, Lifecycle] = {}


def register_lifecycle(lifecycle: Lifecycle) -> Lifecycle:
    """Register a lifecycle by name (idempotent on identical re-registration)."""
    existing = LIFECYCLE_REGISTRY.get(lifecycle.name)
    if existing is not None and existing is not lifecycle:
        raise LifecycleError(
            f"A different lifecycle named '{lifecycle.name}' is already registered."
        )
    LIFECYCLE_REGISTRY[lifecycle.name] = lifecycle
    return lifecycle


def get_lifecycle(name: str) -> Lifecycle:
    try:
        return LIFECYCLE_REGISTRY[name]
    except KeyError:
        raise LifecycleError(f"No lifecycle named '{name}' is registered.") from None


# --- Restriction evaluation -------------------------------------------------


def _user_in_roles(user, role_types: tuple, instance) -> bool:
    """Whether ``user`` is assigned to an ISO 27001 role of one of ``role_types``.

    When the instance is scoped, the role must share at least one scope with it
    (a role only grants its authority within its own scopes); unscoped instances
    match any such role.
    """
    from context.models.role import Role

    qs = Role.objects.filter(type__in=list(role_types), assigned_users=user)
    instance_scope_ids = None
    if hasattr(instance, "scopes"):
        try:
            instance_scope_ids = set(instance.scopes.values_list("id", flat=True))
        except Exception:
            instance_scope_ids = None
    if instance_scope_ids:
        qs = qs.filter(scopes__id__in=instance_scope_ids)
    return qs.exists()


def user_can_perform(transition: Transition, instance, user) -> bool:
    """Whether ``user`` may perform ``transition`` on ``instance``.

    Open transitions (no role/user restriction) are allowed for any user;
    superusers always pass. A restricted transition is allowed when the user
    matches an allowed ISO role (scoped) or is among the resolved allowed users.
    """
    if user is None:
        return False
    if getattr(user, "is_superuser", False):
        return True
    # Optional per-transition Django permission (publishing surfaces): the user
    # must hold ``<workflow_perm_namespace>.<permission_action>``.
    action = getattr(transition, "permission_action", "")
    if action:
        namespace = getattr(instance, "workflow_perm_namespace", None)
        if namespace and not user.has_perm(f"{namespace}.{action}"):
            return False
    if not transition.is_restricted:
        return True
    if transition.allowed_roles and _user_in_roles(user, transition.allowed_roles, instance):
        return True
    if transition.allowed_users is not None:
        try:
            candidates = transition.allowed_users(instance) or ()
        except Exception:
            candidates = ()
        user_pk = getattr(user, "pk", None)
        if any(getattr(u, "pk", u) == user_pk for u in candidates):
            return True
    return False


def available_transitions(lifecycle: Lifecycle, current_code: str, *, instance=None, user=None) -> tuple:
    """Transitions legal from ``current_code``, filtered by ``user`` if given."""
    candidates = lifecycle.transitions_from(current_code)
    if user is None:
        return candidates
    return tuple(t for t in candidates if user_can_perform(t, instance, user))


def validate_transition(
    lifecycle: Lifecycle,
    current_code: str,
    target_code: str,
    *,
    instance=None,
    user=None,
    comment: str | None = None,
    enforce_permission: bool = True,
) -> Transition:
    """Validate ``current_code -> target_code`` and return the matched transition.

    Raises :class:`UnknownStepError`, :class:`IllegalTransitionError`,
    :class:`TransitionNotAllowedError` or :class:`CommentRequiredError`.
    """
    if not lifecycle.has_step(current_code):
        raise UnknownStepError(f"'{current_code}' is not a step of '{lifecycle.name}'.")
    if not lifecycle.has_step(target_code):
        raise UnknownStepError(f"'{target_code}' is not a step of '{lifecycle.name}'.")
    transition = lifecycle.find_transition(current_code, target_code)
    if transition is None or target_code == current_code:
        raise IllegalTransitionError(
            f"Cannot move from '{current_code}' to '{target_code}' in '{lifecycle.name}'."
        )
    if enforce_permission and user is not None and not user_can_perform(transition, instance, user):
        raise TransitionNotAllowedError(
            f"User may not perform transition '{transition.code}' in '{lifecycle.name}'."
        )
    if transition.requires_comment and not (comment and comment.strip()):
        raise CommentRequiredError(
            f"A comment is required for the transition '{transition.code}'."
        )
    return transition


# --- Legacy port helper -----------------------------------------------------


def lifecycle_from_state_flags(name, state_flags_items, transitions, *, layout="line"):
    """Build a :class:`Lifecycle` from legacy ``(code, label, flags)`` tuples.

    The single workflow-to-lifecycle porting helper: each app feeds it the same
    per-state governance data its old ``core.workflow`` machine used, so the
    standardised lifecycle keeps the identical step codes, labels and governance
    flags (no ``workflow_state`` data migration is needed).

    ``state_flags_items`` is an iterable of
    ``(code, label, counts_in_reports, linkable, deletable, is_initial,
    is_terminal, tone)``. The one ``is_initial`` state becomes the mandatory
    ``DRAFT`` entry step; every ``is_terminal`` state becomes an ``ARCHIVED``
    exit step; the rest are ``INTERMEDIATE``. ``transitions`` is an iterable of
    ``(source, target, label)``, ``(source, target, label, requires_comment)`` or
    ``(source, target, label, requires_comment, permission_action)``.
    """
    steps = []
    for code, label, counts, can_link, can_delete, is_initial, is_terminal, tone in state_flags_items:
        if is_initial:
            kind = StepKind.DRAFT
        elif is_terminal:
            kind = StepKind.ARCHIVED
        else:
            kind = StepKind.INTERMEDIATE
        steps.append(
            Step(
                code,
                label,
                kind=kind,
                counts_in_reports=counts,
                linkable=can_link,
                deletable=can_delete,
                tone=tone,
            )
        )
    built = []
    for t in transitions:
        source, target, label = t[0], t[1], t[2]
        requires_comment = t[3] if len(t) > 3 else False
        permission_action = t[4] if len(t) > 4 else ""
        built.append(
            Transition(
                target=target,
                source=source,
                label=label,
                requires_comment=requires_comment,
                permission_action=permission_action,
            )
        )
    return Lifecycle(name, steps, built, layout=layout)


# --- Default lifecycle ------------------------------------------------------
#
# The 4-step lifecycle every model runs unless it declares a specific
# ``LIFECYCLE_NAME``. It mirrors the historical default workflow: only
# "validated" counts in reports and is linkable, only "draft" can be deleted,
# "archived" is the exit.

DEFAULT_LIFECYCLE_NAME = "default"

DEFAULT_LIFECYCLE = register_lifecycle(
    Lifecycle(
        DEFAULT_LIFECYCLE_NAME,
        steps=[
            draft_step(),
            Step("pending", _lazy("Pending validation"), kind=StepKind.INTERMEDIATE, tone="info"),
            Step(
                "validated",
                _lazy("Validated"),
                kind=StepKind.INTERMEDIATE,
                counts_in_reports=True,
                linkable=True,
                tone="success",
            ),
            archived_step(),
        ],
        transitions=[
            Transition("pending", source="draft", label=_lazy("Submit"), permission_action="update"),
            Transition("draft", source="pending", label=_lazy("Send back to draft"), permission_action="update"),
            Transition("validated", source="pending", label=_lazy("Validate"), permission_action="approve"),
            Transition("archived", source="validated", label=_lazy("Archive"), permission_action="approve"),
        ],
        layout="line",
    )
)


def lifecycle_name_for(model_or_label) -> str:
    """Resolve the lifecycle name assigned to a model.

    Precedence: the model's declared ``LIFECYCLE_NAME`` class attribute, then the
    default lifecycle. Mirrors the historical ``core.workflow.workflow_name_for``
    so callers never branch on assignment logic.
    """
    name = getattr(model_or_label, "LIFECYCLE_NAME", None)
    if name and name in LIFECYCLE_REGISTRY:
        return name
    return DEFAULT_LIFECYCLE_NAME


def resolve_lifecycle(model_or_label) -> Lifecycle:
    """Return the :class:`Lifecycle` a model runs (its own or the default)."""
    if isinstance(model_or_label, Lifecycle):
        return model_or_label
    return get_lifecycle(lifecycle_name_for(model_or_label))


# Backwards-compatible alias: the single deletion guard error class.
LifecycleProtectedError = StepProtectedError


# --- Cross-cutting governance helpers ---------------------------------------
#
# Reports / KPIs / calendar inclusion, link pickers and deletion all read these
# instead of hardcoding a status value, so a lifecycle's ``counts_in_reports`` /
# ``linkable`` / ``deletable`` step flags are the single source of truth.


def reportable_states(model_or_label) -> frozenset:
    """Step codes whose elements count in reports / KPIs / calendar."""
    return resolve_lifecycle(model_or_label).reportable_step_codes


def linkable_states(model_or_label) -> frozenset:
    """Step codes whose elements may currently be linked."""
    return resolve_lifecycle(model_or_label).linkable_step_codes


def deletable_states(model_or_label) -> frozenset:
    """Step codes whose elements may currently be deleted."""
    return resolve_lifecycle(model_or_label).deletable_step_codes


def _has_lifecycle_field(model) -> bool:
    """Whether a model carries the ``workflow_state`` lifecycle field.

    Plain child models (e.g. stakeholder expectations) have no lifecycle and are
    not governed: the queryset helpers below leave them untouched.
    """
    try:
        model._meta.get_field("workflow_state")
    except Exception:
        return False
    return True


def reportable(queryset):
    """Restrict a queryset to elements whose step counts in reports / KPIs / calendar."""
    if not _has_lifecycle_field(queryset.model):
        return queryset
    return queryset.filter(workflow_state__in=reportable_states(queryset.model))


def linkable(queryset):
    """Restrict a queryset to elements that may currently be linked."""
    if not _has_lifecycle_field(queryset.model):
        return queryset
    return queryset.filter(workflow_state__in=linkable_states(queryset.model))


def linkable_or_linked(queryset, linked_qs=None):
    """Linkable elements, plus those already linked to the edited object.

    Link pickers use this so a new link can only target a linkable element,
    while existing links survive a target leaving its linkable state (archiving
    an element never silently drops the links it already has).
    """
    from django.db.models import Q

    if not _has_lifecycle_field(queryset.model):
        return queryset
    allowed = Q(workflow_state__in=linkable_states(queryset.model))
    if linked_qs is not None:
        allowed |= Q(pk__in=linked_qs.values_list("pk", flat=True))
    return queryset.filter(allowed)
