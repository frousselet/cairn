# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""The regulatory obligation register and its append-only filing log.

Two entities, deliberately in one file because neither is readable without the
other : :class:`IncidentNotification` holds *what is owed, to whom, by when, and
what was decided about it*, and :class:`NotificationFiling` holds *what was
actually transmitted*. The obligation carries the duty and the clock ; the
filing carries the act.

Four properties of this file are load-bearing and none of them is decorative:

1. **The omission is a governed state, not a missing row.** GDPR Art. 33(1)
   does not say *notify* : it says notify **unless** the breach is unlikely to
   result in a risk. That "unless" is a legal act taken under a derogation, and
   Art. 33(5) requires it to be documented. It is therefore the terminal
   ``not_required`` step, reached through an approve-gated, comment-bearing
   transition that stamps a named ``decided_by``, a ``decided_at`` and a written
   ``decision_rationale`` (RG-INC-25). A boolean column carries none of that.
2. **The uniqueness key is a derived, never-null discriminator.** Keying the
   constraint on the nullable recipient foreign keys would not prevent the
   duplicate it is written for : both are ``NULL`` on every auto-generated
   authority obligation and PostgreSQL treats ``NULL``s as distinct in a unique
   index, so re-running generation would silently file a second 72-hour clock
   nobody is watching. ``recipient_key`` is computed in :meth:`save` and the
   generator is independently idempotent : the constraint is the last line of
   defence, never the mechanism.
3. **The clock is stored, and lateness is frozen.** ``anchor_at`` and ``due_at``
   are columns rather than properties because a deadline that cannot be
   filtered, sorted, indexed or swept by the daily escalation command is
   invisible everywhere it matters. They stop recomputing for good at the first
   filing (RG-INC-28), so a later correction of ``Incident.awareness_at`` - a
   field that stays editable, because facts change - can never silently
   un-breach a filing that was late when it was made.
4. **The filing log is append-only.** What we said is frozen ; what they
   answered is completable. Exactly three fields may be written after the
   insert, exactly once each, through :meth:`NotificationFiling.record_outcome`.

As everywhere else in the module, this is **prevention at application level and
detection via** ``HistoricalRecords`` : ``QuerySet.update()``, ``bulk_update()``,
raw SQL and a ``manage.py shell`` session bypass ``save()`` entirely. The honest
claim is that tampering is prevented on every supported path and detectable on
the rest, not that the register is immutable.

