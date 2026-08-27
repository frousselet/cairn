# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""The A.5.24 incident management procedure of record.

Every :class:`~incidents.models.incident.Incident` points at the plan it was
handled under through a ``PROTECT`` foreign key, so a two-year-old incident file
stays readable at audit time : *this is the procedure that was in force when we
handled it*. The foreign key points at the plan **row**, not at a frozen copy of
its text : the evolution is recoverable through ``HistoricalRecords``, and the
working convention is that a material change to the procedure is a new plan row
put into force with its own ``effective_from`` rather than an in-place rewrite.
"""

from datetime import datetime, timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

from context.models.base import ScopedModel
from incidents.constants import REFERENCE_PREFIXES, NotificationRegime

# A.5.24 asks for the plan to be tested. Twelve months without an exercise is
# the point at which the UI raises a warning badge : an untested plan is a
# nonconformity waiting to be written up.
EXERCISE_STALE_AFTER_DAYS = 365

# The two intermediate step codes of the **core** ``default`` lifecycle
# (``core/lifecycle.py`` ``DEFAULT_LIFECYCLE``), used only by
# :meth:`IncidentResponsePlan.put_into_force`. RG-INC-37 forbids state literals
# for the module's own lifecycles, whose codes live in ``incidents/constants.py``;
# these belong to core, which exports no constant for them. ``transition_to()``
# raises ``UnknownStepError`` should core ever rename one, so the coupling fails
# loudly instead of silently skipping a step.
_DEFAULT_PENDING_STEP = "pending"
_DEFAULT_VALIDATED_STEP = "validated"


class IncidentResponsePlan(ScopedModel):
    """The documented incident management procedure (ISO/IEC 27001:2022 A.5.24).

    Runs the core ``default`` 4-state lifecycle : a governance document does not
    need operational stages, it needs a controlled approval, and ``validated``
    means *in force*. That lifecycle needs no bookend correction, unlike the six
    lifecycles this module registers : its archive edge already carries
    ``permission_action="approve"`` and it declares no restore transition at
    all, so there is no path from ``validated`` back into a deletable step.
    """

    REFERENCE_PREFIX = REFERENCE_PREFIXES["IncidentResponsePlan"]

    name = models.CharField(_("Name"), max_length=255)
    purpose = models.TextField(_("Purpose"), blank=True, default="")
    procedure = models.TextField(_("Procedure"), blank=True, default="")
    classification_scale = models.TextField(
        _("Classification scale"),
        blank=True,
        default="",
        help_text=_(
            "What low / medium / high / critical mean in this organisation's "
            "terms : the A.5.25 decision criterion that gives incident severity "
            "its meaning."
        ),
    )
    escalation_matrix = models.TextField(
        _("Escalation matrix"),
        blank=True,
        default="",
        help_text=_("Who is escalated to, at which severity, within which delay."),
    )
    reporting_channels = models.TextField(
        _("Reporting channels"),
        blank=True,
        default="",
        help_text=_(
            "How events and weaknesses are reported, including the anonymous "
            "channel required by A.6.8."
        ),
    )
    evidence_procedure = models.TextField(
        _("Evidence procedure"),
        blank=True,
        default="",
        help_text=_(
            "Identification, collection, acquisition and preservation of "
            "evidence (A.5.28)."
        ),
    )
    lessons_learned_procedure = models.TextField(
        _("Lessons learned procedure"),
        blank=True,
        default="",
        help_text=_(
            "How knowledge gained from incidents is used to strengthen "
            "controls (A.5.27)."
        ),
    )
    # A JSONField rather than a postgres ArrayField : the test settings
    # (``core.settings_test``) run on SQLite in memory, where an ArrayField
    # would not exist at all.
    applicable_regimes = models.JSONField(
        _("Applicable regimes"),
        default=list,
        blank=True,
        help_text=_(
            "Regulatory regimes this plan is built to satisfy. Triage "
            "instantiates one notification obligation per regime."
        ),
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="owned_incident_response_plans",
        verbose_name=_("Owner"),
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_incident_response_plans",
        verbose_name=_("Approved by"),
    )
    approved_at = models.DateField(_("Approved at"), null=True, blank=True)
    effective_from = models.DateField(_("Effective from"), null=True, blank=True)
    review_date = models.DateField(
        _("Review date"), null=True, blank=True, db_index=True
    )
    # Maintained exclusively by :meth:`record_exercise`, called from the
    # incident closure transition. No form, serializer or MCP tool offers the
    # edit : a hand-typed plan-testing date is worthless as evidence.
    last_exercise_date = models.DateField(
        _("Last exercise date"), null=True, blank=True
    )
    responsible_roles = models.ManyToManyField(
        "context.Role",
        blank=True,
        related_name="incident_response_plans",
        verbose_name=_("Responsible roles"),
    )
    linked_requirements = models.ManyToManyField(
        "compliance.Requirement",
        blank=True,
        related_name="linked_incident_response_plans",
        verbose_name=_("Linked requirements"),
    )

    history = HistoricalRecords()

    class Meta(ScopedModel.Meta):
        ordering = ["-effective_from", "name"]
        verbose_name = _("Incident response plan")
        verbose_name_plural = _("Incident response plans")

    def __str__(self):
        return f"{self.reference} : {self.name}"

    @property
    def workflow_perm_namespace(self):
        """Gate this entity on the ``incidents.response_plan`` feature.

        The derived ``incidents.incidentresponseplan`` matches no feature in
        ``PERMISSION_REGISTRY``, so every lifecycle permission check would
        silently evaluate against a codename nobody holds.
        """
        return "incidents.response_plan"

    # --- Read-only display helpers ----------------------------------------

    @property
    def owner_name(self):
        """Display name of the accountable owner (read-only API / assistant output)."""
        return self.owner.display_name if self.owner_id else ""

    @property
    def approved_by_name(self):
        """Display name of the management approver (read-only API / assistant output)."""
        return self.approved_by.display_name if self.approved_by_id else ""

    @property
    def applicable_regime_labels(self):
        """Human labels of the configured regimes, in declaration order."""
        labels = dict(NotificationRegime.choices)
        return [str(labels.get(regime, regime)) for regime in self.applicable_regimes or []]

    @property
    def is_in_force(self):
        """Whether the plan is currently the procedure of record.

        Read off the lifecycle step's governance metadata rather than compared
        against a state literal (RG-INC-37) : *in force* is exactly *counts in
        reports* on the core ``default`` lifecycle.
        """
        return self.counts_in_reports

    @property
    def is_review_overdue(self):
        """Whether the scheduled review of the procedure has passed."""
        if not self.review_date:
            return False
        return self.review_date < timezone.localdate()

    @property
    def is_exercise_overdue(self):
        """Whether the plan has gone more than twelve months without a test.

        A plan that has never been exercised is overdue as soon as it is in
        force : A.5.24 asks for a tested plan, and *never tested* is the worst
        case, not an exempt one.
        """
        if not self.is_in_force:
            return False
        if not self.last_exercise_date:
            return True
        return self.last_exercise_date < timezone.localdate() - timedelta(
            days=EXERCISE_STALE_AFTER_DAYS
        )

    # --- Maintained state --------------------------------------------------

    def record_exercise(self, exercise_date):
        """Record the closure date of an exercise as the plan-testing evidence.

        The single writer of ``last_exercise_date`` (RG-INC-17) : the incident
        closure transition calls it with the exercise incident's ``closed_at``.
        Only a more recent date wins, so closing an older exercise after a newer
        one never walks the evidence backwards. Returns ``True`` when the plan
        was actually updated.
        """
        if exercise_date is None:
            return False
        if isinstance(exercise_date, datetime):
            # ``closed_at`` is an aware datetime : the date an operator reads
            # is the local one, the same convention the deadline sweep uses.
            if timezone.is_aware(exercise_date):
                exercise_date = timezone.localtime(exercise_date).date()
            else:
                exercise_date = exercise_date.date()
        if self.last_exercise_date and self.last_exercise_date >= exercise_date:
            return False
        self.last_exercise_date = exercise_date
        self.save(update_fields=["last_exercise_date", "updated_at"])
        return True

    def put_into_force(self, user=None, comment=None):
        """Walk a freshly created plan from ``draft`` to *in force*, atomically.

        For the paths that must produce a plan already in force : the demo seed,
        an import. Writing ``workflow_state="validated"`` at insert would stick,
        because ``_ensure_initial_step()`` only snaps a blank or unknown value,
        but it would leave no ``core.LifecycleEvent`` row : the plan would
        appear in force with no record of ever having been approved, which is
        precisely the evidence A.5.24 and clause 7.5.3 ask for.

        ``enforce_permission=False`` is correct here : these are not user acts.
        A plan put into force through the UI, the API or MCP goes through the
        stepper and is permission-checked at the transition endpoint.
        """
        with transaction.atomic():
            for target in (_DEFAULT_PENDING_STEP, _DEFAULT_VALIDATED_STEP):
                if self.workflow_state == target:
                    continue
                if not any(
                    transition.target == target
                    for transition in self.available_transitions()
                ):
                    continue
                self.transition_to(
                    target, user, comment=comment, enforce_permission=False
                )
            if not self.is_in_force:
                # An archived plan has no route back into force : say so rather
                # than return a plan the caller believes is the one in force.
                raise ValidationError(
                    _("This incident response plan cannot be put into force from its current state.")
                )
        return self

    # --- Validation --------------------------------------------------------

    def clean(self):
        """Reject a regime list that is not a list of known regime values.

        A ``JSONField`` accepts any JSON, and an unknown regime would generate
        no obligation at triage while reading on the plan page as a covered
        duty : silence where a legal position was expected.
        """
        super().clean()
        regimes = self.applicable_regimes
        if regimes in (None, ""):
            return
        if not isinstance(regimes, list):
            raise ValidationError(
                {"applicable_regimes": _("Applicable regimes must be a list.")}
            )
        valid = set(NotificationRegime.values)
        unknown = [regime for regime in regimes if regime not in valid]
        if unknown:
            raise ValidationError(
                {
                    "applicable_regimes": _("Unknown notification regimes : %(values)s")
                    % {"values": ", ".join(str(value) for value in unknown)}
                }
            )
