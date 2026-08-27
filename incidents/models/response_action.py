# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""In-incident operational steps : the A.5.26 response, action by action.

Isolate the host, revoke the token, block the sender, restore from backup,
pull the logs before they rotate. One row per step taken **during** an
incident, with an owner, a deadline and a completion state.

The entity that records the corrective work done **because of** an incident is
``compliance.ComplianceActionPlan``, linked from the post-incident review
(RG-INC-35). The split is deliberate and is the single most important thing to
understand here : an audit-gap remediation lives for weeks and deserves the
eight-step approval lifecycle; a containment step lives for twenty minutes and
would be actively harmed by one.
"""

import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy
from simple_history.models import HistoricalRecords

from compliance.constants import EffectivenessVerdict
from context.models.base import ReferenceGeneratorMixin
from incidents.constants import (
    REFERENCE_PREFIXES,
    ResponseActionStatus,
    ResponseActionType,
)

# The statuses that end a response action's working life. RG-INC-37 forbids a
# state literal outside ``incidents/constants.py``, and that prohibition covers
# this plain enum as much as it covers the lifecycle step codes : the overdue
# sweep, the kanban buckets and every KPI read this set rather than spelling
# the two values again.
TERMINAL_STATUSES = frozenset(
    {ResponseActionStatus.DONE, ResponseActionStatus.CANCELLED}
)


class IncidentResponseAction(ReferenceGeneratorMixin):
    """One operational step taken during an incident (A.5.26 / ISO 27035).

    Deliberately **not** a ``BaseModel`` and deliberately carrying a plain
    ``status`` column instead of a registered lifecycle. The doctrine in
    ``CLAUDE.md`` governs domain elements : things a user navigates to, reports
    on, links from elsewhere and archives. This is a child row worked entirely
    inside its parent incident's detail page, it has no list page, no detail
    page and no scope of its own, and its governance is the incident's
    governance. A responder ticking four containment steps in ninety seconds
    must not pay a permission check, a ``LifecycleEvent`` row and a comment
    modal four times, and any approval inserted into that path manufactures
    delay in the exact window where delay is the harm.

    The price is stated rather than hidden : ``reportable()``, ``linkable()``
    and ``deletable_states()`` answer nothing about this model, a status change
    leaves a ``HistoricalRecords`` row and no ``LifecycleEvent``, and the row is
    deletable at any status (gated by permission alone). See
    ``docs/modules/m6-incidents/incident-response-action.md``.

    The row is **mutable by design** : moving from planned to done while the
    incident is live is its whole purpose. No append-only claim is made for it,
    unlike its neighbours ``IncidentTimelineEntry`` and ``EvidenceCustodyEvent``.
    """

    REFERENCE_PREFIX = REFERENCE_PREFIXES["IncidentResponseAction"]

    # Never independently scoped (RG-INC-38) : the parent incident's scopes are
    # the only tenancy answer, so re-scoping the incident can never leave its
    # response actions behind.
    scope_parent_lookup = "incident__scopes"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    incident = models.ForeignKey(
        "incidents.Incident",
        on_delete=models.CASCADE,
        related_name="response_actions",
        verbose_name=pgettext_lazy("incident", "Incident"),
    )
    action_type = models.CharField(
        _("Action type"),
        max_length=30,
        choices=ResponseActionType.choices,
        help_text=_("Which ISO 27035 response step this action belongs to."),
    )
    title = models.CharField(
        _("Title"),
        max_length=255,
        help_text=_("What is being done, in the imperative."),
    )
    description = models.TextField(
        _("Description"),
        blank=True,
        default="",
        help_text=_("The command to run, the runbook section, the person to call."),
    )
    status = models.CharField(
        _("Status"),
        max_length=20,
        choices=ResponseActionStatus.choices,
        default=ResponseActionStatus.PLANNED,
        help_text=_(
            "Operational progress. A plain status column, not a lifecycle "
            "state : this row follows its parent incident's governance."
        ),
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="incident_response_actions",
        verbose_name=_("Owner"),
        help_text=_("Who is accountable for the step being done."),
    )
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="performed_incident_response_actions",
        verbose_name=_("Performed by"),
        help_text=_("Who actually executed it, when that differs from the owner."),
    )
    due_at = models.DateTimeField(
        _("Due at"),
        null=True,
        blank=True,
        db_index=True,
        help_text=_("Drives the daily escalation sweep and the overdue styling."),
    )
    started_at = models.DateTimeField(_("Started at"), null=True, blank=True)
    completed_at = models.DateTimeField(
        _("Completed at"),
        null=True,
        blank=True,
        help_text=_(
            "Execution end. With the start time, the raw material of the "
            "mean-time-to-contain indicator."
        ),
    )
    outcome = models.TextField(
        _("Outcome"),
        blank=True,
        default="",
        help_text=_(
            "What the action actually achieved. A containment step marked done "
            "with no stated outcome is not evidence of containment."
        ),
    )
    effectiveness = models.CharField(
        _("Effectiveness"),
        max_length=32,
        choices=EffectivenessVerdict.choices,
        blank=True,
        default="",
        help_text=_(
            "Whether the step worked, assessed during the post-incident review "
            "(A.5.27). Blank until it has been assessed."
        ),
    )
    version = models.PositiveIntegerField(_("Version"), default=1)
    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated at"), auto_now=True)

    # The only per-change record this entity has, since it emits no
    # ``LifecycleEvent``. It is what an auditor is pointed at for who marked a
    # step done, when, and with what outcome text at that moment.
    history = HistoricalRecords()

    class Meta:
        verbose_name = _("Response action")
        verbose_name_plural = _("Response actions")
        # Deadline order with a stable tie-break, so an incident's actions read
        # the way a responder works them.
        ordering = ["incident", "due_at", "reference"]
        constraints = [
            models.CheckConstraint(
                condition=(
                    ~models.Q(status=ResponseActionStatus.DONE)
                    | ~models.Q(outcome="")
                ),
                name="response_action_done_has_outcome",
            ),
        ]

    def __str__(self):
        return f"{self.reference} : {self.title}"

    # --- Read-only display helpers (API / assistant output) ----------------

    @property
    def incident_reference(self):
        """Reference of the parent incident (for read-only API output)."""
        return self.incident.reference if self.incident_id else ""

    @property
    def owner_name(self):
        """Display name of the accountable owner (read-only output)."""
        return self.owner.display_name if self.owner_id else ""

    @property
    def performed_by_name(self):
        """Display name of whoever executed the step (read-only output)."""
        return self.performed_by.display_name if self.performed_by_id else ""

    @property
    def is_terminal(self):
        """Whether the step has stopped moving (done or abandoned)."""
        return self.status in TERMINAL_STATUSES

    @property
    def is_overdue(self):
        """Past its deadline and still expected to be worked.

        Derived, never stored : an overdue action is a late one, not one in a
        different state, and freezing lateness into a column would make it
        drift the moment the deadline is corrected.
        """
        if self.due_at is None or self.is_terminal:
            return False
        return self.due_at < timezone.now()

    @property
    def execution_duration(self):
        """``completed_at - started_at``, or None while either stamp is missing."""
        if self.started_at is None or self.completed_at is None:
            return None
        return self.completed_at - self.started_at

    # --- Validation --------------------------------------------------------

    def clean(self):
        """Refuse a completion the incident file could not be read from.

        The outcome rule is also a DB ``CheckConstraint``; it is restated here
        so the form, the serializer and the MCP tool report it as a field error
        instead of surfacing an integrity error from the database.
        """
        super().clean()
        errors = {}
        if self.status == ResponseActionStatus.DONE:
            if not (self.outcome or "").strip():
                errors["outcome"] = _(
                    "A completed action must state what it achieved."
                )
            if self.completed_at is None:
                errors["completed_at"] = _(
                    "A completed action must record when it was completed."
                )
        if (
            self.started_at
            and self.completed_at
            and self.completed_at < self.started_at
        ):
            errors["completed_at"] = _(
                "An action cannot be completed before it was started."
            )
        if errors:
            raise ValidationError(errors)

    # --- Completion --------------------------------------------------------

    @transaction.atomic
    def mark_done(self, user=None, *, outcome, completed_at=None):
        """Complete the step in one act : outcome, stamp and executor together.

        Kept on the model rather than repeated in the inline form, the
        serializer and the MCP tool, because the three fields are what make a
        completion evidential and splitting them across surfaces is how one of
        them ends up optional. ``full_clean()`` runs first, so the same field
        errors are raised everywhere rather than an ``IntegrityError`` on one
        surface and a clean message on another.
        """
        self.status = ResponseActionStatus.DONE
        self.outcome = outcome
        self.completed_at = completed_at or timezone.now()
        if self.performed_by_id is None and user is not None:
            self.performed_by = user
        self.full_clean(exclude=["reference"])
        self.save()
        return self