Every audit gate lives in :meth:`IncidentNotification.transition_to`
(RG-INC-08), never on the ``Transition`` object : ``lifecycle_to_json`` drops
``form_class`` / ``allowed_roles`` / ``allowed_users`` by design and
``get_lifecycle()`` prefers the ``post_migrate``-seeded ``LifecycleDefinition``
row, so a gate declared that way is green in an in-memory unit test and silently
dead on every migrated database.
"""

import uuid
from datetime import timedelta

from django.apps import apps
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.db import models, transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy
from simple_history.models import HistoricalRecords

from context.models.base import BaseModel, ReferenceGeneratorMixin
from core.lifecycle import DomainRefusalError, LifecycleProtectedError
from incidents.constants import (
    NOTIFICATION_STATES,
    REFERENCE_PREFIXES,
    ClockAnchor,
    ControllerRole,
    FilingOutcome,
    NotificationChannel,
    NotificationRecipientKind,
    NotificationRegime,
    TimelineEntryKind,
    TimelineEntrySource,
)


def _model(name):
    """Resolve a sibling model by label rather than by import.

    Every cross-file reference in this app goes through the app registry or a
    string reference, so no import cycle can form between the module's models.
    """
    return apps.get_model("incidents", name)


def _notification_step(code):
    """Resolve a step code **by name** against the single source of truth.

    Reading the codes back out of ``incidents/constants.py`` (RG-INC-37) means
    a rename there raises at import time instead of silently disabling a gate.
    A dead gate on the Art. 33(1) omission is precisely the class of failure
    this module exists to prevent.
    """
    if code not in {declared for declared, *_flags in NOTIFICATION_STATES}:
        raise ImproperlyConfigured(
            f"'{code}' is not a step of the incident_notification lifecycle."
        )
    return code


STEP_DRAFT = _notification_step("draft")
STEP_ASSESSED = _notification_step("assessed")
STEP_REQUIRED = _notification_step("required")
STEP_DRAFTED = _notification_step("drafted")
STEP_SENT = _notification_step("sent")
STEP_ACKNOWLEDGED = _notification_step("acknowledged")
STEP_NOT_REQUIRED = _notification_step("not_required")
STEP_ARCHIVED = _notification_step("archived")


class NotificationDecision(models.TextChoices):
    """Whether the obligation was decided to apply, not to apply, or not yet.

    Declared here rather than in ``incidents/constants.py`` because it is not
    lifecycle vocabulary : the column **mirrors** the step and is written by the
    same transition, and its two decided values reuse the step codes verbatim so
    the pair can never spell two different things. It exists as a column at all
    because the list facets, the closure gate (RG-INC-14) and the MCP filters
    would otherwise have to read the lifecycle to answer *has anyone decided
    this yet*, which is the one question the register is for.
    """

    UNDECIDED = "undecided", _("Undecided")
    REQUIRED = "required", pgettext_lazy("incident", "Required")
    NOT_REQUIRED = "not_required", _("Not required")


class ObligationSource(models.TextChoices):
    """Whether the row was generated or typed in by hand.

    Governs deletability : a generated obligation is answered through
    ``not_required`` with a rationale and is never deleted, because deleting it
    destroys the evidence that the organisation considered the regime at all.
    """

    AUTO = "auto", _("Generated")
    MANUAL = "manual", _("Added manually")


#: The three deadline buckets an obligation falls in. Collapsing the last two
#: into a single "no date" state is how a real deadline disappears from a
#: dashboard : one has no deadline in law, the other has one that has not
#: started yet, and they are rendered as two different things.
DEADLINE_BUCKET_DATED = "dated"
DEADLINE_BUCKET_NO_DEADLINE = "no_deadline"
DEADLINE_BUCKET_PENDING = "pending"

#: Fallback for ``settings.INCIDENT_NOTIFICATION_MAX_PROOF_BYTES`` (10 MB).
#: Deliberately an order of magnitude below the evidence cap : these bytes live
#: in a database column rather than on a volume, and a portal receipt is a few
#: hundred kilobytes.
DEFAULT_NOTIFICATION_MAX_PROOF_BYTES = 10485760

#: Written by the transition override and by the filing freeze only (G-08,
#: RG-INC-12) : excluded from every ``ModelForm``, ``read_only`` in every
#: serializer, absent from every MCP ``writable_fields`` list, never cleared.
NOTIFICATION_STAMPED_FIELDS = (
    "decision",
    "decided_by",
    "decided_at",
    "sent_at",
    "sent_by",
    "anchor_at",
    "due_at",
    "first_submitted_at",
    "late_by",
    "recipient_key",
)

#: Frozen the instant a filing exists (G-05, RG-INC-29). An amendment is an
#: additional filing on the same obligation, never a rewrite of what was
#: transmitted.
NOTIFICATION_FILED_FROZEN_FIELDS = ("content", "channel", "sent_at")

#: The only three fields a filing accepts after its insert, once each. The
#: recipient's answer arrives after the transmission ; what we said does not
#: change because of it.
FILING_COMPLETION_FIELDS = ("outcome", "acknowledged_at", "external_reference")

#: Bookkeeping columns a completion write is allowed to touch alongside them.
FILING_BOOKKEEPING_FIELDS = ("version", "updated_at")

#: The sibling regime whose **first filing** anchors a staged obligation.
#: NIS2 Art. 23(4)(d) gives one month from the incident **notification**, not
#: from awareness : anchoring it on awareness would make every NIS2 final-report
#: deadline in the register wrong, always in the direction that makes the
#: organisation look later than it is.
STAGE_DEPENDENCIES = {
    NotificationRegime.NIS2_FINAL: NotificationRegime.NIS2_NOTIFICATION,
}


def notification_max_proof_bytes():
    """Cap on the inline proof-of-filing bytes, for both entities."""
    return getattr(
        settings,
        "INCIDENT_NOTIFICATION_MAX_PROOF_BYTES",
        DEFAULT_NOTIFICATION_MAX_PROOF_BYTES,
    )


def _assert_proof_within_cap(value, field):
    """Refuse a proof document above the configured cap.

    Checked in ``save()`` rather than through a field validator : a
    ``BinaryField`` is not editable, so no form or serializer validation pass
    ever runs against it and the only guard that covers the web, DRF and MCP
    write paths at once is the one on the way to the database.
    """
    if not value:
        return
    limit = notification_max_proof_bytes()
    if len(bytes(value)) > limit:
        raise ValidationError(
            {
                field: _(
                    "This proof document exceeds the %(limit)d byte limit. "
                    "Register the document as evidence and link it instead."
                )
                % {"limit": limit}
            }
        )


class ObligationTerms:
    """The legal terms one obligation is instantiated from.

    A small value object rather than a dict so the generator, the template
    snapshot (RG-INC-30) and the shipped regime defaults all produce the same
    shape and a missing term fails at construction instead of surfacing as a
    silently absent deadline three months later.
    """

    __slots__ = (
        "regime",
        "recipient_kind",
        "obligation_reference",
        "clock_anchor",
        "deadline_hours",
        "no_fixed_deadline",
        "content_requirements",
        "authority",
        "template",
        "depends_on_regime",
        "source",
    )

    def __init__(
        self,
        *,
        regime,
        recipient_kind,
        obligation_reference="",
        clock_anchor=ClockAnchor.AWARENESS_AT,
        deadline_hours=None,
        no_fixed_deadline=False,
        content_requirements="",
        authority=None,
        template=None,
        depends_on_regime="",
        source=ObligationSource.AUTO,
    ):
        self.regime = regime
        self.recipient_kind = recipient_kind
        self.obligation_reference = obligation_reference or ""
        self.clock_anchor = clock_anchor
        self.deadline_hours = deadline_hours
        self.no_fixed_deadline = no_fixed_deadline
        self.content_requirements = content_requirements or ""
        self.authority = authority
        self.template = template
        self.depends_on_regime = depends_on_regime or STAGE_DEPENDENCIES.get(
            regime, ""
        )
        self.source = source


#: The shipped defaults for a phase-1 installation, whose obligations are
#: generated from ``IncidentResponsePlan.applicable_regimes`` rather than from
#: the [ReportingObligationTemplate] catalogue. Every entry states either a
#: numeric delay **or** ``no_fixed_deadline``, never neither and never both :
#: a "without undue delay" duty with a fabricated 72-hour clock is a worse
#: record than one with no clock at all.
REGIME_DEFAULTS = {
    NotificationRegime.NIS2_EARLY_WARNING: {
        "recipient_kind": NotificationRecipientKind.SUPERVISORY_AUTHORITY,
        "obligation_reference": "NIS2 Art. 23(4)(a)",
        "deadline_hours": 24,
    },
    NotificationRegime.NIS2_NOTIFICATION: {
        "recipient_kind": NotificationRecipientKind.SUPERVISORY_AUTHORITY,
        "obligation_reference": "NIS2 Art. 23(4)(b)",
        "deadline_hours": 72,
    },
    NotificationRegime.NIS2_FINAL: {
        "recipient_kind": NotificationRecipientKind.SUPERVISORY_AUTHORITY,
        "obligation_reference": "NIS2 Art. 23(4)(d)",
        # One month, counted from the filing of the 72-hour notification.
        "deadline_hours": 720,
        "clock_anchor": ClockAnchor.PREVIOUS_STAGE,
    },
    NotificationRegime.GDPR_ART33_AUTHORITY: {
        "recipient_kind": NotificationRecipientKind.SUPERVISORY_AUTHORITY,
        "obligation_reference": "GDPR Art. 33(1)",
        "deadline_hours": 72,
    },
    NotificationRegime.GDPR_ART33_2_CONTROLLER: {
        "recipient_kind": NotificationRecipientKind.CONTROLLER,
        "obligation_reference": "GDPR Art. 33(2)",
        # "Without undue delay" with no numeric limit : the law states no hours,
        # so neither does the register.
        "no_fixed_deadline": True,
    },
    NotificationRegime.GDPR_ART34_DATA_SUBJECT: {
        "recipient_kind": NotificationRecipientKind.DATA_SUBJECT,
        "obligation_reference": "GDPR Art. 34(1)",
        "no_fixed_deadline": True,
    },
    NotificationRegime.DORA_INITIAL: {
        "recipient_kind": NotificationRecipientKind.SUPERVISORY_AUTHORITY,
        "obligation_reference": "DORA Art. 19",
        # The outer limit of the initial report, counted from awareness. A
        # deployment whose competent authority applies the shorter
        # classification-based delay edits the obligation or ships a template.
        "deadline_hours": 24,
    },
    NotificationRegime.SECTOR_REGULATOR: {
        "recipient_kind": NotificationRecipientKind.SUPERVISORY_AUTHORITY,
        "no_fixed_deadline": True,
    },
    NotificationRegime.CONTRACTUAL_CUSTOMER: {
        "recipient_kind": NotificationRecipientKind.CUSTOMER,
        "no_fixed_deadline": True,
    },
    NotificationRegime.LAW_ENFORCEMENT: {
        "recipient_kind": NotificationRecipientKind.SUPERVISORY_AUTHORITY,
        "no_fixed_deadline": True,
    },
    NotificationRegime.OTHER: {
        "recipient_kind": NotificationRecipientKind.INTERNAL,
        "no_fixed_deadline": True,
    },
}


def _terms_from_regime(regime):
    """Terms for a regime configured on the response plan (phase 1).

    An unknown value cannot raise here : ``applicable_regimes`` is validated
    against the enum by the plan itself, and a regime this table has no entry
    for is still a duty somebody has to answer, so it is instantiated with no
    fabricated deadline rather than dropped.
    """
    defaults = REGIME_DEFAULTS.get(
        regime,
        {
            "recipient_kind": NotificationRecipientKind.INTERNAL,
            "no_fixed_deadline": True,
        },
    )
    return ObligationTerms(regime=regime, **defaults)


def _terms_from_template(template):
    """Snapshot a catalogue row's legal terms onto a new obligation (RG-INC-30).

    Snapshotted rather than read through the foreign key, for the same reason
    ``risks.Risk`` snapshots its criteria : a template corrected in 2027 must
    not retroactively change what a 2025 filing cited. The FK is kept alongside
    the snapshot because it answers a different question - *which rule produced
    this* - and neither substitutes for the other.
    """
    return ObligationTerms(
        regime=template.regime,
        recipient_kind=template.recipient_kind,
        obligation_reference=template.legal_reference,
        clock_anchor=template.clock_anchor,
        deadline_hours=template.clock_hours,
        no_fixed_deadline=template.no_fixed_deadline,
        content_requirements=template.content_requirements,
        authority=template.authority,
        template=template,
        depends_on_regime=template.depends_on_regime,
    )


def _matching_templates(incident):
    """Catalogue rows whose trigger conditions this incident satisfies.

    The ten-condition conjunction is the catalogue entity's own business and is
    implemented there (``ReportingObligationTemplate.matching_for()``) : this
    file consumes the result and owns the snapshot, the idempotence and the
    clock. ``LookupError`` is caught rather than assumed away so an installation
    running the phase-1 subset, with no catalogue at all, still generates its
    obligations from the response plan.
    """
    try:
        Template = _model("ReportingObligationTemplate")
    except LookupError:
        return []
    return list(Template.matching_for(incident))


def _breach_for(incident):
    """The GDPR qualification record of this incident, when one exists.

    Conditions keyed on the qualification evaluate to *no match* when it does
    not : a GDPR-conditioned obligation cannot fire on an incident that has not
    been qualified under GDPR at all.
    """
    try:
        Breach = _model("PersonalDataBreach")
    except LookupError:
        return None
    return Breach.objects.filter(incident=incident).first()


class IncidentNotification(BaseModel):
    """One regulatory or contractual notification obligation.

    Exactly one row per ``(incident, regime, recipient)`` triple. The obligation
    is the unit of record, not the message : it exists as soon as the duty is
    conceivable, it carries the legal clock, it carries the decision on whether
    it applies, and it carries the trail of what was actually filed against it.

    Obligations are instantiated **at triage rather than when someone decides to
    file**, because an obligation nobody has thought about must be *visible*
    rather than absent. It sits in ``assessed`` ("To decide"), it is the loudest
    thing on the incident's notification card, and it blocks closure through
    RG-INC-14. A design that creates the row only when the notification is
    drafted cannot distinguish *we considered GDPR Art. 33 and concluded it did
    not apply* from *nobody looked*, which is exactly the distinction an
    inspection turns on.

    It is **not** a ``ScopedModel``. It inherits the incident's tenancy through
    ``scope_parent_lookup``, declared on the model rather than only on the views
    so the generic workflow, history and MCP surfaces enforce it too (RG-INC-38,
    see ``core.scoping``). The endpoint that would otherwise be left open is the
    one that records the Art. 33(1) omission.
    """

    REFERENCE_PREFIX = REFERENCE_PREFIXES["IncidentNotification"]
    LIFECYCLE_NAME = "incident_notification"

    # Scope is inherited from the parent incident, so it can never drift out of
    # alignment when the incident is re-scoped. `incident` is required, so no
    # `scope_parent_optional` : there is no such thing as a parentless duty.
    scope_parent_lookup = "incident__scopes"

    incident = models.ForeignKey(
        "incidents.Incident",
        on_delete=models.PROTECT,
        related_name="notifications",
        verbose_name=pgettext_lazy("incident", "Incident"),
        help_text=_(
            "The incident the obligation arises from. Protected on delete : an "
            "incident that owes, or owed, a regulator anything can never be "
            "deleted."
        ),
    )

    # --- What is owed, and to whom -----------------------------------------

    regime = models.CharField(
        _("Regime"),
        max_length=32,
        choices=NotificationRegime.choices,
        db_index=True,
        help_text=_("The legal or contractual basis the obligation arises from."),
    )
    recipient_kind = models.CharField(
        _("Recipient kind"),
        max_length=25,
        choices=NotificationRecipientKind.choices,
        db_index=True,
    )
    recipient_stakeholder = models.ForeignKey(
        "context.Stakeholder",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="incident_notifications",
        verbose_name=_("Recipient stakeholder"),
        help_text=_(
            "Registered stakeholder recipient, reusing the stakeholder register "
            "rather than retyping a contact."
        ),
    )
    recipient_supplier = models.ForeignKey(
        "assets.Supplier",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="incident_notifications",
        verbose_name=_("Recipient supplier"),
        help_text=_(
            "Supplier recipient, and the controller we must notify under GDPR "
            "Art. 33(2) when we act as processor."
        ),
    )
    recipient_name = models.CharField(
        _("Recipient"),
        max_length=255,
        blank=True,
        default="",
        help_text=_(
            "Free-text recipient when it is neither a registered stakeholder, "
            "supplier nor authority of record."
        ),
    )
    recipient_key = models.CharField(
        _("Recipient key"),
        max_length=255,
        blank=True,
        default="",
        editable=False,
        help_text=_(
            "Derived recipient discriminator backing the uniqueness of an "
            "obligation. Computed on save, never edited."
        ),
    )
    authority = models.ForeignKey(
        "incidents.ReportingAuthority",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="obligations",
        verbose_name=_("Authority"),
        help_text=_(
            "The body the filing goes to, with its portal, mailbox and "
            "procedure. Protected on delete : an authority that has been "
            "notified is part of the record."
        ),
    )
    template = models.ForeignKey(
        "incidents.ReportingObligationTemplate",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="obligations",
        verbose_name=_("Obligation template"),
        help_text=_(
            "The rule this obligation was generated from. Its legal terms are "
            "snapshotted onto this row and are never rewritten by a later "
            "template edit ; the foreign key answers the other question, which "
            "rule produced this."
        ),
    )
    obligation_reference = models.CharField(
        _("Legal reference"),
        max_length=255,
        blank=True,
        default="",
        help_text=_(
            "The cited article, e.g. 'GDPR Art. 33(1)'. This is the string an "
            "auditor greps the register for."
        ),
    )
    content_requirements = models.TextField(
        _("Content requirements"),
        blank=True,
        default="",
        help_text=_(
            "The legal checklist of what the filing must contain, rendered "
            "beside the drafting field so the drafter never leaves the page to "
            "find out what the article requires."
        ),
    )

    # --- The clock (RG-INC-27, RG-INC-28) ----------------------------------

    clock_anchor = models.CharField(
        _("Clock anchor"),
        max_length=30,
        choices=ClockAnchor.choices,
        default=ClockAnchor.AWARENESS_AT,
        help_text=_(
            "Which timestamp starts the statutory clock. The first four values "
            "are the incident's own field names, so resolution is a lookup with "
            "no mapping table to drift out of date."
        ),
    )
    deadline_hours = models.PositiveIntegerField(
        _("Deadline (hours)"),
        null=True,
        blank=True,
        help_text=_(
            "Statutory delay in wall-clock hours from the anchor : 24, 72, 720. "
            "Empty if and only if the obligation carries no fixed deadline."
        ),
    )
    no_fixed_deadline = models.BooleanField(
        _("No statutory deadline"),
        default=False,
        db_index=True,
        help_text=_(
            "A 'without undue delay' duty with no numeric limit (GDPR "
            "Art. 33(2) and Art. 34(1), NIS2 Art. 23(1)). The obligation is "
            "never counted late and surfaces in its own bucket. Never fabricate "
            "a deadline for an obligation that legally has none."
        ),
    )
    anchor_at = models.DateTimeField(
        _("Anchor timestamp"),
        null=True,
        blank=True,
        db_index=True,
        help_text=_(
            "The resolved anchor actually used, stored so the derivation is "
            "auditable months later rather than re-derived by today's code "
            "against today's data. Frozen at the first filing."
        ),
    )
    due_at = models.DateTimeField(
        _("Due at"),
        null=True,
        blank=True,
        db_index=True,
        help_text=_(
            "The statutory deadline, recomputed on save from the anchor while "
            "no filing exists and never editable directly."
        ),
    )
    depends_on = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="dependents",
        verbose_name=_("Depends on"),
        help_text=_(
            "The sibling obligation whose filing starts this one's clock. The "
            "NIS2 final report is due one month after the incident "
            "notification, not one month after awareness."
        ),
    )

    # --- The decision (RG-INC-25) ------------------------------------------

    decision = models.CharField(
        pgettext_lazy("incident", "Decision"),
        max_length=15,
        choices=NotificationDecision.choices,
        default=NotificationDecision.UNDECIDED,
        db_index=True,
        help_text=_(
            "Mirrors the lifecycle step and is written by the same transition. "
            "Kept as a column so filters, list facets, the closure gate and MCP "
            "never have to read the lifecycle."
        ),
    )
    decision_rationale = models.TextField(
        _("Decision rationale"),
        blank=True,
        default="",
        help_text=_(
            "The Art. 33(1) justification, mandatory once the obligation is "
            "ruled out. The single most audited sentence in a breach file."
        ),
    )
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="incident_notification_decisions",
        verbose_name=_("Decided by"),
        help_text=_("Stamped by the transition, never by a form."),
    )
    decided_at = models.DateTimeField(
        _("Decided at"),
        null=True,
        blank=True,
        help_text=_("Stamped by the transition. Written once."),
    )

    # --- The filing (mirrored from the first NotificationFiling) -----------

    channel = models.CharField(
        _("Channel"),
        max_length=20,
        choices=NotificationChannel.choices,
        blank=True,
        default="",
        help_text=_("How the notification was actually transmitted."),
    )
    content = models.TextField(
        _("Content"),
        blank=True,
        default="",
        help_text=_(
            "The exact text transmitted. Write-once once the filing is "
            "recorded : an amendment is a further filing, never a rewrite of "
            "what left the organisation."
        ),
    )
    sent_at = models.DateTimeField(
        _("Sent at"),
        null=True,
        blank=True,
        db_index=True,
        help_text=_("Transmission timestamp, stamped by the filing transition."),
    )
    sent_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sent_incident_notifications",
        verbose_name=_("Sent by"),
    )
    first_submitted_at = models.DateTimeField(
        _("First filed at"),
        null=True,
        blank=True,
        help_text=_(
            "Stamped by the first filing. Once set, the anchor and the deadline "
            "stop recomputing for good."
        ),
    )
    late_by = models.DurationField(
        _("Late by"),
        null=True,
        blank=True,
        help_text=_(
            "Frozen lateness at the first filing : the positive part of the "
            "delay past the deadline. The breach record, which no later "
            "correction of the anchor can undo."
        ),
    )
    acknowledgement_reference = models.CharField(
        _("Acknowledgement reference"),
        max_length=255,
        blank=True,
        default="",
        help_text=_(
            "The authority's case, ticket or receipt number. An "
            "acknowledgement with no case number is not an acknowledgement."
        ),
    )
    acknowledged_at = models.DateTimeField(
        _("Acknowledged at"),
        null=True,
        blank=True,
    )
    proof_file_content = models.BinaryField(
        _("Proof document"),
        null=True,
        blank=True,
        editable=False,
    )
    proof_filename = models.CharField(
        _("Proof file name"),
        max_length=255,
        blank=True,
        default="",
    )
    proof_evidence = models.ForeignKey(
        "incidents.IncidentEvidence",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notification_proofs",
        verbose_name=pgettext_lazy("incident", "Evidence"),
        help_text=_(
            "Used when the receipt is itself registered as evidence under "
            "A.5.28."
        ),
    )
    source = models.CharField(
        _("Source"),
        max_length=10,
        choices=ObligationSource.choices,
        default=ObligationSource.AUTO,
        db_index=True,
        help_text=_(
            "A generated obligation is answered through a decision, never "
            "deleted : deleting it destroys the evidence that the organisation "
            "considered the regime at all."
        ),
    )

    history = HistoricalRecords(excluded_fields=["proof_file_content"])

    class Meta:
        verbose_name = _("Notification obligation")
        verbose_name_plural = _("Notification obligations")
        # The register reads by deadline within an incident, which is the order
        # the clock actually runs out in.
        ordering = ["incident", "due_at"]
        indexes = [
            # The index the "are we late" query runs on, on the list page, in
            # the calendar, in the dashboard widget and in the daily sweep.
            models.Index(
                fields=["due_at", "workflow_state"],
                name="incidents_notif_due_idx",
            ),
        ]
        constraints = [
            # Keyed on `recipient_key` and never on the nullable recipient FKs :
            # both are NULL on every generated authority obligation, NULLs are
            # distinct inside a unique index on PostgreSQL, and the duplicate
            # this constraint exists for would sail straight through. Three
            # non-nullable columns behave identically on PostgreSQL and on the
            # SQLite the test suite runs against, which `nulls_distinct=False`
            # would not : Django drops that clause with W047 on backends that do
            # not support it, leaving the constraint untested exactly where the
            # regression would be introduced.
            models.UniqueConstraint(
                fields=["incident", "regime", "recipient_key"],
                name="unique_notification_per_incident_regime_recipient",
            ),
            # RG-INC-25 : an omission with no written justification is not a
            # documented omission.
            models.CheckConstraint(
                condition=(
                    ~models.Q(decision=NotificationDecision.NOT_REQUIRED)
                    | ~models.Q(decision_rationale="")
                ),
                name="notification_not_required_has_rationale",
            ),
            # A numeric delay and "no fixed deadline" are mutually exclusive,
            # and exactly one of them must hold.
            models.CheckConstraint(
                condition=(
                    models.Q(no_fixed_deadline=True, deadline_hours__isnull=True)
                    | models.Q(
                        no_fixed_deadline=False, deadline_hours__isnull=False
                    )
                ),
                name="notification_deadline_hours_xor_no_fixed_deadline",
            ),
            # A numeric deadline with no due date is a bug, except in the one
            # legitimate case : a staged obligation whose previous filing has
            # not happened yet.
            models.CheckConstraint(
                condition=(
                    models.Q(no_fixed_deadline=True)
                    | models.Q(due_at__isnull=False)
                    | models.Q(clock_anchor=ClockAnchor.PREVIOUS_STAGE)
                ),
                name="notification_pending_anchor_only_for_previous_stage",
            ),
        ]

    def __str__(self):
        return f"{self.reference} - {self.get_regime_display()}"

    @property
    def workflow_perm_namespace(self):
        """Mandatory override : the default would grant nobody anything.

        ``app_label.model_name`` spells ``incidents.incidentnotification``,
        which matches no feature in ``accounts.constants.PERMISSION_REGISTRY``,
        so every lifecycle permission check on this entity would silently
        evaluate against a codename nobody holds and every transition would be
        refused for everyone.
        """
        return "incidents.notification"

    # --- Read-only display helpers (API / assistant output) ----------------

    @property
    def incident_reference(self):
        """Reference of the parent incident (read-only output)."""
        return self.incident.reference if self.incident_id else ""

    @property
    def incident_name(self):
        """Title of the parent incident (read-only output)."""
        return self.incident.title if self.incident_id else ""

    @property
    def recipient_display(self):
        """The recipient, whichever of the four ways it is recorded.

        Resolved in the same order as ``recipient_key``, so what the register
        displays and what the uniqueness constraint keys on can never disagree.
        """
        if self.recipient_stakeholder_id:
            return self.recipient_stakeholder.name
        if self.recipient_supplier_id:
            return self.recipient_supplier.name
        if self.authority_id:
            return self.authority.short_name or self.authority.name
        if self.recipient_name:
            return self.recipient_name
        return str(self.get_recipient_kind_display())

    @property
    def authority_name(self):
        """Name of the body the filing goes to (read-only output)."""
        return self.authority.name if self.authority_id else ""

    @property
    def template_name(self):
        """Name of the catalogue rule this obligation came from."""
        return self.template.name if self.template_id else ""

    @property
    def decided_by_name(self):
        """Display name of whoever took the decision (read-only output)."""
        return self.decided_by.display_name if self.decided_by_id else ""

    @property
    def sent_by_name(self):
        """Display name of whoever filed it (read-only output)."""
        return self.sent_by.display_name if self.sent_by_id else ""

    @property
    def depends_on_reference(self):
        """Reference of the obligation this one's clock waits on."""
        return self.depends_on.reference if self.depends_on_id else ""

    @property
    def proof_filename_display(self):
        """Filename of the stored proof, or an empty string."""
        return self.proof_filename or ""

    @property
    def has_proof(self):
        """Whether Cairn holds a proof document for this obligation."""
        return bool(self.proof_file_content)

    def get_proof_bytes(self):
        """Return the stored proof bytes, or ``None`` when none is held."""
        return bytes(self.proof_file_content) if self.proof_file_content else None

    # --- Derived state -----------------------------------------------------

    @property
    def is_undecided(self):
        """Whether nobody has yet decided if this obligation applies."""
        return self.decision == NotificationDecision.UNDECIDED

    @property
    def is_overdue(self):
        """Whether the deadline has passed with no filing recorded.

        Always derived, never stored : it is a query, so it is right the instant
        the clock passes and there is no status column to fall out of date
        (RG-INC-28).
        """
        if self.due_at is None or self.sent_at is not None:
            return False
        if self.is_terminal_state:
            return False
        return self.due_at < timezone.now()

    @property
    def was_filed_late(self):
        """Whether the frozen lateness verdict records a breach."""
        return self.late_by is not None

    @property
    def deadline_bucket(self):
        """Which of the three deadline buckets this obligation belongs to.

        The two undated buckets are deliberately distinct : *no statutory
        deadline* is a fact about the law, *deadline pending* is a clock that
        exists and has simply not started. Merging them is how a real deadline
        disappears from a dashboard.
        """
        if self.due_at is not None:
            return DEADLINE_BUCKET_DATED
        if self.no_fixed_deadline:
            return DEADLINE_BUCKET_NO_DEADLINE
        return DEADLINE_BUCKET_PENDING

    # --- The clock ---------------------------------------------------------

    def resolve_anchor(self):
        """The timestamp this obligation's deadline is counted from.

        The first four ``ClockAnchor`` values are the exact field names on
        ``Incident``, so this is a ``getattr`` with no mapping dictionary to
        drift out of date : a grep for the enum value finds both the constant
        and the field it reads. ``previous_stage`` is the one value that is not
        an incident field, which is exactly why it gets its own branch.
        """
        if self.first_submitted_at:
            # Frozen : a filed obligation never recomputes (RG-INC-28).
            return self.anchor_at
        if self.no_fixed_deadline:
            return None
        if self.clock_anchor == ClockAnchor.PREVIOUS_STAGE:
            return self.depends_on.first_submitted_at if self.depends_on_id else None
        if not self.incident_id:
            return None
        return getattr(self.incident, self.clock_anchor, None)

    def _recompute_clock(self, stored):
        """Refresh ``anchor_at`` and ``due_at`` while no filing exists.

        All arithmetic is wall-clock, which is correct for GDPR, NIS2 and DORA :
        the 72 hours of Art. 33(1) run through nights, weekends and public
        holidays. A contractual clause written in business days cannot be
        expressed by this model and is out of scope rather than approximated.
        """
        if stored is not None and stored.first_submitted_at is not None:
            return
        self.anchor_at = self.resolve_anchor()
        if self.anchor_at is not None and self.deadline_hours:
            self.due_at = self.anchor_at + timedelta(hours=self.deadline_hours)
        else:
            self.due_at = None

    def _assert_deadline_consistent(self):
        """Refuse the two deadline shapes the register must never hold.

        Both are also database constraints. They are raised here first so the
        form, the serializer and the MCP tool report a named field rather than
        an ``IntegrityError`` from the middle of a triage transaction.
        """
        errors = {}
        if self.no_fixed_deadline and self.deadline_hours is not None:
            errors["deadline_hours"] = _(
                "An obligation with no statutory deadline carries no number of "
                "hours."
            )
        if not self.no_fixed_deadline and self.deadline_hours is None:
            errors["deadline_hours"] = _(
                "State the statutory delay in hours, or record that the "
                "obligation has no fixed deadline."
            )
        if (
            not self.no_fixed_deadline
            and self.due_at is None
            and self.clock_anchor != ClockAnchor.PREVIOUS_STAGE
        ):
            errors["clock_anchor"] = _(
                "This obligation has a deadline but its anchor is not recorded "
                "on the incident. Record the anchor timestamp, or mark the "
                "obligation as having no fixed deadline."
            )
        if errors:
            raise ValidationError(errors)

    # --- Uniqueness --------------------------------------------------------

    def _derive_recipient_key(self):
        """The non-nullable recipient discriminator the constraint keys on.

        Empty when the obligation is addressed to the regime's authority of
        record with no authority row yet, which is the phase-1 shape and is a
        perfectly good key : two GDPR Art. 33(1) obligations on one incident
        with no named authority are the duplicate this exists to reject.
        """
        if self.recipient_stakeholder_id:
            return f"stakeholder:{self.recipient_stakeholder_id}"
        if self.recipient_supplier_id:
            return f"supplier:{self.recipient_supplier_id}"
        if self.authority_id:
            return f"authority:{self.authority_id}"
        name = (self.recipient_name or "").strip()
        if name:
            return f"name:{name.casefold()}"[:255]
        return ""

    @staticmethod
    def recipient_key_for(*, stakeholder=None, supplier=None, authority=None, name=""):
        """The key a candidate obligation would carry, for the generator.

        Kept beside :meth:`_derive_recipient_key` so the lookup the generator
        performs and the value the row will store are computed by the same two
        lines of logic and cannot drift apart.
        """
        if stakeholder is not None:
            return f"stakeholder:{getattr(stakeholder, 'pk', stakeholder)}"
        if supplier is not None:
            return f"supplier:{getattr(supplier, 'pk', supplier)}"
        if authority is not None:
            return f"authority:{getattr(authority, 'pk', authority)}"
        cleaned = (name or "").strip()
        if cleaned:
            return f"name:{cleaned.casefold()}"[:255]
        return ""

    # --- Write-once guards (G-05, G-06, G-08) ------------------------------

    def save(self, *args, **kwargs):
        """Derive the key, refresh the clock, refuse a write to a frozen field.

        The stored row is re-read and compared field by field, so the guard
        applies to the web form, the DRF serializer, the MCP update tool and the
        Django admin at once rather than being reproduced in four places. The
        stamping transitions themselves pass : the stored row is still unfrozen
        at that instant, and the freeze applies from the next write onwards.

        What bypasses this, stated rather than glossed : ``QuerySet.update()``,
        ``bulk_update()``, raw SQL and a ``manage.py shell`` session never call
        ``save()``. ``HistoricalRecords`` is what turns that prevention gap into
        detection, and it captures every deadline recomputation too, so the
        derivation of a due date is reconstructable from the history alone.
        """
        _assert_proof_within_cap(self.proof_file_content, "proof_file_content")
        self.recipient_key = self._derive_recipient_key()
        stored = None
        if not self._state.adding and self.pk:
            stored = type(self)._base_manager.filter(pk=self.pk).first()
        if stored is not None:
            self._assert_frozen_fields_unchanged(stored)
        self._recompute_clock(stored)
        self._assert_deadline_consistent()
        super().save(*args, **kwargs)

    def _assert_frozen_fields_unchanged(self, stored):
        errors = {}

        # G-08 : the stamps are write-once on every path. They are the record of
        # who decided what, and when.
        for field in ("decided_at", "sent_at", "first_submitted_at", "late_by"):
            if getattr(stored, field) is not None and getattr(self, field) != getattr(
                stored, field
            ):
                errors[field] = _("This timestamp is written once.")

        # G-05 (RG-INC-29) : what was transmitted is not rewritten.
        if stored.sent_at is not None:
            for field in NOTIFICATION_FILED_FROZEN_FIELDS:
                if getattr(self, field) != getattr(stored, field):
                    errors[field] = _(
                        "This field is frozen : the notification was filed on "
                        "%(sent_at)s. An amendment is a further filing."
                    ) % {"sent_at": stored.sent_at}

        # G-06 (RG-INC-28) : the clock of a filed obligation is not recomputed
        # and is not writable either, so a correction of the anchor can never
        # silently un-breach a record.
        if stored.first_submitted_at is not None:
            for field in ("anchor_at", "due_at"):
                if getattr(self, field) != getattr(stored, field):
                    errors[field] = _(
                        "The clock of a filed obligation is frozen and cannot "
                        "be recomputed."
                    )

        if errors:
            raise ValidationError(errors)

    def clean(self):
        """Surface the deadline rules on the form and the serializer too."""
        super().clean()
        self._assert_deadline_consistent()

    def delete(self, *args, **kwargs):
        """Refuse to delete a generated obligation, whatever its step.

        ``draft`` and ``assessed`` stay deletable so an obligation typed in by
        hand in error can be removed without an approver. A **generated** one is
        answered through ``not_required`` with a rationale : deleting it
        destroys the evidence that the organisation considered the regime at
        all, which is the one thing the register exists to prove.
        """
        if self.source == ObligationSource.AUTO:
            raise LifecycleProtectedError(
                "A generated notification obligation is never deleted : decide "
                "that it is not required, with a written rationale."
            )
        return super().delete(*args, **kwargs)

    # --- Lifecycle ---------------------------------------------------------

    def stage_filing_details(
        self,
        *,
        submitted_at=None,
        channel=None,
        subject="",
        content=None,
        recipient_name="",
        external_reference="",
        proof_file_content=None,
        proof_filename="",
    ):
        """Carry the details of a filing into the transition that records it.

        ``BaseModel.transition_to()`` has a fixed signature that the generic
        stepper endpoint, the DRF mixin and the MCP handler all call, so the
        *record filing* form stages its extra fields on the instance first.
        :meth:`record_filing` does the same for a caller that has them to hand.
        """
        self._pending_filing = {
            "submitted_at": submitted_at,
            "channel": channel,
            "subject": (subject or "").strip(),
            "content": content,
            "recipient_name": (recipient_name or "").strip(),
            "external_reference": (external_reference or "").strip(),
            "proof_file_content": proof_file_content,
            "proof_filename": (proof_filename or "").strip(),
        }
        return self._pending_filing

    def transition_to(
        self,
        target,
        user=None,
        comment=None,
        *,
        enforce_permission=False,
        save=True,
    ):
        """Apply the obligation gates, stamp the write-once fields, then move.

        The whole body runs in one transaction, so a refusal leaves neither a
        stamp nor a filing row, and a committed filing transition leaves exactly
        one filing, one frozen lateness verdict and one chronology line.

        Gates raise :class:`core.lifecycle.LifecycleError` rather than a bare
        ``ValidationError`` : that is the exception the generic stepper endpoint
        catches and turns into a message, and the DRF mixin catches both, so it
        behaves correctly on all three write surfaces.
        """
        from core.lifecycle import validate_transition

        lifecycle = self.get_lifecycle()
        current = self.workflow_state or lifecycle.initial_step.code
        # Legality and the mandatory-comment rule first, so an illegal move is
        # reported as such rather than as a domain refusal.
        validate_transition(
            lifecycle, current, target, instance=self, user=user,
            comment=comment, enforce_permission=False,
        )
        with transaction.atomic():
            self._check_transition_gates(current, target, comment)
            self._stamp_transition(current, target, user, comment)
            result = super().transition_to(
                target, user, comment=comment,
                enforce_permission=enforce_permission, save=save,
            )
            self._apply_side_effects(current, target, user, comment)
        self._pending_filing = {}
        return result

    def _check_transition_gates(self, current, target, comment):
        """Refuse the moves the obligation register must never record."""
        staged = getattr(self, "_pending_filing", {}) or {}

        # G-01 (RG-INC-25) : the omission is a judgement, and a judgement with
        # no written reason is not one. `requires_comment` on the transition
        # already refuses a blank comment ; this covers the row that reaches the
        # step with neither a comment nor a stored rationale.
        if target == STEP_NOT_REQUIRED and not (
            (comment or "").strip() or self.decision_rationale.strip()
        ):
            raise DomainRefusalError(
                str(_(
                    "Deciding not to notify requires a written rationale : this "
                    "is the Art. 33(1) justification an inspector reads first."
                ))
            )

        if target == STEP_SENT:
            # G-02 : a filing with no channel and no content is not a filing.
            channel = staged.get("channel") or self.channel
            if not channel:
                raise DomainRefusalError(
                    str(_(
                        "Recording a filing requires the channel it was "
                        "transmitted through."
                    ))
                )
            content = staged.get("content")
            if content is None:
                content = self.content
            if not (content or "").strip():
                raise DomainRefusalError(
                    str(_(
                        "Recording a filing requires the content that was "
                        "transmitted, or the filing that carries it."
                    ))
                )
            submitted_at = staged.get("submitted_at") or self.sent_at
            if submitted_at is not None and submitted_at > timezone.now():
                raise DomainRefusalError(
                    str(_("A filing cannot be recorded in the future."))
                )
            self._check_early_warning_content()

        # G-04 : an acknowledgement with no case number is not an
        # acknowledgement.
        if target == STEP_ACKNOWLEDGED and not self.acknowledgement_reference.strip():
            raise DomainRefusalError(
                str(_(
                    "Recording an acknowledgement requires the recipient's "
                    "case, ticket or receipt number."
                ))
            )

        # G-07 : the restore bookend is the one edge that could walk an
        # obligation of record back into a deletable step. It is refused for any
        # row the immutable ledger shows has ever been opened.
        if current == STEP_ARCHIVED and target == STEP_DRAFT and self._has_left_draft():
            raise DomainRefusalError(
                str(_(
                    "An obligation that was opened for decision cannot be "
                    "restored to draft."
                ))
            )

    def _check_early_warning_content(self):
        """G-03 : NIS2 Art. 23(4)(a) asks two questions the record must answer.

        The early warning must state whether the incident is suspected of being
        caused by an unlawful or malicious act and whether it has cross-border
        impact. An early warning that cannot answer them cannot be completed
        from the record, and the gate says so rather than filing a blank. The
        three verdicts are three-state on purpose, so each is compared to
        ``None`` and never with a truthiness test : *not yet determined* is not
        *no*.
        """
        if self.regime != NotificationRegime.NIS2_EARLY_WARNING:
            return
        incident = self.incident
        missing = [
            field
            for field in ("is_significant", "suspected_malicious", "cross_border_impact")
            if getattr(incident, field, None) is None
        ]
        if missing:
            raise DomainRefusalError(
                str(_(
                    "A NIS2 early warning states whether the incident is "
                    "significant, whether it is suspected to be malicious and "
                    "whether it has cross-border impact. Record those verdicts "
                    "on the incident first."
                ))
            )

    def _stamp_transition(self, current, target, user, comment):
        """Write the fields the lifecycle owns, and only it (G-08, RG-INC-12).

        Write-once in both directions : a stamp already set is never rewritten,
        and the only value ever cleared is ``decision``, which mirrors the step
        and therefore has to follow a reopened decision back to *undecided*.
        ``decided_by`` and ``decided_at`` deliberately survive that reopening :
        they record that a decision was once taken, which is a fact, and the
        rationale that went with it stays readable in the register.
        """
        staged = getattr(self, "_pending_filing", {}) or {}

        if target == STEP_REQUIRED:
            self.decision = NotificationDecision.REQUIRED
            self._stamp_decision(user)
        elif target == STEP_NOT_REQUIRED:
            self.decision = NotificationDecision.NOT_REQUIRED
            if (comment or "").strip():
                # Persisted into the register itself, not only into the
                # `core.LifecycleEvent`, so the omission is readable without
                # joining the history.
                self.decision_rationale = comment.strip()
            self._stamp_decision(user)
        elif target == STEP_ASSESSED and current == STEP_NOT_REQUIRED:
            self.decision = NotificationDecision.UNDECIDED

        if target == STEP_SENT:
            if staged.get("channel"):
                self.channel = staged["channel"]
            if staged.get("content") is not None:
                self.content = staged["content"]
            if self.sent_at is None:
                self.sent_at = staged.get("submitted_at") or timezone.now()
            if self.sent_by_id is None and user is not None:
                self.sent_by = user
            self._freeze_lateness()

        if target == STEP_ACKNOWLEDGED and self.acknowledged_at is None:
            self.acknowledged_at = timezone.now()

    def _stamp_decision(self, user):
        if self.decided_at is None:
            self.decided_at = timezone.now()
        if self.decided_by_id is None and user is not None:
            self.decided_by = user

    def _freeze_lateness(self):
        """Stamp ``first_submitted_at`` and ``late_by``, once and for ever.

        This is not an optimisation, it is the point. ``Incident.awareness_at``
        stays editable after triage because facts change, and without the freeze
        a six-hour correction of the anchor would move ``due_at`` past a filing
        that was late when it was made : an obligation that breached the
        72-hour limit would quietly stop having breached it, with nothing in the
        record to show it ever did.
        """
        if self.first_submitted_at is not None:
            return
        self.first_submitted_at = self.sent_at
        if self.due_at is not None and self.first_submitted_at > self.due_at:
            self.late_by = self.first_submitted_at - self.due_at
        else:
            self.late_by = None

    def _apply_side_effects(self, current, target, user, comment):
        """The filing row, the dependent clocks and the chronology line."""
        if target != STEP_SENT:
            return
        filing = self._record_first_filing(user, comment)
        self._recorded_filing = filing
        # This is the moment a staged clock actually starts : the NIS2
        # Art. 23(4)(d) one-month final report is due from *this* filing.
        self.recompute_dependent_clocks()
        self._append_chronology_entry(user, comment)

    def _record_first_filing(self, user, comment):
        """Insert the filing that discharges this obligation for the first time.

        Recorded here rather than left to the caller so a transmission can never
        be recorded without the lateness verdict that goes with it, on any of
        the three write surfaces. An obligation that somehow already carries a
        filing (a re-run of the same transition) inserts nothing : the log is
        append-only, not append-twice.
        """
        if self.filings.exists():
            return None
        staged = getattr(self, "_pending_filing", {}) or {}
        return NotificationFiling.objects.create(
            notification=self,
            submitted_at=self.first_submitted_at or self.sent_at,
            channel=self.channel or NotificationChannel.PORTAL,
            recipient_name=staged.get("recipient_name") or self.recipient_name,
            external_reference=staged.get("external_reference", ""),
            subject=staged.get("subject", ""),
            content=staged.get("content") if staged.get("content") is not None else self.content,
            submitted_by=user or self.sent_by,
            proof_file_content=staged.get("proof_file_content"),
            proof_filename=staged.get("proof_filename", ""),
        )

    def recompute_dependent_clocks(self):
        """Start the clock of every obligation waiting on this one's filing.

        A per-row ``save()`` and never ``QuerySet.update()``, so
        ``HistoricalRecords`` captures each recomputation and the derivation of
        a due date stays reconstructable from the history alone (RG-INC-40 keeps
        the same discipline in the daily sweep).
        """
        for dependent in self.dependents.filter(
            clock_anchor=ClockAnchor.PREVIOUS_STAGE, first_submitted_at__isnull=True
        ):
            dependent.save()

    def _append_chronology_entry(self, user, comment):
        """Narrate the filing in the incident's chronology (RG-INC-09).

        A transition with no actor at all (a migration, a fixture) appends
        nothing : the chronology's author is a required, ``PROTECT``-ed
        attribution, and an unattributed line in the account a regulator reads
        is worse than none. The move itself is still recorded, with its null
        actor, in the immutable ``LifecycleEvent``.
        """
        if user is None:
            return
        _model("IncidentTimelineEntry").objects.create(
            incident=self.incident,
            occurred_at=self.sent_at or timezone.now(),
            entry_type=TimelineEntryKind.COMMUNICATION,
            source=TimelineEntrySource.LIFECYCLE,
            summary=str(
                _("Notification filed : %(reference)s (%(regime)s)")
                % {
                    "reference": self.reference,
                    "regime": self.get_regime_display(),
                }
            )[:500],
            detail=(comment or "").strip(),
            author=user,
        )

    def _has_left_draft(self):
        """Whether the immutable ledger records a step beyond draft / archived."""
        from django.contrib.contenttypes.models import ContentType

        from core.models import LifecycleEvent

        return (
            LifecycleEvent.objects.filter(
                content_type=ContentType.objects.get_for_model(type(self)),
                object_id=str(self.pk),
            )
            .exclude(to_step__in=[STEP_DRAFT, STEP_ARCHIVED])
            .exists()
        )

    # --- Recording a filing ------------------------------------------------

    @transaction.atomic
    def record_filing(
        self,
        user=None,
        *,
        submitted_at=None,
        channel=None,
        subject="",
        content=None,
        recipient_name="",
        external_reference="",
        proof_file_content=None,
        proof_filename="",
        is_correction=False,
        supersedes=None,
        comment=None,
    ):
        """Record one transmission against this obligation.

        The **first** filing is a single atomic act performed through the
        lifecycle (RG-INC-08) : it inserts the filing, stamps ``sent_at``,
        ``sent_by``, ``first_submitted_at`` and ``late_by``, moves the
        obligation to ``sent``, starts any dependent clock and narrates the act
        in the incident's chronology. Every **subsequent** filing inserts
        normally and changes none of the frozen values : the obligation stays
        one row with one clock, one decision and one lateness verdict, and
        GDPR Art. 33(4) phased provision becomes a further filing rather than an
        edit of what was already sent.
        """
        if not self.filings.exists():
            if is_correction:
                raise ValidationError(
                    {"is_correction": _("The first filing is never a correction.")}
                )
            self.stage_filing_details(
                submitted_at=submitted_at,
                channel=channel,
                subject=subject,
                content=content,
                recipient_name=recipient_name,
                external_reference=external_reference,
                proof_file_content=proof_file_content,
                proof_filename=proof_filename,
            )
            self.transition_to(STEP_SENT, user, comment=comment)
            return getattr(self, "_recorded_filing", None)

        filing = NotificationFiling(
            notification=self,
            submitted_at=submitted_at or timezone.now(),
            channel=channel or self.channel or NotificationChannel.PORTAL,
            recipient_name=(recipient_name or self.recipient_name or "").strip(),
            external_reference=(external_reference or "").strip(),
            subject=(subject or "").strip(),
            content=content or "",
            submitted_by=user,
            is_correction=is_correction,
            supersedes=supersedes,
            proof_file_content=proof_file_content,
            proof_filename=(proof_filename or "").strip(),
        )
        filing.full_clean(exclude=["reference", "was_late"])
        filing.save()
        return filing

    # --- Generation (RG-INC-11, RG-INC-18, RG-INC-30) ----------------------

    @classmethod
    @transaction.atomic
    def generate_obligations(cls, incident, user=None):
        """Instantiate every obligation this incident raises, idempotently.

        Runs at triage, on a severity raise that can cross a template's floor,
        and on the confirmation of a personal data breach, because the answer
        can change at each of those points and the absence of a re-run is a
        missed 24-hour clock rather than a cosmetic gap.

        Idempotence is the generator's own job and not the constraint's :
        relying on the unique index alone would turn a re-run into an
        ``IntegrityError`` in the middle of a severity-raise save, which is a
        worse failure than the duplicate it prevents. Re-running therefore never
        duplicates a row, never rewrites a snapshot a template has since
        changed, and never revisits a decision already taken.

        Returns the obligations it actually created, each already moved to
        ``assessed`` : nothing here is ever *created in* a domain step, because
        an insert that names one leaves no ``core.LifecycleEvent`` and therefore
        no record that the obligation was ever opened.
        """
        if incident.is_exercise:
            # RG-INC-17. Also guarded on the incident, and stated twice on
            # purpose : filing a real notification for a drill is an incident in
            # its own right.
            return []

        created = []
        terms_list = cls._terms_for(incident)
        for terms in terms_list:
            obligation, was_created = cls._ensure_obligation(incident, terms, user)
            if was_created:
                created.append(obligation)
        cls._wire_stage_dependencies(incident, terms_list)
        return created

    @classmethod
    def _terms_for(cls, incident):
        """The obligations this incident owes, as snapshottable terms.

        The catalogue is authoritative where it has an opinion : a regime a
        matching template covers is never generated a second time from the
        response plan's flat list, which would file two rows for one duty with
        two different recipients and two clocks.
        """
        terms_list = [
            _terms_from_template(template) for template in _matching_templates(incident)
        ]
        covered = {terms.regime for terms in terms_list}

        plan = incident.response_plan
        for regime in (plan.applicable_regimes or []) if plan else []:
            if regime in covered:
                continue
            terms_list.append(_terms_from_regime(regime))
            covered.add(regime)

        terms_list.extend(cls._gdpr_terms(incident, covered))
        return terms_list

    @classmethod
    def _gdpr_terms(cls, incident, covered):
        """The GDPR obligations the flags force, whatever the plan says.

        RG-INC-18 : ``personal_data_involved`` alone instantiates the Art. 33(1)
        duty, because a plan that forgot to list the regime must never read as
        *nothing was owed*. The capacity the organisation acted in is what
        decides which duty exists at all : a processor owes Art. 33(2) to its
        controller and never Art. 33(1) to the supervisory authority, so the two
        are mutually exclusive rather than cumulative. The Art. 34 duty is added
        only on a verdict of exactly ``True`` : a high-risk assessment nobody
        has made yet is not a high risk, and it is not a no either.
        """
        if not incident.personal_data_involved:
            return []

        breach = _breach_for(incident)
        controller_role = getattr(breach, "controller_role", None)
        terms = []
        if controller_role == ControllerRole.PROCESSOR:
            regime = NotificationRegime.GDPR_ART33_2_CONTROLLER
        else:
            regime = NotificationRegime.GDPR_ART33_AUTHORITY
        if regime not in covered:
            terms.append(_terms_from_regime(regime))

        if (
            getattr(breach, "high_risk_to_rights", None) is True
            and NotificationRegime.GDPR_ART34_DATA_SUBJECT not in covered
        ):
            terms.append(_terms_from_regime(NotificationRegime.GDPR_ART34_DATA_SUBJECT))
        return terms

    @classmethod
    def _ensure_obligation(cls, incident, terms, user):
        """Resolve one candidate to an existing row, or create and open it.

        An explicit lookup on ``(incident, regime, recipient_key)`` rather than
        ``get_or_create`` on the model's own kwargs : the key is derived in
        ``save()`` from four different recipient fields, so it is the only value
        both sides of the comparison can be written in terms of.
        """
        recipient_key = cls.recipient_key_for(authority=terms.authority)
        existing = cls.objects.filter(
            incident=incident, regime=terms.regime, recipient_key=recipient_key
        ).first()
        if existing is None and recipient_key:
            # An obligation generated before the authority of record was known
            # carries the empty placeholder key for the very same duty : the
            # regime's authority, not yet named. Adopting it rather than
            # inserting beside it is what keeps one clock per duty when a
            # catalogue is populated on an incident that was triaged without
            # one. The row is adopted untouched : generation never rewrites a
            # snapshot (RG-INC-30).
            existing = cls.objects.filter(
                incident=incident, regime=terms.regime, recipient_key=""
            ).first()
        if existing is not None:
            return existing, False

        obligation = cls(
            incident=incident,
            regime=terms.regime,
            recipient_kind=terms.recipient_kind,
            obligation_reference=terms.obligation_reference,
            content_requirements=terms.content_requirements,
            clock_anchor=terms.clock_anchor,
            deadline_hours=terms.deadline_hours,
            no_fixed_deadline=terms.no_fixed_deadline,
            authority=terms.authority,
            template=terms.template,
            source=terms.source,
            created_by=user,
        )
        obligation.save()
        # Saved in `draft`, then transitioned : the row must carry a
        # `core.LifecycleEvent` recording its entry into the register, and a row
        # left in `draft` would be deletable, absent from the "To decide" bucket
        # and still blocking closure with no visible reason.
        # `enforce_permission=False` is correct : the permission was checked on
        # the parent transition the user actually performed, and the obligation
        # is a consequence of it rather than a separate act.
        obligation.transition_to(STEP_ASSESSED, user, enforce_permission=False)
        return obligation, True

    @classmethod
    def _wire_stage_dependencies(cls, incident, terms_list):
        """Point each staged obligation at the filing that starts its clock.

        Done in a second pass because the obligation a staged one depends on may
        have been created after it in the same run, and because a re-run must
        repair a link left dangling by a partial earlier generation.
        """
        dependency_regimes = {
            terms.regime: terms.depends_on_regime
            for terms in terms_list
            if terms.depends_on_regime
        }
        if not dependency_regimes:
            return
        staged = cls.objects.filter(
            incident=incident,
            clock_anchor=ClockAnchor.PREVIOUS_STAGE,
            depends_on__isnull=True,
        )
        for obligation in staged:
            dependency_regime = dependency_regimes.get(obligation.regime)
            if not dependency_regime:
                continue
            dependency = (
                cls.objects.filter(incident=incident, regime=dependency_regime)
                .exclude(pk=obligation.pk)
                .first()
            )
            if dependency is None:
                continue
            obligation.depends_on = dependency
            obligation.save()


