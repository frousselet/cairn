# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""The A.6.8 register of reported security events and weaknesses.

Every reported occurrence enters here, and **it is not an incident until a
named person decides it is**. That single constraint is the whole point of the
entity : it turns the promotion decision into an auditable, permissioned,
comment-bearing lifecycle transition instead of an implicit data entry, and it
is the only way to answer the question every ISO 27001 auditor asks - *show me
the events you decided were not incidents, and who decided*. A design that
jumps straight to an incident table with a status column cannot answer it at
all, because the events that were correctly dismissed leave no trace.
"""

from django.apps import apps
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.db import models, transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy
from simple_history.models import HistoricalRecords

from context.models.base import ScopedModel
from core.lifecycle import LifecycleError
from incidents.constants import (
    SECURITY_EVENT_STATES,
    DetectionSource,
    EventTriageDecision,
    REFERENCE_PREFIXES,
    SecurityEventClass,
)
from risks.constants import ThreatCategory

# The ``security_event`` step codes, resolved **by name** against the single
# source of truth (RG-INC-37). Reading them back out of the constants means a
# rename in ``incidents/constants.py`` raises at import time instead of
# silently disabling one of the gates below : a dead gate on an A.5.25
# assessment is exactly the kind of failure this module exists to prevent.
_STEP_CODES = {code for code, *_flags in SECURITY_EVENT_STATES}


def _step(code):
    if code not in _STEP_CODES:
        raise ImproperlyConfigured(
            f"'{code}' is not a step of the security_event lifecycle."
        )
    return code


STEP_DRAFT = _step("draft")
STEP_REPORTED = _step("reported")
STEP_UNDER_ASSESSMENT = _step("under_assessment")
STEP_CONFIRMED_INCIDENT = _step("confirmed_incident")
STEP_CONFIRMED_WEAKNESS = _step("confirmed_weakness")
STEP_DISCARDED = _step("discarded")
STEP_ARCHIVED = _step("archived")

# Which triage verdict each terminal assessment step carries. The column
# mirrors the step so filters, list facets and MCP enums never have to read the
# lifecycle, and the pair is written in one place so the two can never drift.
_DECISION_BY_STEP = {
    STEP_CONFIRMED_INCIDENT: EventTriageDecision.INCIDENT,
    STEP_CONFIRMED_WEAKNESS: EventTriageDecision.WEAKNESS,
    STEP_DISCARDED: EventTriageDecision.NO_ACTION,
}


def _domain_entry_step(instance):
    """The first non-terminal step a freshly created row is moved into.

    Nothing in this module is ever *created* in a domain step : a row is saved
    in ``draft`` and then transitioned, so the move leaves a
    ``core.LifecycleEvent`` behind. The target is read off the target model's
    own lifecycle rather than hardcoded, so this file never has to know another
    entity's step codes.
    """
    lifecycle = instance.get_lifecycle()
    initial = lifecycle.initial_step.code
    for transition in lifecycle.transitions_from(initial):
        step = lifecycle.step(transition.target)
        if not step.is_archived:
            return transition.target
    raise LifecycleError(
        f"Lifecycle '{lifecycle.name}' has no domain step reachable from "
        f"'{initial}'."
    )


class SecurityEvent(ScopedModel):
    """One reported information security event or weakness (A.6.8 / A.5.25).

    An **event** is an identified occurrence indicating a possible breach of
    policy, a failure of controls or a previously unknown security-relevant
    situation. A **weakness** is a reported flaw that has *not* been exploited.
    An **incident** is neither : it is what a named person decides one or more
    events amount to, and it lives in its own entity, reachable only through
    the ``under_assessment -> confirmed_incident`` transition.
    """

    REFERENCE_PREFIX = REFERENCE_PREFIXES["SecurityEvent"]
    LIFECYCLE_NAME = "security_event"

    title = models.CharField(_("Title"), max_length=255)
    description = models.TextField(
        _("Description"),
        blank=True,
        default="",
        help_text=_(
            "What was observed, in the reporter's own words. Never rewritten "
            "on promotion : the original report is part of the A.6.8 record."
        ),
    )
    event_class = models.CharField(
        _("Class"),
        max_length=20,
        choices=SecurityEventClass.choices,
        default=SecurityEventClass.EVENT,
        db_index=True,
        help_text=_("Governs which promotion targets are legal."),
    )
    category = models.CharField(
        _("Category"),
        max_length=30,
        choices=ThreatCategory.choices,
        blank=True,
        default="",
        help_text=_("Provisional classification, refined on promotion."),
    )
    detection_source = models.CharField(
        pgettext_lazy("incident", "Detection source"),
        max_length=30,
        choices=DetectionSource.choices,
        default=DetectionSource.OTHER,
    )
    source_reference = models.CharField(
        _("Source reference"),
        max_length=255,
        blank=True,
        default="",
        help_text=_("SIEM alert id, ticket number or CERT bulletin reference."),
    )
    occurred_at = models.DateTimeField(
        _("Occurred at"),
        null=True,
        blank=True,
        help_text=_("Best estimate of when the occurrence started."),
    )
    detected_at = models.DateTimeField(
        _("Detected at"),
        db_index=True,
        help_text=_("When it was detected. Base of the mean-time-to-detect KPI."),
    )
    reported_at = models.DateTimeField(
        _("Reported at"),
        db_index=True,
        help_text=_(
            "When it reached the incident response function. The gap with the "
            "detection timestamp is the A.6.8 reporting delay."
        ),
    )
    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reported_security_events",
        verbose_name=_("Reporter"),
    )
    reporter_label = models.CharField(
        _("Reporter (external)"),
        max_length=255,
        blank=True,
        default="",
        help_text=_(
            "Identity of an external or non-user reporter : a customer, a "
            "researcher, an authority."
        ),
    )
    is_anonymous = models.BooleanField(
        _("Anonymous report"),
        default=False,
        help_text=_("Reported through the anonymous channel A.6.8 requires."),
    )
    assessed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assessed_security_events",
        verbose_name=_("Assessed by"),
        help_text=_("Person who performed the A.5.25 assessment."),
    )
    assessed_at = models.DateTimeField(
        _("Assessment started at"),
        null=True,
        blank=True,
        help_text=_("Stamped by the lifecycle transition; never edited by hand."),
    )
    assessment_notes = models.TextField(
        pgettext_lazy("incident", "Assessment notes"),
        blank=True,
        default="",
        help_text=_(
            "The reasoning behind the decision. An undocumented assessment is "
            "not an assessment."
        ),
    )
    triage_decision = models.CharField(
        pgettext_lazy("incident", "Triage decision"),
        max_length=20,
        choices=EventTriageDecision.choices,
        # Blank means the assessment has not concluded. There is deliberately
        # no "pending" member : an undecided event is one with no verdict, not
        # one carrying a verdict that says nothing.
        default="",
        blank=True,
        db_index=True,
        help_text=_("Set by the lifecycle transition, never written directly."),
    )

    incident = models.ForeignKey(
        "incidents.Incident",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="source_events",
        verbose_name=pgettext_lazy("incident", "Incident"),
        help_text=_(
            "The incident this event was promoted into. Several events may "
            "feed one incident; an event promotes into at most one."
        ),
    )
    vulnerability = models.ForeignKey(
        "risks.Vulnerability",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="source_events",
        verbose_name=_("Vulnerability"),
        help_text=_(
            "The vulnerability a confirmed weakness was promoted into. There "
            "is no parallel weakness register."
        ),
    )
    duplicate_of = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="duplicates",
        verbose_name=_("Duplicate of"),
        help_text=_(
            "The earlier event this one repeats. Also the link used when a "
            "previously reported weakness is later exploited."
        ),
    )
    reported_by_supplier = models.ForeignKey(
        "assets.Supplier",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reported_security_events",
        verbose_name=_("Reported by supplier"),
        help_text=_("Third-party notification (NIS2 supply chain, GDPR Art. 33(2))."),
    )
    affected_support_assets = models.ManyToManyField(
        "assets.SupportAsset",
        blank=True,
        related_name="security_events",
        verbose_name=_("Affected support assets"),
    )
    affected_essential_assets = models.ManyToManyField(
        "assets.EssentialAsset",
        blank=True,
        related_name="security_events",
        verbose_name=_("Affected essential assets"),
    )
    affected_sites = models.ManyToManyField(
        "context.Site",
        blank=True,
        related_name="security_events",
        verbose_name=_("Affected sites"),
    )

    history = HistoricalRecords()

    class Meta(ScopedModel.Meta):
        verbose_name = pgettext_lazy("incident", "Security event")
        verbose_name_plural = pgettext_lazy("incident", "Security events")
        ordering = ["-reported_at"]
        constraints = [
            # The database half of RG-INC-02 : the transition gate refuses the
            # promotion and the constraint refuses the row, so neither a raw
            # SQL insert nor a ``QuerySet.update()`` can leave a "promoted"
            # event pointing at nothing.
            models.CheckConstraint(
                condition=(
                    ~models.Q(triage_decision=EventTriageDecision.INCIDENT)
                    | models.Q(incident__isnull=False)
                ),
                name="event_incident_decision_requires_incident",
            ),
            models.CheckConstraint(
                condition=(
                    ~models.Q(triage_decision=EventTriageDecision.WEAKNESS)
                    | models.Q(vulnerability__isnull=False)
                ),
                name="event_weakness_decision_requires_vulnerability",
            ),
            # The database, not a form, is what guarantees the anonymous
            # channel is actually anonymous.
            models.CheckConstraint(
                condition=(
                    models.Q(is_anonymous=False)
                    | (models.Q(reporter__isnull=True) & models.Q(reporter_label=""))
                ),
                name="event_anonymous_has_no_reporter",
            ),
        ]

    def __str__(self):
        return f"{self.reference} : {self.title}"

    # --- Permissions -------------------------------------------------------

    @property
    def workflow_perm_namespace(self):
        """The permission feature is ``event``, not the model name.

        The derived ``incidents.securityevent`` matches no feature in
        ``PERMISSION_REGISTRY``, and every transition would then be refused for
        everyone holding the real codenames.
        """
        return "incidents.event"

    # --- Read-only display helpers (API / assistant output) ----------------

    @property
    def reporter_name(self):
        """Who reported it, or an empty string on the anonymous channel."""
        if self.is_anonymous:
            return ""
        if self.reporter_id:
            return self.reporter.display_name
        return self.reporter_label

    @property
    def assessed_by_name(self):
        """Who performed the A.5.25 assessment (read-only output)."""
        return self.assessed_by.display_name if self.assessed_by_id else ""

    @property
    def incident_reference(self):
        """Reference of the incident this event was promoted into."""
        return self.incident.reference if self.incident_id else ""

    @property
    def vulnerability_reference(self):
        """Reference of the vulnerability a confirmed weakness fed."""
        return self.vulnerability.reference if self.vulnerability_id else ""

    @property
    def duplicate_of_reference(self):
        """Reference of the earlier event this one repeats."""
        return self.duplicate_of.reference if self.duplicate_of_id else ""

    @property
    def reported_by_supplier_name(self):
        """Name of the notifying third party (read-only output)."""
        return (
            self.reported_by_supplier.name if self.reported_by_supplier_id else ""
        )

    @property
    def reporting_delay(self):
        """``reported_at - detected_at`` : the A.6.8 reporting delay, or None.

        This is the measurable quantity the control's "as quickly as possible"
        is assessed against, so it is derived here once rather than recomputed
        by each surface.
        """
        if self.reported_at is None or self.detected_at is None:
            return None
        return self.reported_at - self.detected_at

    @property
    def reporting_delay_hours(self):
        """The reporting delay in hours, or None when either stamp is missing."""
        delay = self.reporting_delay
        return None if delay is None else delay.total_seconds() / 3600

    # --- Validation --------------------------------------------------------

    def clean(self):
        """Field-level coherence the register cannot be trusted without."""
        super().clean()
        errors = {}
        if self.reported_at and self.detected_at and self.reported_at < self.detected_at:
            errors["reported_at"] = _(
                "An event cannot be reported before it was detected."
            )
        if self.detected_at and self.occurred_at and self.detected_at < self.occurred_at:
            errors["detected_at"] = _(
                "An event cannot be detected before it occurred."
            )
        if self.is_anonymous and (self.reporter_id or self.reporter_label):
            errors["is_anonymous"] = _(
                "An anonymous report carries no reporter identity."
            )
        if errors:
            raise ValidationError(errors)

    # --- Lifecycle ---------------------------------------------------------

    def transition_to(self, target, user=None, comment=None, *, enforce_permission=False, save=True):
        """Apply the A.5.25 gates, then perform the transition.

        Every gate lives here rather than on the ``Transition`` (RG-INC-08) :
        ``lifecycle_to_json()`` omits ``form_class`` / ``allowed_roles`` /
        ``allowed_users`` by design and ``get_lifecycle()`` prefers the
        ``post_migrate``-seeded row over the code default, so a gate declared
        there is green in an in-memory unit test and silently dead on every
        migrated database. The web, API and MCP write surfaces all funnel
        through this method, so it is the one place that binds the three.
        """
        from core.lifecycle import validate_transition

        lifecycle = self.get_lifecycle()
        current = self.workflow_state or lifecycle.initial_step.code
        # Legality and the mandatory-comment rule first, so an illegal move is
        # reported as such instead of as a domain refusal.
        validate_transition(
            lifecycle, current, target, instance=self, user=user,
            comment=comment, enforce_permission=False,
        )
        self._apply_transition_gates(current, target, comment)
        self._stamp_transition(current, target, user)
        return super().transition_to(
            target, user, comment=comment,
            enforce_permission=enforce_permission, save=save,
        )

    def _apply_transition_gates(self, current, target, comment):
        """Refuse the A.5.25 moves the register must never record."""
        # G-05, first : the mandatory discard comment is the assessment, so it
        # is written into the register itself and not only into the immutable
        # ledger. Persisting it here also satisfies G-01 below.
        if target == STEP_DISCARDED and comment and comment.strip():
            self._append_assessment_note(comment)

        if current == STEP_UNDER_ASSESSMENT:
            # G-01 : an undocumented assessment is not an assessment, by any
            # route including MCP.
            if not self.assessment_notes.strip():
                raise LifecycleError(
                    str(_(
                        "Leaving the assessment requires written assessment "
                        "notes."
                    ))
                )
            # G-06 : a single event never carries two verdicts.
            expected = _DECISION_BY_STEP.get(target)
            decided = bool(self.triage_decision)
            if expected and decided and self.triage_decision != expected:
                raise LifecycleError(
                    str(_("This event already carries a triage decision."))
                )

        if target == STEP_CONFIRMED_INCIDENT:
            # G-03 : a weakness that has actually been exploited is a NEW event
            # of class ``event`` linked back through ``duplicate_of``, so the
            # original reporting history stays intact and the exploitation's
            # reporting delay is measured from its own detection.
            if self.event_class == SecurityEventClass.WEAKNESS:
                raise LifecycleError(
                    str(_(
                        "A weakness is never promoted to an incident : report "
                        "the exploitation as a new event."
                    ))
                )
            # G-02 : the incident must exist before the event claims it does.
            if self.incident_id is None:
                raise LifecycleError(
                    str(_(
                        "Promotion requires the incident it promotes into. Use "
                        "the promotion action rather than the bare transition."
                    ))
                )

        # G-04 : same shape against the existing vulnerability register.
        if target == STEP_CONFIRMED_WEAKNESS and self.vulnerability_id is None:
            raise LifecycleError(
                str(_(
                    "Recording a weakness requires the vulnerability it is "
                    "recorded as. Use the promotion action rather than the "
                    "bare transition."
                ))
            )

        # The restore bookend is gated so archiving can never become a way of
        # deleting an A.6.8 record : ``draft`` and ``reported`` are deletable
        # steps, and an event that ever reached the register must not be able
        # to walk back into one of them.
        if current == STEP_ARCHIVED and target == STEP_DRAFT and self._has_left_draft():
            raise LifecycleError(
                str(_(
                    "An event that entered the register cannot be restored to "
                    "draft."
                ))
            )

    def _stamp_transition(self, current, target, user):
        """Write the columns the lifecycle owns : stamps and the verdict."""
        if target == STEP_UNDER_ASSESSMENT:
            # Write-once (RG-INC-12) : reopening a discarded event does not
            # rewrite when the assessment began, and the reopening actor is
            # recorded on the LifecycleEvent.
            if self.assessed_at is None:
                self.assessed_at = timezone.now()
            if self.assessed_by_id is None and user is not None:
                self.assessed_by = user
        if current == STEP_DISCARDED and target == STEP_UNDER_ASSESSMENT:
            # Reopening clears the verdict; the original discard stays in the
            # lifecycle history.
            self.triage_decision = ""
        decision = _DECISION_BY_STEP.get(target)
        if decision:
            self.triage_decision = decision

    def _append_assessment_note(self, comment):
        """Fold a mandatory transition comment into the register itself."""
        note = comment.strip()
        existing = self.assessment_notes.strip()
        if not existing:
            self.assessment_notes = note
        elif note not in existing:
            self.assessment_notes = f"{existing}\n\n{note}"

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

    # --- Promotion ---------------------------------------------------------

    @transaction.atomic
    def promote_to_incident(self, user, comment, *, enforce_permission=True, **incident_overrides):
        """Create the incident and promote this event into it, atomically.

        One act, not a sequence a user can abandon halfway. The incident is
        **created in draft and then transitioned** rather than inserted in a
        domain step : assigning the step at insert would stick, but it would
        leave no ``core.LifecycleEvent``, so the incident would have no
        recorded declaration - which is the evidence the register exists to
        hold.

        ``enforce_permission`` is deliberately False on the incident's own
        entry transition : the permission was checked on the event transition
        the user actually performed, and the incident's declaration is a
        consequence of it, not a separate act.
        """
        Incident = apps.get_model("incidents", "Incident")

        fields = {
            "title": self.title,
            "description": self.description,
            "detection_source": self.detection_source,
            "occurred_at": self.occurred_at,
            "detected_at": self.detected_at,
            "reporter": self.reporter,
            "created_by": user,
        }
        if self.category:
            fields["category"] = self.category
        fields.update(incident_overrides)

        incident = Incident(**fields)
        incident.save()
        # RG-INC-38 : the incident inherits the event's tenancy, and every
        # child row of the incident inherits it from there.
        incident.scopes.set(self.scopes.all())
        incident.affected_support_assets.set(self.affected_support_assets.all())
        incident.affected_essential_assets.set(self.affected_essential_assets.all())
        incident.affected_sites.set(self.affected_sites.all())
        incident.transition_to(
            _domain_entry_step(incident), user, enforce_permission=False,
        )

        self.incident = incident
        self.transition_to(
            STEP_CONFIRMED_INCIDENT, user, comment=comment,
            enforce_permission=enforce_permission,
        )
        return incident

    @transaction.atomic
    def promote_to_vulnerability(self, user, comment, *, enforce_permission=True, **vulnerability_overrides):
        """Create the vulnerability and record this event as a weakness.

        A confirmed weakness is promoted into the **existing** vulnerability
        register (A.8.8), never into a parallel weakness table : two weakness
        registers would be two answers to *what do we know is broken*. Same
        create-then-transition shape as :meth:`promote_to_incident`, for the
        same reason.
        """
        Vulnerability = apps.get_model("risks", "Vulnerability")

        fields = {
            "name": self.title,
            "description": self.description,
            "created_by": user,
        }
        fields.update(vulnerability_overrides)

        vulnerability = Vulnerability(**fields)
        vulnerability.save()
        vulnerability.scopes.set(self.scopes.all())
        vulnerability.affected_assets.set(self.affected_support_assets.all())
        vulnerability.transition_to(
            _domain_entry_step(vulnerability), user, enforce_permission=False,
        )

        self.vulnerability = vulnerability
        self.transition_to(
            STEP_CONFIRMED_WEAKNESS, user, comment=comment,
            enforce_permission=enforce_permission,
        )
        return vulnerability

    @classmethod
    @transaction.atomic
    def report(cls, user=None, *, enforce_permission=False, **fields):
        """Create an event and move it into the register in one act.

        The entry point for bulk imports, inbound integrations and the seed :
        no row in this module is ever *created in* a domain step, because that
        would leave the event with no recorded entry into the A.6.8 register.
        Permission defaults to unenforced here because these callers have
        already been authorised at their own surface (an import, an inbound
        integration, a seed run).
        """
        event = cls(created_by=user, **fields)
        event.save()
        event.transition_to(
            STEP_REPORTED, user, enforce_permission=enforce_permission,
        )
        return event
