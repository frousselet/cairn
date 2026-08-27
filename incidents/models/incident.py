# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""The A.5.26 incident file : the record every other entity in the module hangs off.

Two properties are load-bearing here and are argued where they are implemented
rather than assumed :

**Two clocks.** ``detected_at`` is when a control, a tool or a person saw
something, and it is the base of the mean-time-to-detect indicator. It has no
legal meaning. ``awareness_at`` is the point at which the organisation became
aware within the meaning of GDPR Art. 33(1) and NIS2 Art. 23, and **every**
statutory deadline in the module derives from it and from nothing else.
Anchoring a 72-hour clock to technical detection is legally wrong and is the
first thing a supervisory-authority inspector attacks.

**A decision is a transition, never a field write.** Declaring, triaging,
closing, reopening and reclassifying are permissioned, comment-bearing
lifecycle moves that leave an immutable ``core.LifecycleEvent``, and every gate
below lives in :meth:`Incident.transition_to` (RG-INC-08). It is the one place
that binds the web stepper, the DRF mixin and MCP at once : ``lifecycle_to_json``
drops ``form_class`` / ``allowed_roles`` / ``allowed_users`` by design and
``get_lifecycle()`` prefers the seeded ``LifecycleDefinition`` row, so a gate
declared on the transition is green in an in-memory unit test and silently dead
on every migrated database.
"""

from django.apps import apps
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.db import models, transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy
from simple_history.models import HistoricalRecords

from context.constants import Criticality
from context.models.base import ScopedModel
from core.lifecycle import LifecycleError
from incidents.constants import (
    BREACH_STATES,
    EVIDENCE_STATES,
    INCIDENT_STATES,
    NOTIFICATION_STATES,
    REFERENCE_PREFIXES,
    REVIEW_STATES,
    DetectionSource,
    TimelineEntryKind,
    TimelineEntrySource,
    TrafficLightProtocol,
)
from risks.constants import ThreatCategory


def _step(code, states, lifecycle):
    """Resolve a step code **by name** against the single source of truth.

    Reading the codes back out of ``incidents/constants.py`` (RG-INC-37) means
    a rename there raises at import time instead of silently disabling one of
    the gates below. A dead gate on an incident closure is exactly the class of
    failure this module exists to prevent.
    """
    if code not in {declared for declared, *_flags in states}:
        raise ImproperlyConfigured(
            f"'{code}' is not a step of the {lifecycle} lifecycle."
        )
    return code


def _incident_step(code):
    return _step(code, INCIDENT_STATES, "incident")


STEP_DRAFT = _incident_step("draft")
STEP_DETECTED = _incident_step("detected")
STEP_TRIAGED = _incident_step("triaged")
STEP_INVESTIGATING = _incident_step("investigating")
STEP_CONTAINED = _incident_step("contained")
STEP_ERADICATED = _incident_step("eradicated")
STEP_RECOVERED = _incident_step("recovered")
STEP_POST_INCIDENT_REVIEW = _incident_step("post_incident_review")
STEP_CLOSED = _incident_step("closed")
STEP_RECLASSIFIED = _incident_step("reclassified")
STEP_ARCHIVED = _incident_step("archived")

# Steps of the *children*' lifecycles the closure gate reads. Resolved the same
# way, so this file never carries a literal for another entity's state either.
EVIDENCE_STEP_COLLECTED = _step("collected", EVIDENCE_STATES, "incident_evidence")
NOTIFICATION_STEP_DRAFT = _step("draft", NOTIFICATION_STATES, "incident_notification")
NOTIFICATION_STEP_ASSESSED = _step(
    "assessed", NOTIFICATION_STATES, "incident_notification"
)
REVIEW_STEP_SCHEDULED = _step("scheduled", REVIEW_STATES, "post_incident_review")
REVIEW_STEP_APPROVED = _step("approved", REVIEW_STATES, "post_incident_review")
REVIEW_STEP_EFFECTIVENESS_VERIFIED = _step(
    "effectiveness_verified", REVIEW_STATES, "post_incident_review"
)
BREACH_STEP_UNDER_QUALIFICATION = _step(
    "under_qualification", BREACH_STATES, "personal_data_breach"
)

#: An obligation is "undecided" exactly while it sits in one of these two steps :
#: the ``decision`` column mirrors the step and is written by the same
#: transition, so the step is the half of the pair that ``incidents/constants.py``
#: guarantees (RG-INC-37).
NOTIFICATION_UNDECIDED_STEPS = (NOTIFICATION_STEP_DRAFT, NOTIFICATION_STEP_ASSESSED)

#: Which phase stamp each step owns. Write-once (RG-INC-12) : the override
#: stamps a blank field and never rewrites a set one, and only the matching
#: reopen edge clears it.
PHASE_STAMPS = {
    STEP_DETECTED: "declared_at",
    STEP_TRIAGED: "triaged_at",
    STEP_CONTAINED: "contained_at",
    STEP_ERADICATED: "eradicated_at",
    STEP_RECOVERED: "recovered_at",
    STEP_CLOSED: "closed_at",
}

#: ``Criticality`` is declared least to most severe, so its declaration order
#: **is** the scale. Ranking is needed to answer "was the severity raised",
#: which is the trigger that re-runs obligation generation and can start a
#: 24-hour NIS2 clock that did not exist an hour earlier.
_SEVERITY_ORDER = list(Criticality.values)


def _severity_rank(value):
    """Position of a severity on the shared scale, or ``-1`` when unset."""
    try:
        return _SEVERITY_ORDER.index(value)
    except ValueError:
        return -1


def _model(name):
    """Resolve a sibling model by label rather than by import.

    Every cross-file reference in this app goes through the app registry or a
    string reference, so no import cycle can form between the module's models.
    """
    return apps.get_model("incidents", name)


class Incident(ScopedModel):
    """One information security incident (ISO/IEC 27001:2022 A.5.26).

    Reached either by promoting a :class:`~incidents.models.security_event.SecurityEvent`
    through its A.5.25 assessment, or by a direct declaration recorded with a
    detection source and a named declarer. It carries the impact picture, the
    process clock stamps every ISO/IEC 27035 KPI is computed from, the legal
    awareness anchor every statutory deadline derives from, and the blast-radius
    links into the asset, supplier, site, activity, risk and compliance
    registers.

    ``workflow_perm_namespace`` is deliberately **not** overridden : the derived
    ``incidents.incident`` already spells the permission feature.
    """

    REFERENCE_PREFIX = REFERENCE_PREFIXES["Incident"]
    LIFECYCLE_NAME = "incident"

    # --- Identity and narrative -------------------------------------------

    title = models.CharField(_("Title"), max_length=255)
    summary = models.TextField(
        _("Summary"),
        blank=True,
        default="",
        help_text=_(
            "One-paragraph executive summary : what the management review and "
            "any external statement are drafted from."
        ),
    )
    description = models.TextField(_("Description"), blank=True, default="")
    category = models.CharField(
        _("Category"),
        max_length=30,
        choices=ThreatCategory.choices,
        default=ThreatCategory.OTHER,
        db_index=True,
        help_text=_(
            "Reuses the threat taxonomy verbatim : an incident is a threat that "
            "materialised, and a parallel taxonomy would drift within one "
            "release and break the incident -> threat -> risk chain."
        ),
    )
    severity = models.CharField(
        pgettext_lazy("incident", "Severity"),
        max_length=20,
        choices=Criticality.choices,
        default=Criticality.MEDIUM,
        db_index=True,
        help_text=_(
            "Interpreted through the response plan's classification scale. The "
            "scale assets and suppliers already share is reused, so no parallel "
            "severity enum exists."
        ),
    )
    initial_severity = models.CharField(
        _("Initial severity"),
        max_length=20,
        choices=Criticality.choices,
        blank=True,
        default="",
        help_text=_(
            "Severity as fixed at triage. Write-once, so later severity drift "
            "is auditable by comparing two columns instead of by reading a "
            "history diff."
        ),
    )
    detection_source = models.CharField(
        pgettext_lazy("incident", "Detection source"),
        max_length=30,
        choices=DetectionSource.choices,
        default=DetectionSource.OTHER,
        help_text=_("Copied from the promoting event, when there was one."),
    )
    is_exercise = models.BooleanField(
        _("Exercise"),
        default=False,
        db_index=True,
        help_text=_(
            "Simulation or tabletop run through the real process : identical "
            "lifecycle and identical gates, excluded from every KPI and report, "
            "and never instantiating a regulatory notification."
        ),
    )
    tlp = models.CharField(
        _("TLP"),
        max_length=20,
        choices=TrafficLightProtocol.choices,
        default=TrafficLightProtocol.AMBER,
        help_text=_("Handling caveat for the incident file and its evidence."),
    )

    # --- Impact picture ----------------------------------------------------

    confidentiality_impact = models.BooleanField(
        _("Confidentiality impacted"),
        default=False,
        help_text=_(
            "Mirrors the risk register's impact flags so incident and risk "
            "impact read the same way in reports."
        ),
    )
    integrity_impact = models.BooleanField(_("Integrity impacted"), default=False)
    availability_impact = models.BooleanField(_("Availability impacted"), default=False)
    personal_data_involved = models.BooleanField(
        _("Personal data involved"),
        default=False,
        db_index=True,
        help_text=_(
            "Personal data was, or may have been, affected. Forces the GDPR "
            "Art. 33(1) obligation at triage whatever the plan configures, and "
            "opens the breach qualification."
        ),
    )

    # --- The two clocks ----------------------------------------------------

    occurred_at = models.DateTimeField(
        _("Occurred at"),
        null=True,
        blank=True,
        help_text=_("Best estimate of when the incident began."),
    )
    detected_at = models.DateTimeField(
        _("Detected at"),
        db_index=True,
        help_text=_(
            "Technical detection : the base of mean-time-to-detect. This is "
            "**not** the legal clock."
        ),
    )
    awareness_at = models.DateTimeField(
        _("Awareness at"),
        null=True,
        blank=True,
        db_index=True,
        help_text=_(
            "The legal clock anchor (GDPR Art. 33(1), NIS2 Art. 23). Defaults "
            "to the detection timestamp and must never precede it. Every "
            "statutory deadline in the module derives from this field."
        ),
    )
    awareness_justification = models.TextField(
        _("Awareness justification"),
        blank=True,
        default="",
        help_text=_(
            "Why legal awareness postdates technical detection : an alert unread "
            "over a weekend, a supplier notification arriving late. Defensible, "
            "but only when written down at the time."
        ),
    )

    # --- Phase stamps (written by the lifecycle only, RG-INC-12) -----------

    declared_at = models.DateTimeField(
        _("Declared at"),
        null=True,
        blank=True,
        help_text=_("Stamped by the declaration transition; never edited by hand."),
    )
    triaged_at = models.DateTimeField(
        _("Triaged at"),
        null=True,
        blank=True,
        help_text=_("Stamped when the A.5.25 assessment and decision completed."),
    )
    contained_at = models.DateTimeField(_("Contained at"), null=True, blank=True)
    eradicated_at = models.DateTimeField(_("Eradicated at"), null=True, blank=True)
    recovered_at = models.DateTimeField(_("Recovered at"), null=True, blank=True)
    closed_at = models.DateTimeField(_("Closed at"), null=True, blank=True)

    # --- Measured impact ---------------------------------------------------

    outage_duration = models.DurationField(
        _("Outage duration"),
        null=True,
        blank=True,
        help_text=_(
            "Measured service interruption. Reported beside each affected "
            "asset's declared objectives verbatim : the register states both "
            "and declines to conclude a breach."
        ),
    )
    estimated_cost = models.DecimalField(
        _("Estimated cost"),
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )
    no_obligation_justification = models.TextField(
        _("No-obligation justification"),
        blank=True,
        default="",
        help_text=_(
            "Why nothing is owed to anyone. Mandatory when triage produced no "
            "notification obligation at all : a missing regime configuration "
            "must never read as compliance on a green dashboard."
        ),
    )

    # --- NIS2 significance and qualification -------------------------------
    #
    # Three-state booleans throughout : `None` means "not determined yet", and
    # it is deliberately not the same answer as `False`. A null verdict blocks
    # the filings that must state one.

    is_significant = models.BooleanField(
        _("Significant incident"),
        null=True,
        default=None,
        help_text=_(
            "NIS2 Art. 23(3) significance verdict, deliberately separate from "
            "severity : the two are different judgements."
        ),
    )
    significance_determined_at = models.DateTimeField(
        _("Significance determined at"),
        null=True,
        blank=True,
        help_text=_("Usable as a statutory clock anchor in its own right."),
    )
    significance_justification = models.TextField(
        _("Significance justification"), blank=True, default=""
    )
    cross_border_impact = models.BooleanField(
        _("Cross-border impact"),
        null=True,
        default=None,
        help_text=_(
            "Whether entities or users in more than one Member State are "
            "affected. Not the same concept as GDPR cross-border processing : "
            "an incident with no personal data at all can still be cross-border "
            "for NIS2."
        ),
    )
    cross_border_justification = models.TextField(
        _("Cross-border justification"), blank=True, default=""
    )
    suspected_malicious = models.BooleanField(
        _("Suspected malicious act"),
        null=True,
        default=None,
        help_text=_(
            "NIS2 Art. 23(4)(a) requires the 24-hour early warning to state "
            "this, so the obligation cannot be completed while it is unknown."
        ),
    )
    suspected_malicious_justification = models.TextField(
        _("Malicious-act justification"), blank=True, default=""
    )

    # --- People and provenance ---------------------------------------------

    response_plan = models.ForeignKey(
        "incidents.IncidentResponsePlan",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="incidents",
        verbose_name=_("Response plan"),
        help_text=_(
            "The procedure version this incident was handled under. PROTECT is "
            "what makes a two-year-old incident file readable at audit time."
        ),
    )
    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reported_incidents",
        verbose_name=_("Reporter"),
    )
    incident_manager = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="managed_incidents",
        verbose_name=_("Incident manager"),
        help_text=_("The single accountable responder (A.5.24). Required at triage."),
    )
    parent_incident = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="child_incidents",
        verbose_name=_("Parent incident"),
        help_text=_("Major incident composed of sub-incidents, or merge target."),
    )
    origin_supplier = models.ForeignKey(
        "assets.Supplier",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="originated_incidents",
        verbose_name=_("Origin supplier"),
        help_text=_(
            "The third party whose breach or outage caused this. A sub-processor "
            "is itself a supplier row, so nth-party origin needs no extra field."
        ),
    )

    # --- Blast radius ------------------------------------------------------

    affected_suppliers = models.ManyToManyField(
        "assets.Supplier",
        blank=True,
        related_name="incidents",
        verbose_name=_("Affected suppliers"),
        help_text=_(
            "Suppliers impacted or notified downstream. The causal direction is "
            "kept apart from the origin supplier because NIS2, DORA and GDPR "
            "Art. 28 reporting depend on it."
        ),
    )
    affected_essential_assets = models.ManyToManyField(
        "assets.EssentialAsset",
        blank=True,
        related_name="incidents",
        verbose_name=_("Affected essential assets"),
    )
    affected_support_assets = models.ManyToManyField(
        "assets.SupportAsset",
        blank=True,
        related_name="incidents",
        verbose_name=_("Affected support assets"),
    )
    affected_sites = models.ManyToManyField(
        "context.Site",
        blank=True,
        related_name="incidents",
        verbose_name=_("Affected sites"),
    )
    affected_activities = models.ManyToManyField(
        "context.Activity",
        blank=True,
        related_name="incidents",
        verbose_name=_("Affected activities"),
        help_text=_("For a halted business activity with no named asset."),
    )
    threats = models.ManyToManyField(
        "risks.Threat",
        blank=True,
        related_name="incidents",
        verbose_name=_("Threats"),
        help_text=_("The threat that materialised."),
    )
    exploited_vulnerabilities = models.ManyToManyField(
        "risks.Vulnerability",
        blank=True,
        related_name="incidents",
        verbose_name=_("Exploited vulnerabilities"),
    )
    realised_risks = models.ManyToManyField(
        "risks.Risk",
        blank=True,
        related_name="incidents",
        verbose_name=_("Realised risks"),
        help_text=_("Which registered risks actually materialised."),
    )
    linked_requirements = models.ManyToManyField(
        "compliance.Requirement",
        blank=True,
        related_name="linked_incidents",
        verbose_name=_("Linked requirements"),
        help_text=_("The controls in play."),
    )

    history = HistoricalRecords()

    class Meta(ScopedModel.Meta):
        verbose_name = pgettext_lazy("incident", "Incident")
        verbose_name_plural = pgettext_lazy("incident", "Incidents")
        ordering = ["-detected_at"]
        indexes = [
            models.Index(fields=["workflow_state", "severity"]),
            models.Index(fields=["severity", "detected_at"]),
            models.Index(fields=["awareness_at"]),
        ]
        constraints = [
            # Detection before occurrence is incoherent, and the register is
            # only worth what its chronology is worth.
            models.CheckConstraint(
                condition=(
                    models.Q(occurred_at__isnull=True)
                    | models.Q(detected_at__gte=models.F("occurred_at"))
                ),
                name="incident_detected_after_occurred",
            ),
        ]

    def __str__(self):
        return f"{self.reference} : {self.title}"

    # --- Loaded-value tracking ---------------------------------------------

    @classmethod
    def from_db(cls, db, field_names, values, *args, **kwargs):
        """Remember the stored severity and personal-data flag.

        Both drive a side effect on the **change** rather than on the value :
        a severity raise re-runs obligation generation, and setting the
        personal-data flag opens the GDPR qualification. Comparing against the
        loaded value is what keeps those from firing on every unrelated save.

        The trailing ``*args`` / ``**kwargs`` are not decoration : Django has
        added arguments to this hook before (``fetch_mode`` most recently), and
        a fixed signature turns a routine dependency bump into a TypeError on
        every single row load. Forward whatever we are handed.
        """
        instance = super().from_db(db, field_names, values, *args, **kwargs)
        instance._loaded_severity = instance.severity
        instance._loaded_personal_data_involved = instance.personal_data_involved
        return instance

    # --- Read-only display helpers (API / assistant output) ----------------

    @property
    def response_plan_name(self):
        """Name of the procedure version the incident was handled under."""
        return self.response_plan.name if self.response_plan_id else ""

    @property
    def reporter_name(self):
        """Who reported it (read-only output)."""
        return self.reporter.display_name if self.reporter_id else ""

    @property
    def incident_manager_name(self):
        """The accountable responder (read-only output)."""
        return self.incident_manager.display_name if self.incident_manager_id else ""

    @property
    def origin_supplier_name(self):
        """The third party whose failure caused this (read-only output)."""
        return self.origin_supplier.name if self.origin_supplier_id else ""

    @property
    def parent_incident_reference(self):
        """Reference of the major incident this one is part of."""
        return self.parent_incident.reference if self.parent_incident_id else ""

    @property
    def awareness_gap(self):
        """``awareness_at - detected_at``, or None while either is unknown.

        The quantity the justification has to account for, derived once here
        rather than recomputed by each surface.
        """
        if self.awareness_at is None or self.detected_at is None:
            return None
        return self.awareness_at - self.detected_at

    @property
    def time_to_contain(self):
        """``contained_at - detected_at`` : the A.5.26 containment KPI."""
        if self.contained_at is None or self.detected_at is None:
            return None
        return self.contained_at - self.detected_at

    @property
    def time_to_recover(self):
        """``recovered_at - detected_at`` : the restoration KPI."""
        if self.recovered_at is None or self.detected_at is None:
            return None
        return self.recovered_at - self.detected_at

    @property
    def severity_raised_since_triage(self):
        """Whether severity now exceeds the value fixed at triage."""
        if not self.initial_severity:
            return False
        return _severity_rank(self.severity) > _severity_rank(self.initial_severity)

    # --- Validation --------------------------------------------------------

    def clean(self):
        """Coherence the two clocks and the NIS2 verdicts cannot be read without."""
        super().clean()
        errors = {}
        if self.detected_at and self.occurred_at and self.detected_at < self.occurred_at:
            errors["detected_at"] = _("An incident cannot be detected before it began.")
        if self.awareness_at and self.detected_at:
            if self.awareness_at < self.detected_at:
                errors["awareness_at"] = _(
                    "Becoming legally aware before the technical detection that "
                    "produced the record is incoherent."
                )
            elif (
                self.awareness_at > self.detected_at
                and not self.awareness_justification.strip()
            ):
                errors["awareness_justification"] = _(
                    "A gap between detection and legal awareness must be "
                    "justified in writing, at the time."
                )
        if (
            self.cross_border_impact is not None
            and not self.cross_border_justification.strip()
        ):
            errors["cross_border_justification"] = _(
                "A cross-border verdict must state its reasoning."
            )
        if (
            self.suspected_malicious is not None
            and not self.suspected_malicious_justification.strip()
        ):
            errors["suspected_malicious_justification"] = _(
                "A malicious-act verdict must state its reasoning."
            )
        if errors:
            raise ValidationError(errors)

    # --- Persistence -------------------------------------------------------

    def save(self, *args, **kwargs):
        """Back-fill the legal anchor, then run the change-driven side effects.

        The common case is correct with no operator action : a blank
        ``awareness_at`` means the organisation became aware when it detected,
        which is true far more often than not, and the operator only has to act
        on the case where it is not.
        """
        adding = self._state.adding
        if self.awareness_at is None:
            self.awareness_at = self.detected_at
        severity_raised = (
            not adding
            and _severity_rank(self.severity)
            > _severity_rank(getattr(self, "_loaded_severity", self.severity))
        )
        personal_data_flipped_on = (
            not adding
            and self.personal_data_involved
            and not getattr(self, "_loaded_personal_data_involved", True)
        )

        super().save(*args, **kwargs)

        self._loaded_severity = self.severity
        self._loaded_personal_data_involved = self.personal_data_involved

        if not adding:
            # RG-INC-31 : the review can never drift out of scope alignment
            # with the incident it reviews.
            self._sync_review_scopes()
        if severity_raised and self.triaged_at is not None:
            # A raise can cross a template's severity floor and start a 24-hour
            # NIS2 clock that did not exist an hour earlier. Generation is
            # idempotent, so re-running it disturbs no decision already taken.
            self.generate_notification_obligations()
        if personal_data_flipped_on:
            self.ensure_personal_data_breach()

    def _sync_review_scopes(self):
        """Re-align the post-incident review's scopes with the incident's."""
        review = _model("PostIncidentReview").objects.filter(incident=self).first()
        if review is None:
            return
        scope_ids = set(self.scopes.values_list("id", flat=True))
        if scope_ids != set(review.scopes.values_list("id", flat=True)):
            review.scopes.set(scope_ids)

    # --- Lifecycle ---------------------------------------------------------

    def transition_to(self, target, user=None, comment=None, *, enforce_permission=False, save=True):
        """Apply the A.5.26 gates, stamp the phase clocks, then move.

        The whole body runs in one transaction, so a refusal raised **after**
        the child rows were generated - the obligation-coverage gate is
        evaluated at the end of triage, which is the only point at which the
        obligation count is knowable - rolls the entire triage back, generated
        obligations included.

        Gates raise :class:`core.lifecycle.LifecycleError` rather than a bare
        ``ValidationError`` : that is the exception the generic stepper endpoint
        (``core/workflow_views.py``) catches and turns into a message, and the
        DRF mixin catches both, so it is the one that behaves correctly on all
        three write surfaces.
        """
        from core.lifecycle import validate_transition

        lifecycle = self.get_lifecycle()
        current = self.workflow_state or lifecycle.initial_step.code
        # Legality and the mandatory-comment rule first, so an illegal move is
        # reported as such rather than as a domain refusal.
        transition = validate_transition(
            lifecycle, current, target, instance=self, user=user,
            comment=comment, enforce_permission=False,
        )
        with transaction.atomic():
            self._check_transition_gates(current, target)
            self._stamp_transition(current, target)
            result = super().transition_to(
                target, user, comment=comment,
                enforce_permission=enforce_permission, save=save,
            )
            self._apply_side_effects(current, target, user)
            self._append_lifecycle_timeline_entry(transition, user, comment)
        return result

    def _check_transition_gates(self, current, target):
        """Refuse the moves the incident file must never record."""
        # G-01 : an incident is declared against a detection, and the legal
        # clock can never precede it.
        if target == STEP_DETECTED:
            if self.detected_at is None:
                raise LifecycleError(
                    str(_("Declaring an incident requires its detection timestamp."))
                )
            if self.awareness_at and self.awareness_at < self.detected_at:
                raise LifecycleError(
                    str(_(
                        "The legal awareness timestamp cannot precede the "
                        "technical detection."
                    ))
                )

        # G-02 (RG-INC-11) : the A.5.25 assessment is not complete until the
        # classification and the accountable responder are fixed.
        if target == STEP_TRIAGED and current == STEP_DETECTED:
            if not self.severity or not self.category:
                raise LifecycleError(
                    str(_("Triage requires a severity and a category."))
                )
            if self.incident_manager_id is None:
                raise LifecycleError(
                    str(_("Triage requires a named incident manager."))
                )
            if (
                self.awareness_at
                and self.detected_at
                and self.awareness_at > self.detected_at
                and not self.awareness_justification.strip()
            ):
                raise LifecycleError(
                    str(_(
                        "A legal awareness postdating the detection must be "
                        "justified before triage can complete."
                    ))
                )

        # G-04 (RG-INC-15) : you cannot un-declare something you have already
        # told a regulator about. The `detected -> reclassified` edge predates
        # obligation generation, so no check is possible or needed there.
        if target == STEP_RECLASSIFIED and current in (STEP_TRIAGED, STEP_INVESTIGATING):
            if (
                _model("IncidentNotification")
                .objects.filter(incident=self, sent_at__isnull=False)
                .exists()
            ):
                raise LifecycleError(
                    str(_(
                        "This incident cannot be reclassified : a regulatory "
                        "notification has already been filed."
                    ))
                )

        # G-05 (RG-INC-14) : the learning phase, the obligation register and
        # the evidence register are all closure gates, not side panels.
        if target == STEP_CLOSED:
            self._check_closure_gate()

        # G-07 : the restore bookend is the one path that could walk a declared
        # incident back into the single deletable step, so it is refused for
        # any row the immutable ledger shows has ever left `draft` (RG-INC-07).
        if current == STEP_ARCHIVED and target == STEP_DRAFT and self._has_left_draft():
            raise LifecycleError(
                str(_(
                    "An incident that was declared cannot be restored to draft."
                ))
            )

    def _check_closure_gate(self):
        """The three conditions an incident closure rests on (RG-INC-14)."""
        review = _model("PostIncidentReview").objects.filter(incident=self).first()
        if review is None or review.workflow_state not in (
            REVIEW_STEP_APPROVED,
            REVIEW_STEP_EFFECTIVENESS_VERIFIED,
        ):
            raise LifecycleError(
                str(_(
                    "Closing an incident requires an approved post-incident "
                    "review (A.5.27)."
                ))
            )
        if (
            _model("IncidentNotification")
            .objects.filter(
                incident=self, workflow_state__in=NOTIFICATION_UNDECIDED_STEPS
            )
            .exists()
        ):
            raise LifecycleError(
                str(_(
                    "Closing an incident requires a decision on every "
                    "regulatory notification obligation."
                ))
            )
        if (
            _model("IncidentEvidence")
            .objects.filter(incident=self, workflow_state=EVIDENCE_STEP_COLLECTED)
            .exists()
        ):
            raise LifecycleError(
                str(_(
                    "Closing an incident requires every collected evidence item "
                    "to have been secured or otherwise disposed of."
                ))
            )

    def _stamp_transition(self, current, target):
        """Write the phase clocks the lifecycle owns (RG-INC-12, G-08).

        Write-once in both directions : a stamp already set is never rewritten
        (so a re-triage or a re-closure keeps the original date), and a stamp is
        cleared only by its own reopen edge.
        """
        if target == STEP_DETECTED and self.awareness_at is None:
            self.awareness_at = self.detected_at
        if target == STEP_TRIAGED and not self.initial_severity:
            # Copied once, so severity drift after triage is a difference
            # between two columns rather than a history diff to read.
            self.initial_severity = self.severity

        field = PHASE_STAMPS.get(target)
        if field and getattr(self, field) is None:
            setattr(self, field, timezone.now())

        if current == STEP_RECOVERED and target == STEP_INVESTIGATING:
            self.recovered_at = None
        if current == STEP_CLOSED and target == STEP_INVESTIGATING:
            # RG-INC-16 : the original closure stays in the lifecycle history;
            # only the stamp is cleared, and re-closure re-stamps it.
            self.closed_at = None

    def _apply_side_effects(self, current, target, user):
        """The child rows and the plan evidence a transition is responsible for."""
        if target == STEP_TRIAGED and current == STEP_DETECTED:
            self.generate_notification_obligations(user)
            # RG-INC-18 : the qualification is opened by the flag, and is never
            # closed by clearing it.
            self.ensure_personal_data_breach(user)
            # G-03 (RG-INC-19), evaluated last, inside the same transaction :
            # this is the only point at which the obligation count is knowable,
            # and a refusal here rolls the whole triage back.
            self._check_obligation_coverage()
        if target == STEP_POST_INCIDENT_REVIEW:
            self.ensure_post_incident_review(user)
        if target == STEP_CLOSED and self.is_exercise and self.response_plan_id:
            # RG-INC-17 : the A.5.24 plan-testing evidence is maintained here
            # and nowhere else. Hand-editing it would make it worthless.
            self.response_plan.record_exercise(self.closed_at)

    def _check_obligation_coverage(self):
        """Refuse a triage that owes nothing to anyone without saying why.

        An exercise is exempt : it produces zero obligations by construction
        (RG-INC-17), so an unqualified gate would force a legal justification
        for owing nothing on every single drill, training the wrong reflex and
        polluting the exact field an auditor reads.
        """
        if self.is_exercise or self.personal_data_involved:
            return
        if _model("IncidentNotification").objects.filter(incident=self).exists():
            return
        if self.no_obligation_justification.strip():
            return
        raise LifecycleError(
            str(_(
                "This triage produced no notification obligation : record why "
                "nothing is owed to any authority, controller or counterparty."
            ))
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

    def _append_lifecycle_timeline_entry(self, transition, user, comment):
        """Append the chronology line every transition owes (RG-INC-09).

        The narrative and the state machine can then never diverge : they are
        written in the same transaction. A transition with no actor at all (a
        migration, a fixture) appends nothing, because the chronology's author
        is a required, PROTECT-ed attribution and an unattributed line in the
        account a regulator reads is worse than none : the move is still
        recorded, with its null actor, in the immutable ``LifecycleEvent``.
        """
        if user is None:
            return
        _model("IncidentTimelineEntry").objects.create(
            incident=self,
            occurred_at=timezone.now(),
            entry_type=TimelineEntryKind.SYSTEM,
            summary=str(transition.label)[:500],
            detail=(comment or "").strip(),
            source=TimelineEntrySource.LIFECYCLE,
            author=user,
        )

    # --- Auto-created children ---------------------------------------------
    #
    # Nothing in this module is ever *created in* a domain step. Assigning the
    # step at insert would stick, because `_ensure_initial_step()` only snaps a
    # blank or unknown value, but it would leave no `core.LifecycleEvent`, so
    # the child would have no recorded entry into its register - which is
    # precisely the audit trail the design exists to produce. Every path below
    # therefore saves in `draft` and then transitions.
    #
    # `enforce_permission=False` is correct on all three : the permission was
    # already checked on the parent transition the user actually performed, and
    # the child row is a consequence of it, not a separate act.

    def generate_notification_obligations(self, user=None):
        """Instantiate the regulatory obligations this incident raises.

        Idempotent, and re-run at every point where the answer can change : at
        triage, and on a severity raise that crosses a template's floor. An
        exercise generates nothing at all (RG-INC-17) : filing a real
        notification for a drill is an incident in its own right.
        """
        if self.is_exercise:
            return []
        return _model("IncidentNotification").generate_obligations(self, user)

    @transaction.atomic
    def ensure_personal_data_breach(self, user=None):
        """Open the GDPR qualification when personal data is involved.

        Creating it is driven by the flag; **closing** it never is. A breach is
        ruled out through the qualification's own ``not_a_breach`` transition -
        by a named person, with a mandatory comment, at a stamped time - because
        "we considered it and concluded it was not a personal data breach" is
        exactly the sentence a supervisory authority asks to see.
        """
        if not self.personal_data_involved:
            return None
        Breach = _model("PersonalDataBreach")
        breach = Breach.objects.filter(incident=self).first()
        if breach is not None:
            return breach
        breach = Breach(incident=self, created_by=user)
        breach.save()
        breach.transition_to(
            BREACH_STEP_UNDER_QUALIFICATION, user, enforce_permission=False
        )
        return breach

    @transaction.atomic
    def ensure_post_incident_review(self, user=None):
        """Open the A.5.27 review, exactly one per incident (RG-INC-31)."""
        Review = _model("PostIncidentReview")
        review = Review.objects.filter(incident=self).first()
        if review is not None:
            return review
        review = Review(incident=self, created_by=user)
        review.save()
        review.scopes.set(self.scopes.all())
        review.transition_to(REVIEW_STEP_SCHEDULED, user, enforce_permission=False)
        return review

    @classmethod
    @transaction.atomic
    def declare(cls, user=None, **fields):
        """Create an incident and declare it in one act.

        The entry point for a direct declaration, an import or the seed : a row
        left in ``draft`` is not yet on the register, and one written straight
        into ``detected`` has no recorded declaration.
        """
        incident = cls(created_by=user, **fields)
        incident.save()
        incident.transition_to(STEP_DETECTED, user, enforce_permission=False)
        return incident