class NotificationFiling(ReferenceGeneratorMixin):
    """One append-only record of an actual transmission to a recipient.

    This is the evidence handed to an inspector who asks *prove you filed the
    72-hour notification*. The obligation says what was owed and when ; the
    filing says what was actually done, and it is the only record that can
    answer with a document rather than with a status.

    Not a ``BaseModel``, and each reason is load-bearing:

    **No lifecycle.** A transmission has no states : it happened, at a time,
    through a channel, with a content. A workflow would put a governance process
    around a fact and would make the log filterable by a step that carries no
    meaning. The entity therefore carries no ``workflow_state`` at all and is
    deliberately invisible to ``reportable()``, ``linkable()`` and
    ``deletable_states()`` : it is read through its parent obligation, always.
    What it does carry is ``outcome``, which records the recipient's response -
    a fact about the world, not a state of our process.

    **A reference prefix, unlike the chronology.** A busy obligation has two or
    three filings and a contested one perhaps a dozen, and each one is *cited* :
    "the 72-hour notification was filed as NFIL-12 on 14 March and supplemented
    by NFIL-19 on 21 March" is a sentence someone has to be able to write. The
    reference scan is paid a handful of times per incident and buys a citable
    identity, which is the trade the mixin exists for.

    **Never rewritten.** What we said is frozen ; what they answered is
    completable. Exactly three fields may be written after the insert, once
    each, through :meth:`record_outcome`, and everything else refuses any
    post-insert write. A correction to what the organisation told a regulator is
    a **new filing**, never an edit of the old one.
    """

    REFERENCE_PREFIX = REFERENCE_PREFIXES["NotificationFiling"]

    # A grandchild of a scoped model chains its parent's lookup (RG-INC-38).
    # What leaks otherwise is the verbatim regulatory content of another
    # perimeter's filings.
    scope_parent_lookup = "notification__incident__scopes"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    notification = models.ForeignKey(
        IncidentNotification,
        on_delete=models.CASCADE,
        related_name="filings",
        verbose_name=_("Obligation"),
        help_text=_(
            "The obligation this transmission discharges, in whole or in part. "
            "Cascade is safe : an obligation is undeletable from 'required' "
            "onward, and one that can still be deleted has no filings by "
            "construction."
        ),
    )
    submitted_at = models.DateTimeField(
        _("Submitted at"),
        db_index=True,
        help_text=_(
            "When the filing actually left the organisation, not when the row "
            "was typed. A portal submission recorded two hours later carries "
            "the submission time, and the recording delay stays visible."
        ),
    )
    channel = models.CharField(
        _("Channel"),
        max_length=20,
        choices=NotificationChannel.choices,
        default=NotificationChannel.PORTAL,
    )
    recipient_name = models.CharField(
        _("Recipient"),
        max_length=255,
        blank=True,
        default="",
        help_text=_(
            "The named desk, mailbox or person who received it, when that is "
            "finer-grained than the obligation's recipient."
        ),
    )
    external_reference = models.CharField(
        _("External reference"),
        max_length=200,
        blank=True,
        default="",
        help_text=_(
            "The authority's case, ticket or receipt number. A portal returns "
            "one immediately, an email filing does not, so this is one of the "
            "three fields completable after the insert."
        ),
    )
    subject = models.CharField(
        _("Subject"),
        max_length=500,
        blank=True,
        default="",
    )
    content = models.TextField(
        _("Content"),
        blank=True,
        default="",
        help_text=_(
            "Verbatim content of what was sent. Never edited : a correction is "
            "a new row. This is the field an inspector reads."
        ),
    )
    outcome = models.CharField(
        _("Outcome"),
        max_length=25,
        choices=FilingOutcome.choices,
        default=FilingOutcome.SENT,
        db_index=True,
        help_text=_("The recipient's response, completable once after the filing."),
    )
    acknowledged_at = models.DateTimeField(
        _("Acknowledged at"),
        null=True,
        blank=True,
    )
    is_correction = models.BooleanField(
        _("Correction"),
        default=False,
        help_text=_(
            "A corrective or supplementary filing (GDPR Art. 33(4) phased "
            "provision, or a response to an information request). The first "
            "filing on an obligation is never a correction."
        ),
    )
    was_late = models.BooleanField(
        _("Filed late"),
        default=False,
        help_text=_(
            "Frozen at the insert from the obligation's deadline and never "
            "recomputed. False when the obligation carries no deadline."
        ),
    )
    supersedes = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="superseded_by",
        verbose_name=_("Supersedes"),
        help_text=_(
            "The earlier filing on the same obligation that this one replaces. "
            "Empty on a supplementary filing that adds information without "
            "retracting anything."
        ),
    )
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="incident_filings",
        verbose_name=_("Submitted by"),
        help_text=_(
            "Who transmitted it. Nulled rather than protected on delete : the "
            "filing's evidential weight rests on its content and its receipt, "
            "not on the account still existing, and the history keeps the name."
        ),
    )
    proof_file_content = models.BinaryField(
        _("Proof document"),
        null=True,
        blank=True,
        editable=False,
    )
    proof_filename = models.CharField(
        _("Proof file name"),
        max_length=255,
        blank=True,
        default="",
    )
    # Mirrors the `SupplierSubprocessor` precedent for non-`BaseModel` audit
    # rows. A value other than 1 means a completion field was filled in after
    # the insert, which is legitimate but visible.
    version = models.PositiveIntegerField(_("Version"), default=1)
    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated at"), auto_now=True)

    # Tamper detection, not tamper prevention : see the class docstring.
    history = HistoricalRecords(excluded_fields=["proof_file_content"])

    class Meta:
        verbose_name = _("Notification filing")
        verbose_name_plural = _("Notification filings")
        # Most recent transmission first, which is what the detail page and the
        # API caller both want. The narrative order is the reverse, and the UI
        # renders the filing card ascending.
        ordering = ["-submitted_at"]
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(supersedes__isnull=True) | models.Q(is_correction=True)
                ),
                name="filing_supersedes_implies_correction",
            ),
        ]

    def __str__(self):
        return f"{self.reference} - {self.submitted_at:%Y-%m-%d %H:%M}"

    # --- Read-only display helpers (API / assistant output) ----------------

    @property
    def notification_reference(self):
        """Reference of the obligation being discharged (read-only output)."""
        return self.notification.reference if self.notification_id else ""

    @property
    def incident_reference(self):
        """Reference of the incident behind the obligation (read-only output)."""
        return self.notification.incident_reference if self.notification_id else ""

    @property
    def regime(self):
        """The obligation's regime, so a filing row reads on its own."""
        return self.notification.regime if self.notification_id else ""

    @property
    def submitted_by_name(self):
        """Display name of whoever transmitted it (read-only output)."""
        return self.submitted_by.display_name if self.submitted_by_id else ""

    @property
    def supersedes_reference(self):
        """Reference of the filing this one replaces (read-only output)."""
        return self.supersedes.reference if self.supersedes_id else ""

    @property
    def is_superseded(self):
        """Whether a later filing replaced this one.

        Derived from the reverse relation, never from a stored ``outcome`` :
        stamping ``superseded`` on an old row would be a post-insert write to a
        field outside the completion set, and the log does not do that.
        """
        return self.superseded_by.exists()

    @property
    def has_proof(self):
        """Whether Cairn holds a proof document for this filing."""
        return bool(self.proof_file_content)

    def get_proof_bytes(self):
        """Return the stored proof bytes, or ``None`` when none is held."""
        return bytes(self.proof_file_content) if self.proof_file_content else None

    @property
    def recording_delay(self):
        """``created_at - submitted_at`` : how long the filing went unrecorded.

        Derived rather than stored. A filing made on a portal at 03:00 and typed
        up at 09:00 is legitimate, and the gap is itself information the auditor
        is entitled to see, so the UI shows both timestamps whenever they differ
        by more than a few minutes and never hides the delay.
        """
        if self.created_at is None or self.submitted_at is None:
            return None
        return self.created_at - self.submitted_at

    # --- Validation --------------------------------------------------------

    def clean(self):
        """Keep a supersession chain inside one obligation, and in the past."""
        super().clean()
        errors = {}

        if self.submitted_at and self.submitted_at > timezone.now():
            errors["submitted_at"] = _("A filing cannot be recorded in the future.")

        if self.supersedes_id:
            if self.supersedes_id == self.pk:
                errors["supersedes"] = _("A filing cannot supersede itself.")
            elif self.supersedes.notification_id != self.notification_id:
                errors["supersedes"] = _(
                    "A filing can only supersede another filing on the same "
                    "obligation."
                )
            if not self.is_correction:
                errors["is_correction"] = _(
                    "A filing that replaces another one is a correction."
                )

        if (
            self.is_correction
            and self._state.adding
            and self.notification_id
            and not NotificationFiling.objects.filter(
                notification_id=self.notification_id
            ).exists()
        ):
            errors["is_correction"] = _("The first filing is never a correction.")

        if errors:
            raise ValidationError(errors)

    # --- Append-only guards ------------------------------------------------

    def save(self, *args, **kwargs):
        """Insert freely, then accept only the three completion writes.

        Enforced at application level : ``QuerySet.update()``,
        ``bulk_update()``, cascade deletion, raw SQL and a ``manage.py shell``
        session never reach this method. ``HistoricalRecords`` is what turns
        that prevention gap into detection, which is why the honest claim to
        make to an auditor is *tampering with the filing log is prevented on
        every supported path and detectable on the rest*, and not *the filing
        log is immutable*.
        """
        _assert_proof_within_cap(self.proof_file_content, "proof_file_content")
        if self._state.adding:
            self._freeze_lateness_verdict()
            return super().save(*args, **kwargs)

        stored = type(self)._base_manager.filter(pk=self.pk).first()
        if stored is None:
            raise LifecycleProtectedError(
                "A filing that is no longer in the log cannot be rewritten."
            )
        self._assert_only_completion_changed(stored)
        return super().save(*args, **kwargs)

    def _freeze_lateness_verdict(self):
        """Compute ``was_late`` once, at the insert, and never again.

        Read off the obligation's stored ``due_at``, which is itself frozen from
        the first filing onward, so the verdict on this row is a fact about the
        duty as it stood when the transmission was made.
        """
        due_at = self.notification.due_at if self.notification_id else None
        self.was_late = bool(
            due_at is not None and self.submitted_at is not None
            and self.submitted_at > due_at
        )

    def _assert_only_completion_changed(self, stored):
        """Refuse every post-insert write except a first completion.

        The completion exception is deliberately narrow : each of the three
        fields moves once, from its insert value to a set value, never from one
        set value to another. A filing whose history shows more than two rows
        has been touched more than the design allows, and that is visible.
        """
        changed = [
            field.name
            for field in self._meta.concrete_fields
            if field.name not in FILING_BOOKKEEPING_FIELDS
            and getattr(self, field.attname) != getattr(stored, field.attname)
        ]
        forbidden = [name for name in changed if name not in FILING_COMPLETION_FIELDS]
        if forbidden:
            raise LifecycleProtectedError(
                "The filing log is append-only : what was transmitted is never "
                "rewritten. Record a correction as a new filing "
                f"(refused change to {', '.join(sorted(forbidden))})."
            )
        insert_values = {
            "outcome": FilingOutcome.SENT,
            "acknowledged_at": None,
            "external_reference": "",
        }
        for name in changed:
            if getattr(stored, name) != insert_values[name]:
                raise LifecycleProtectedError(
                    f"The filing's '{name}' has already been completed and is "
                    "written once."
                )

    def delete(self, *args, **kwargs):
        """Refuse deletion outright : there is no delete route on any surface."""
        raise LifecycleProtectedError(
            "A notification filing is never deleted : the log is append-only."
        )

    # --- The narrow completion exception -----------------------------------

    @transaction.atomic
    def record_outcome(
        self, *, outcome=None, acknowledged_at=None, external_reference=None
    ):
        """Complete this filing with the recipient's answer, once.

        The single place the completion exception is implemented, so the web
        form, the DRF patch route and the MCP tool cannot each grow their own
        idea of what may be written after the fact. The ``save()`` guard refuses
        anything else, including a second write to a completion field, and every
        completion write is historised.
        """
        if outcome is not None:
            self.outcome = outcome
        if acknowledged_at is not None:
            self.acknowledged_at = acknowledged_at
        if external_reference is not None:
            self.external_reference = external_reference.strip()
        self.version += 1
        self.save()
        return self
