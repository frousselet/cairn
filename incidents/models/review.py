# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""The A.5.27 learning record, and the gate an incident closes through.

Two properties make this entity worth its own lifecycle rather than a handful
of fields on the incident :

**It is a gate, not a report.** ISO/IEC 27001:2022 A.5.27 asks that knowledge
gained from incidents be used to strengthen controls. That sentence is
trivially satisfiable on paper and almost never satisfied in practice, because
the natural end of an incident is the moment service is restored. Cairn answers
it with a structural constraint : the review is created automatically when the
incident enters its review phase, and ``Incident.transition_to()`` refuses
closure while the review is unapproved (RG-INC-14). There is no surface on
which a closed incident can exist without one.

**It answers clause 10.2 d) and f), which nothing in the platform did.** An
action plan reaching a done step proves an action was *implemented*; it says
nothing about whether it *worked*. The ``effectiveness_verified`` step, its
verdict and its propagation onto every nonconformity the review raised are that
missing record.

Every gate below lives in :meth:`PostIncidentReview.transition_to` (RG-INC-08),
because that is the one place binding the web stepper, the DRF mixin and MCP at
once : ``lifecycle_to_json`` drops ``form_class`` / ``allowed_roles`` /
``allowed_users`` by design and ``get_lifecycle()`` prefers the seeded
``LifecycleDefinition`` row, so a gate declared on the transition is green in an
in-memory unit test and silently dead on every migrated database.
"""

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.db import models, transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

from compliance.constants import EffectivenessVerdict, FindingSource
from context.constants import Criticality
from context.models.base import ScopedModel
from core.lifecycle import LifecycleError, LifecycleProtectedError, reportable
from incidents.constants import (
    INCIDENT_STATES,
    REFERENCE_PREFIXES,
    REVIEW_STATES,
    RootCauseMethod,
)


def _step(code, states, lifecycle):
    """Resolve a step code **by name** against the single source of truth.

    Reading the codes back out of ``incidents/constants.py`` (RG-INC-37) means
    a rename there raises at import time instead of silently disabling one of
    the gates below. A dead gate on this entity lets an incident close with no
    A.5.27 record at all, which is the exact failure the module exists to
    prevent.
    """
    if code not in {declared for declared, *_flags in states}:
        raise ImproperlyConfigured(
            f"'{code}' is not a step of the {lifecycle} lifecycle."
        )
    return code


def _review_step(code):
    return _step(code, REVIEW_STATES, "post_incident_review")


STEP_DRAFT = _review_step("draft")
STEP_SCHEDULED = _review_step("scheduled")
STEP_IN_PROGRESS = _review_step("in_progress")
STEP_SUBMITTED = _review_step("submitted")
STEP_APPROVED = _review_step("approved")
STEP_EFFECTIVENESS_VERIFIED = _review_step("effectiveness_verified")
STEP_CANCELLED = _review_step("cancelled")
STEP_ARCHIVED = _review_step("archived")

#: The parent's step from which a review may actually be held (gate GP-01).
INCIDENT_STEP_POST_INCIDENT_REVIEW = _step(
    "post_incident_review", INCIDENT_STATES, "incident"
)

#: The incident lifecycle in declaration order, which **is** its operational
#: order. Gate GP-01 needs "at ``post_incident_review`` or later", and comparing
#: positions in the declared list keeps the comparison free of any state literal
#: this file would otherwise own a second copy of (RG-INC-37).
INCIDENT_STEP_ORDER = [declared for declared, *_flags in INCIDENT_STATES]


class PostIncidentReview(ScopedModel):
    """The learning record of one incident : ISO/IEC 27001:2022 A.5.27.

    It holds the determined root cause with the method used to determine it,
    the detection gap, the controls that failed, and the outward links that
    make an incident change something : the nonconformities it raised, the
    corrective action plans it produced, the risks to reassess, the weaknesses
    to register, the controls to strengthen and the ISMS changes it forced.

    Every one of those targets already existed in the platform. Nothing here is
    a parallel register : an incident that produces a nonconformity produces the
    *same kind* of nonconformity an audit produces, lands in the same
    ``compliance.Finding`` register, is scored the same way and reaches the same
    management review.

    The entity carries **no title of its own** : exactly one review exists per
    incident (RG-INC-31), so it is identified by its reference and its incident
    everywhere it is rendered.
    """

    REFERENCE_PREFIX = REFERENCE_PREFIXES["PostIncidentReview"]
    LIFECYCLE_NAME = "post_incident_review"

    incident = models.OneToOneField(
        "incidents.Incident",
        on_delete=models.PROTECT,
        related_name="post_incident_review",
        verbose_name=_("Incident"),
        help_text=_("The incident this review draws its lessons from."),
    )
    response_plan = models.ForeignKey(
        "incidents.IncidentResponsePlan",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="post_incident_reviews",
        verbose_name=_("Response plan"),
        help_text=_(
            "The procedure this review concludes must be updated. Copied from "
            "the incident, and editable : the review may conclude that a "
            "different plan is the one at fault."
        ),
    )

    # --- Planning ----------------------------------------------------------

    scheduled_date = models.DateField(
        _("Scheduled date"),
        null=True,
        blank=True,
        help_text=_("When the review is planned."),
    )
    held_at = models.DateTimeField(
        # Write-once, stamped by the `scheduled -> in_progress` transition only
        # (RG-INC-12). Excluded from every form, read-only in every serializer,
        # absent from every MCP writable-field list.
        _("Held at"),
        null=True,
        blank=True,
        help_text=_("When the review actually took place."),
    )
    facilitator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="facilitated_post_incident_reviews",
        verbose_name=_("Facilitator"),
        help_text=_("Who ran the review, and who is recorded as having raised "
                    "the nonconformities it produced."),
    )
    participants = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name="post_incident_reviews",
        verbose_name=_("Participants"),
    )

    # --- Analysis ----------------------------------------------------------

    root_cause_method = models.CharField(
        _("Root cause method"),
        max_length=32,
        choices=RootCauseMethod.choices,
        default=RootCauseMethod.FIVE_WHYS,
        help_text=_(
            "Naming the technique is what separates a determined root cause "
            "from a plausible guess."
        ),
    )
    root_cause = models.TextField(
        _("Root cause"),
        blank=True,
        default="",
        help_text=_(
            "The determined cause of the nonconformity : not the symptom, not "
            "the remediation. Required to submit the review (clause 10.2 b))."
        ),
    )
    contributing_factors = models.TextField(
        _("Contributing factors"), blank=True, default=""
    )
    detection_gap = models.TextField(
        _("Detection gap"),
        blank=True,
        default="",
        help_text=_(
            "Why it was not detected earlier. What makes the mean-time-to-detect "
            "indicator actionable rather than decorative (A.8.16)."
        ),
    )
    containment_assessment = models.TextField(
        _("Containment assessment"),
        blank=True,
        default="",
        help_text=_(
            "Whether the response itself was adequate and timely : the verdict "
            "on the A.5.26 handling, distinct from the verdict on the controls."
        ),
    )
    what_went_well = models.TextField(_("What went well"), blank=True, default="")
    what_failed = models.TextField(_("What failed"), blank=True, default="")
    recurrence_likelihood = models.CharField(
        # Reuses the scale severity, assets and suppliers already share. A
        # parallel enum here would make two four-point scales that mean the same
        # thing and drift apart.
        _("Recurrence likelihood"),
        max_length=20,
        choices=Criticality.choices,
        blank=True,
        default="",
        help_text=_("Clause 10.2 b) 3) : whether similar nonconformities exist, "
                    "or could occur."),
    )
    similar_incidents_checked = models.BooleanField(
        _("Similar incidents checked"),
        default=False,
        help_text=_(
            "Confirms that clause 10.2 b) 3) was actually performed. A boolean "
            "is defensible here precisely because it is gated : it cannot be "
            "left unchecked and still produce an approved review."
        ),
    )

    # --- Consequences ------------------------------------------------------

    risk_reassessment_required = models.BooleanField(
        _("Risk reassessment required"),
        default=False,
        help_text=_("The incident invalidates a registered risk evaluation."),
    )
    response_plan_update_required = models.BooleanField(
        _("Response plan update required"),
        default=False,
        help_text=_("A.5.27 feeding back into the A.5.24 procedure."),
    )
    training_required = models.BooleanField(
        _("Training required"),
        default=False,
        help_text=_("Awareness or training action needed (A.6.3)."),
    )

    # --- Effectiveness : the clause 10.2 d) / f) record ---------------------

    effectiveness_review_date = models.DateField(
        _("Effectiveness review date"),
        null=True,
        blank=True,
        help_text=_(
            "When the corrective actions' effectiveness will be verified. "
            "Required to approve the review, so the clause 10.2 d) verification "
            "lands on the calendar instead of in someone's memory."
        ),
    )
    effectiveness_reviewed_at = models.DateTimeField(
        # Write-once, stamped by the `approved -> effectiveness_verified`
        # transition only (RG-INC-12).
        _("Effectiveness reviewed at"),
        null=True,
        blank=True,
    )
    effectiveness_reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="verified_post_incident_reviews",
        verbose_name=_("Effectiveness reviewed by"),
        help_text=_(
            "Who verified that the corrective action worked. Self-verification "
            "is permitted and rendered beside the facilitator, so a review "
            "verified by the person who ran it reads as exactly that."
        ),
    )
    effectiveness_verdict = models.CharField(
        # Same enum as `compliance.Finding.effectiveness_verdict`, declared once
        # in `compliance/constants.py`, so the propagation below is a straight
        # copy and the two fields can never drift apart.
        _("Effectiveness verdict"),
        max_length=32,
        choices=EffectivenessVerdict.choices,
        blank=True,
        default="",
        help_text=_("Clause 10.2 f) : the documented result of the corrective "
                    "action. Required to verify effectiveness."),
    )
    effectiveness_notes = models.TextField(
        _("Effectiveness notes"),
        blank=True,
        default="",
        help_text=_("The evidence supporting the verdict : what was measured, "
                    "tested or observed, and when."),
    )

    # --- Outward links : what the review must actually change --------------
    #
    # A review whose only output is prose is a story. These are what make it a
    # control. Four of them declare the reverse accessor `post_incident_reviews`
    # on four different targets, which is legal because the targets differ :
    # never write `obj.post_incident_reviews` in shared code without naming the
    # model it hangs off.

    raised_findings = models.ManyToManyField(
        "compliance.Finding",
        blank=True,
        related_name="post_incident_reviews",
        verbose_name=_("Raised findings"),
        help_text=_(
            "The nonconformities this review raised, in the one clause 10.2 "
            "register (source = incident, no fabricated audit)."
        ),
    )
    corrective_action_plans = models.ManyToManyField(
        "compliance.ComplianceActionPlan",
        blank=True,
        related_name="post_incident_reviews",
        verbose_name=_("Corrective action plans"),
        help_text=_("Clause 10.2 c) : corrective actions, on the existing "
                    "action-plan lifecycle (RG-INC-35)."),
    )
    failed_controls = models.ManyToManyField(
        "compliance.Requirement",
        blank=True,
        related_name="failing_post_incident_reviews",
        verbose_name=_("Failed controls"),
        help_text=_("The controls that were in place and did not hold."),
    )
    controls_to_strengthen = models.ManyToManyField(
        # Deliberately a second M2M on the same target rather than one list with
        # a role column : *what broke* and *what we are doing about it* are two
        # different questions an auditor reads side by side, and a single list
        # would make the review look complete while saying nothing.
        "compliance.Requirement",
        blank=True,
        related_name="improving_post_incident_reviews",
        verbose_name=_("Controls to strengthen"),
    )
    identified_risks = models.ManyToManyField(
        "risks.Risk",
        blank=True,
        related_name="post_incident_reviews",
        verbose_name=_("Identified risks"),
        help_text=_("Risks the incident revealed or invalidated."),
    )
    identified_vulnerabilities = models.ManyToManyField(
        "risks.Vulnerability",
        blank=True,
        related_name="post_incident_reviews",
        verbose_name=_("Identified vulnerabilities"),
        help_text=_("Weaknesses to register in the existing vulnerability "
                    "register, never a parallel table."),
    )
    isms_changes = models.ManyToManyField(
        # `reports.IsmsChange` (that exact spelling) is the clause 9.3.3
        # management-review output. It cannot exist outside a management review,
        # so this review *links* one and never creates it : the change is tabled
        # at the next management review and linked back from here.
        "reports.IsmsChange",
        blank=True,
        related_name="post_incident_reviews",
        verbose_name=_("ISMS changes"),
        help_text=_("Clause 10.2 e) : the changes to the ISMS this incident "
                    "forced."),
    )

    history = HistoricalRecords()

    class Meta(ScopedModel.Meta):
        verbose_name = _("Post-incident review")
        verbose_name_plural = _("Post-incident reviews")
        ordering = ["-scheduled_date"]
        indexes = [
            # `workflow_state` already carries `db_index` from `BaseModel`, so
            # only the two dates and the pair the "open clause 10.2 d)
            # obligation" list filters on are declared here.
            models.Index(fields=["scheduled_date"]),
            models.Index(fields=["effectiveness_review_date"]),
            models.Index(fields=["workflow_state", "effectiveness_review_date"]),
        ]

    def __str__(self):
        if self.incident_id:
            return f"{self.reference} - {self.incident.reference}"
        return self.reference

    @property
    def workflow_perm_namespace(self):
        """Gate this entity on the ``incidents.review`` feature.

        The derived ``incidents.postincidentreview`` matches no feature in
        ``PERMISSION_REGISTRY``, so every lifecycle permission check would
        silently evaluate against a codename nobody holds.
        """
        return "incidents.review"

    # --- Read-only display helpers (API / assistant output) ----------------

    @property
    def incident_reference(self):
        """Reference of the incident under review."""
        return self.incident.reference if self.incident_id else ""

    @property
    def incident_title(self):
        """Title of the incident under review."""
        return self.incident.title if self.incident_id else ""

    @property
    def response_plan_name(self):
        """Name of the procedure this review concludes must be updated."""
        return self.response_plan.name if self.response_plan_id else ""

    @property
    def facilitator_name(self):
        """Who ran the review (read-only output)."""
        return self.facilitator.display_name if self.facilitator_id else ""

    @property
    def effectiveness_reviewed_by_name(self):
        """Who verified the corrective action worked (read-only output)."""
        return (
            self.effectiveness_reviewed_by.display_name
            if self.effectiveness_reviewed_by_id
            else ""
        )

    @property
    def is_effectiveness_overdue(self):
        """Whether an approved review has passed its verification date.

        The single most useful thing the review list shows : an open clause
        10.2 d) obligation nobody has answered.
        """
        return (
            self.workflow_state == STEP_APPROVED
            and self.effectiveness_review_date is not None
            and self.effectiveness_review_date < timezone.localdate()
        )

    # --- Validation --------------------------------------------------------

    def clean(self):
        """Coherence the effectiveness record cannot be read without."""
        super().clean()
        errors = {}
        if self.effectiveness_verdict and self.effectiveness_reviewed_by_id is None:
            errors["effectiveness_reviewed_by"] = _(
                "An effectiveness verdict must name who reached it."
            )
        if (
            self.effectiveness_review_date
            and self.scheduled_date
            and self.effectiveness_review_date < self.scheduled_date
        ):
            errors["effectiveness_review_date"] = _(
                "Effectiveness cannot be verified before the review that "
                "decides the corrective actions is held."
            )
        if errors:
            raise ValidationError(errors)

    # --- Lifecycle ---------------------------------------------------------

    def transition_to(
        self, target, user=None, comment=None, *, enforce_permission=False, save=True
    ):
        """Apply the A.5.27 gates, stamp the write-once clocks, then move.

        The whole body runs in one transaction, so a refusal raised after the
        linked nonconformities were normalised rolls that normalisation back
        with the move that triggered it.

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
        validate_transition(
            lifecycle,
            current,
            target,
            instance=self,
            user=user,
            comment=comment,
            enforce_permission=False,
        )
        with transaction.atomic():
            self._check_transition_gates(current, target)
            self._stamp_transition(current, target)
            result = super().transition_to(
                target,
                user,
                comment=comment,
                enforce_permission=enforce_permission,
                save=save,
            )
            self._apply_side_effects(current, target, user)
        return result

    def _check_transition_gates(self, current, target):
        """Refuse the moves the A.5.27 record must never contain."""
        # GP-01 : holding a review for an incident still being contained is not
        # a review, it is a status meeting.
        if target == STEP_IN_PROGRESS and current == STEP_SCHEDULED:
            if not self._incident_reached_review_phase():
                raise LifecycleError(
                    str(_(
                        "The review cannot be held while the incident has not "
                        "reached its post-incident review phase."
                    ))
                )

        # GP-02 (RG-INC-32) : clause 10.2 b) and b) 3). A review submitted with
        # no determined cause is a chronology, and the register already holds
        # the chronology.
        if target == STEP_SUBMITTED:
            if not self.root_cause.strip():
                raise LifecycleError(
                    str(_(
                        "Submitting the review requires the determined root "
                        "cause (clause 10.2 b))."
                    ))
                )
            if not self.similar_incidents_checked:
                raise LifecycleError(
                    str(_(
                        "Submitting the review requires confirming that similar "
                        "incidents were checked for (clause 10.2 b) 3))."
                    ))
                )

        # GP-03 (RG-INC-32) : approving with no verification date scheduled is
        # how clause 10.2 d) is missed, so the gate refuses it rather than
        # trusting a reminder.
        if target == STEP_APPROVED and self.effectiveness_review_date is None:
            raise LifecycleError(
                str(_(
                    "Approving the review requires the date on which the "
                    "corrective actions' effectiveness will be verified."
                ))
            )

        # GP-04 (RG-INC-32) : clause 10.2 f) is a documented result, with an
        # author. Neither half is optional.
        if target == STEP_EFFECTIVENESS_VERIFIED:
            if not self.effectiveness_verdict:
                raise LifecycleError(
                    str(_(
                        "Verifying effectiveness requires a verdict on whether "
                        "the corrective action worked (clause 10.2 f))."
                    ))
                )
            if self.effectiveness_reviewed_by_id is None:
                raise LifecycleError(
                    str(_("Verifying effectiveness requires naming who verified it."))
                )

        # GP-05 : `draft` and `scheduled` are both deletable, so the restore
        # bookend is the one path that could walk an approved review back into a
        # deletable step and destroy the A.5.27 record an incident was closed
        # on. Refused for any row the immutable ledger shows has ever been
        # opened. Mirrors the incident's G-07.
        if current == STEP_ARCHIVED and target == STEP_DRAFT and self._has_left_draft():
            raise LifecycleError(
                str(_(
                    "A review that was opened cannot be restored to draft."
                ))
            )

        # GP-06 : a live incident must have a live review to reach closure, so
        # there is deliberately no path that leaves a closeable incident holding
        # a cancelled one. The OneToOne is PROTECT and RG-INC-31 allows exactly
        # one review per incident, so a cancelled review can never be replaced.
        if target == STEP_CANCELLED:
            if self.is_terminal_state:
                raise LifecycleError(
                    str(_("This review has already reached a terminal state."))
                )
            if not self._incident_is_terminal():
                raise LifecycleError(
                    str(_(
                        "A review can only be cancelled once its incident has "
                        "itself been reclassified or archived."
                    ))
                )

    def _stamp_transition(self, current, target):
        """Write the two clocks the lifecycle owns (RG-INC-12, GP-07).

        Write-once : a stamp already set is never rewritten, so a send-back and
        rework loop keeps the date the review was actually held, and no reopen
        edge on this lifecycle clears either one.
        """
        if target == STEP_IN_PROGRESS and current == STEP_SCHEDULED and self.held_at is None:
            self.held_at = timezone.now()
        if target == STEP_EFFECTIVENESS_VERIFIED and self.effectiveness_reviewed_at is None:
            self.effectiveness_reviewed_at = timezone.now()

    def _apply_side_effects(self, current, target, user):
        """Push the review's conclusions onto the rows that carry them."""
        if target in (STEP_SUBMITTED, STEP_APPROVED):
            # Run on both edges, so a nonconformity attached during a send-back
            # and rework loop is normalised too.
            self.normalise_raised_findings(user)
        if target == STEP_EFFECTIVENESS_VERIFIED:
            self.propagate_effectiveness_verdict()

    def _incident_reached_review_phase(self):
        """Whether the parent is at its review step or beyond (gate GP-01)."""
        try:
            return INCIDENT_STEP_ORDER.index(
                self.incident.workflow_state
            ) >= INCIDENT_STEP_ORDER.index(INCIDENT_STEP_POST_INCIDENT_REVIEW)
        except ValueError:
            # An incident parked on a step its lifecycle no longer declares is
            # not a state to hold a review from.
            return False

    def _incident_is_terminal(self):
        """Whether the parent incident has reached a terminal step.

        Read off the incident's own lifecycle rather than compared against step
        codes (RG-INC-37). The closed step is terminal too, but a closed
        incident's review is necessarily approved or verified, and neither of
        those steps has a cancel edge, so the wider test cannot admit the case
        gate GP-06 exists to refuse.
        """
        return bool(self.incident_id) and self.incident.is_terminal_state

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

    # --- The outward links, written by the lifecycle -----------------------

    @transaction.atomic
    def normalise_raised_findings(self, user=None):
        """Stamp every attached nonconformity as incident-born (RG-INC-34).

        Idempotent, and deliberately not a signal on the M2M : the review is
        what asserts that these rows are clause 10.2 entries arising from this
        incident, and it asserts it at the moment it is submitted for approval,
        not at the moment somebody ticks a picker.

        ``assessment`` is left null. Fabricating an audit to hang an incident's
        nonconformity off is exactly the practice the generalisation of
        ``compliance.Finding`` exists to end. ``assessor`` is only filled when
        blank, so an explicitly named author is never overwritten.
        """
        updated = []
        for finding in self.raised_findings.all():
            finding.source = FindingSource.INCIDENT
            finding.incident = self.incident
            if finding.assessor_id is None:
                finding.assessor = self.facilitator or user
            finding.save()
            updated.append(finding)
        return updated

    @transaction.atomic
    def propagate_effectiveness_verdict(self):
        """Copy the verdict onto every nonconformity this review raised.

        A **snapshot at this instant, not a live mirror**. The review's verdict
        is the aggregate judgement; a nonconformity whose individual verdict
        differs is edited on the finding itself afterwards, and the finding's
        own history records the divergence. Nothing re-writes a finding after
        this transition.

        RG-FND-06 is respected : a finding with no linked action plan in a
        reportable state is **skipped** rather than stamped, because a verdict
        about the effectiveness of nothing is not a record. The skipped rows are
        returned, and kept on the instance so the calling surface can report
        them.
        """
        stamped, skipped = [], []
        for finding in self.raised_findings.all():
            if not reportable(finding.action_plans.all()).exists():
                skipped.append(finding)
                continue
            finding.effectiveness_verdict = self.effectiveness_verdict
            finding.effectiveness_reviewed_at = self.effectiveness_reviewed_at
            finding.effectiveness_reviewed_by = self.effectiveness_reviewed_by
            finding.save()
            stamped.append(finding)
        self.effectiveness_propagation_skipped = skipped
        return stamped, skipped

    # --- Deletion ----------------------------------------------------------

    def delete(self, *args, **kwargs):
        """Refuse to strand an incident by deleting the review it must close on.

        ``BaseModel.delete()`` already refuses every step from ``in_progress``
        onward, so this override only bites on the two deletable steps, which
        exist so a review created by hand in error can be removed without an
        approver. Deleting an automatically created one would leave an incident
        that can never close (RG-INC-14) and can never obtain a second review
        (RG-INC-31, ``OneToOne``) : the row is the answer to a question the
        platform asked on the organisation's behalf, and deleting it destroys
        the evidence that the question was ever considered.
        """
        if self.is_deletable and not self._incident_is_terminal():
            raise LifecycleProtectedError(
                str(_(
                    "This review cannot be deleted while its incident is still "
                    "open : the incident could then never be closed."
                ))
            )
        return super().delete(*args, **kwargs)
