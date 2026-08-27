# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""The GDPR qualification of an incident, and its Art. 33(5) register entry.

One record answering three questions the incident file deliberately does not :
*is this a personal data breach at all*, *in what capacity were we processing*,
and *does it meet the Art. 34 high-risk threshold*. It then holds the
Art. 33(3)(a)-(d) content every filing is drafted from, and its ``documented``
step **is** the internal register entry Art. 33(5) requires the controller to
keep of every breach, notified or not.

It is a distinct entity, with a distinct lifecycle and a distinct approver - the
DPO - for two reasons a boolean on the incident cannot serve:

**The verdict must survive independently of the incident's operational state.**
An incident can be contained, recovered and closed long before the qualification
is settled, and a qualification can be reopened years later when a forensic
finding changes what was actually exfiltrated. Tying the verdict to the
incident's step would force one of those two truths to lie.

**``controller_role`` alone decides which obligations exist at all.** A
controller owes Art. 33(1) to the supervisory authority and may owe Art. 34(1)
to the data subjects. A processor owes **neither** : it owes Art. 33(2) to the
controller, and nothing else. Filing with the supervisory authority as a
processor is not a harmless excess of zeal - it discloses a client's breach on
that client's behalf, without the client's decision, and it may pre-empt or
contradict the controller's own filing. The role is therefore a generation
input, matched by ``ReportingObligationTemplate.controller_roles``, and
generation is re-run on confirmation precisely because that is the moment the
role becomes a settled fact rather than an assumption.

Every gate below lives in :meth:`PersonalDataBreach.transition_to` (RG-INC-08),
never on the ``Transition`` object : ``lifecycle_to_json`` drops ``form_class``
/ ``allowed_roles`` / ``allowed_users`` by design and ``get_lifecycle()``
prefers the ``post_migrate``-seeded ``LifecycleDefinition`` row, so a gate
declared that way is green in an in-memory unit test and silently dead on every
migrated database. The three write surfaces (the web stepper, the DRF mixin and
MCP) all funnel through ``BaseModel.transition_to()``, so the model override is
the one place that binds them at once.
"""

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.db import models, transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

from context.models.base import BaseModel
from core.lifecycle import LifecycleError
from incidents.constants import (
    BREACH_STATES,
    REFERENCE_PREFIXES,
    Art34Ground,
    ControllerRole,
)


def _breach_step(code):
    """Resolve a step code **by name** against the single source of truth.

    Reading the codes back out of ``incidents/constants.py`` (RG-INC-37) means a
    rename there raises at import time instead of silently disabling one of the
    gates below. A dead gate here lets a breach be confirmed with no Art. 34
    verdict, or lets a qualified record be walked back into a deletable step.
    """
    if code not in {declared for declared, *_flags in BREACH_STATES}:
        raise ImproperlyConfigured(
            f"'{code}' is not a step of the personal_data_breach lifecycle."
        )
    return code


STEP_DRAFT = _breach_step("draft")
STEP_UNDER_QUALIFICATION = _breach_step("under_qualification")
STEP_CONFIRMED = _breach_step("confirmed")
STEP_DOCUMENTED = _breach_step("documented")
STEP_NOT_A_BREACH = _breach_step("not_a_breach")
STEP_ARCHIVED = _breach_step("archived")

#: The GDPR Art. 33(3)(a)-(d) minimum content, in article order. Gate G-01 reads
#: this list rather than four inline conditions so the refusal message can name
#: the article letters the filing form asks for.
ARTICLE_33_3_FIELDS = ("nature", "dpo_contact", "likely_consequences", "measures_taken")


def _validate_string_list(value, label):
    """Validate a free ``JSONField`` list of category labels.

    ``JSONField`` rather than ``ArrayField`` is what lets ``core.settings_test``
    (SQLite in memory) run the module unchanged. These two lists carry the same
    free value shape as ``assets.EssentialAsset.personal_data_categories`` - so
    the two registers stay comparable and a breach can be pre-filled from the
    affected essential assets - which means there is no enum to check them
    against and only the shape can be enforced.
    """
    if value in (None, ""):
        return []
    if not isinstance(value, list):
        raise ValidationError({label: _("This value must be a list.")})
    if any(not isinstance(item, str) or not item.strip() for item in value):
        raise ValidationError({label: _("Each entry must be a non-empty label.")})
    return value


class PersonalDataBreach(BaseModel):
    """The GDPR qualification of one incident (Art. 33 and Art. 34).

    Created when the incident declares personal data, **saved then transitioned**
    into ``under_qualification`` so the opening of the qualification leaves a
    ``core.LifecycleEvent`` behind (RG-INC-18).

    **Clearing ``personal_data_involved`` never deletes this record.** A breach
    is ruled out through the ``not_a_breach`` transition : by a named person
    holding ``incidents.notification.approve``, with a mandatory comment, at a
    stamped time, leaving an immutable ledger row. Unchecking a box leaves
    nothing at all, and *"we considered it and concluded it was not a personal
    data breach"* is precisely the sentence a supervisory authority asks to see
    when it notices an incident involving personal data that was never notified.
    """

    REFERENCE_PREFIX = REFERENCE_PREFIXES["PersonalDataBreach"]
    LIFECYCLE_NAME = "personal_data_breach"

    # Scope is inherited from the incident, never held independently (RG-INC-38).
    # A qualification record that could be scoped differently from its incident
    # would be a way to make a breach visible to people the incident is not, and
    # re-scoping the incident would silently leave it behind. Declared on the
    # model rather than only on the views, so the generic workflow, history and
    # MCP surfaces enforce it too (see `core.scoping`). Not `optional` : the
    # incident is required, so there is no parentless row to keep visible.
    scope_parent_lookup = "incident__scopes"

    incident = models.OneToOneField(
        "incidents.Incident",
        on_delete=models.PROTECT,
        related_name="personal_data_breach",
        verbose_name=_("Incident"),
        help_text=_("The incident this record qualifies under the GDPR."),
    )

    # --- The verdict that decides which obligations exist ------------------

    controller_role = models.CharField(
        _("Controller role"),
        max_length=32,
        choices=ControllerRole.choices,
        default=ControllerRole.CONTROLLER,
        db_index=True,
        help_text=_(
            "The capacity the affected data was processed in. A controller owes "
            "Art. 33(1) to the supervisory authority; a processor owes "
            "Art. 33(2) to the controller and nothing else. The split is per "
            "incident, not per organisation."
        ),
    )
    controller_supplier = models.ForeignKey(
        "assets.Supplier",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notified_data_breaches",
        verbose_name=_("Controller notified"),
        help_text=_(
            "When the organisation acted as a processor, the controller it must "
            "notify under Art. 33(2) : a real supplier row, so the contract, "
            "the requirements and the review history are one click away."
        ),
    )
    lead_authority = models.ForeignKey(
        "incidents.ReportingAuthority",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="lead_breaches",
        verbose_name=_("Lead supervisory authority"),
        help_text=_(
            "The lead authority under Art. 56 (one-stop-shop). SET_NULL : a "
            "withdrawn determination must not destroy the breach record."
        ),
    )
    cross_border_eu = models.BooleanField(
        _("Cross-border processing"),
        default=False,
        help_text=_(
            "Cross-border processing within the meaning of Art. 4(23). "
            "Deliberately not the same field as the incident's operational "
            "cross-border impact, which exists for NIS2 incidents involving no "
            "personal data at all."
        ),
    )

    # --- Art. 33(3)(a) : nature, categories and volumes --------------------

    nature = models.TextField(
        _("Nature"),
        blank=True,
        default="",
        help_text=_("Nature of the breach, Art. 33(3)(a). Required to confirm."),
    )
    data_categories = models.JSONField(
        _("Data categories"),
        default=list,
        blank=True,
        help_text=_(
            "Categories of personal data concerned, Art. 33(3)(a). Same value "
            "shape as an essential asset's GDPR categories, so the two "
            "registers stay comparable."
        ),
    )
    special_categories = models.BooleanField(
        _("Special categories"),
        default=False,
        help_text=_(
            "Art. 9 data (health, biometrics, political opinions) is involved. A "
            "strong pointer towards high risk, and rendered as such : it never "
            "sets the Art. 34 verdict automatically, because that is a judgement "
            "and not a lookup."
        ),
    )
    data_subject_categories = models.JSONField(
        _("Data subject categories"),
        default=list,
        blank=True,
        help_text=_("Categories of data subjects concerned, Art. 33(3)(a)."),
    )
    approximate_data_subjects = models.PositiveIntegerField(
        _("Approximate data subjects"),
        null=True,
        blank=True,
        help_text=_("Approximate number of data subjects concerned, Art. 33(3)(a)."),
    )
    approximate_records = models.PositiveIntegerField(
        _("Approximate records"),
        null=True,
        blank=True,
        help_text=_("Approximate number of personal data records concerned."),
    )
    volume_is_estimate = models.BooleanField(
        _("Volumes are estimates"),
        default=True,
        help_text=_(
            "Defaulting to true is the correct default : a 72-hour filing "
            "normally contains an estimate, and Art. 33(4) explicitly allows "
            "the information to be provided in phases."
        ),
    )

    # --- Art. 33(3)(b) to (d) ----------------------------------------------

    dpo_contact = models.CharField(
        _("DPO contact"),
        max_length=255,
        blank=True,
        default="",
        help_text=_(
            "Name and contact details of the DPO or other contact point, "
            "Art. 33(3)(b). Required to confirm."
        ),
    )
    likely_consequences = models.TextField(
        _("Likely consequences"),
        blank=True,
        default="",
        help_text=_(
            "Likely consequences of the breach, Art. 33(3)(c). Required to "
            "confirm : a confirmed breach with empty consequences is a filing "
            "that cannot be drafted."
        ),
    )
    measures_taken = models.TextField(
        _("Measures taken"),
        blank=True,
        default="",
        help_text=_(
            "Measures taken or proposed, including those mitigating possible "
            "adverse effects, Art. 33(3)(d). Required to confirm."
        ),
    )

    # --- Art. 34 : the high-risk determination -----------------------------

    high_risk_to_rights = models.BooleanField(
        _("High risk to rights and freedoms"),
        null=True,
        default=None,
        db_index=True,
        help_text=_(
            "The Art. 34(1) determination. Three-state on purpose : null means "
            "not yet determined and is not a match for anything, and it is not "
            "the same answer as a recorded no. Must be answered to confirm."
        ),
    )
    high_risk_justification = models.TextField(
        _("High risk justification"),
        blank=True,
        default="",
        help_text=_(
            "Reasoning behind the Art. 34 determination, expected in both "
            "directions : a recorded no-high-risk with no reasoning is the "
            "weakest sentence in a breach file."
        ),
    )
    article_34_exemption = models.CharField(
        _("Article 34 exemption"),
        max_length=32,
        choices=Art34Ground.choices,
        default=Art34Ground.NONE,
        help_text=_(
            "The Art. 34(3) ground relied on, if any. Recorded, never assumed : "
            "the exemption is discharged through the obligation's own "
            "not-required decision, and never by suppressing the obligation."
        ),
    )
    article_34_exemption_justification = models.TextField(
        _("Article 34 exemption justification"),
        blank=True,
        default="",
        help_text=_("Written justification for not informing the data subjects. "
                    "Mandatory whenever a ground is claimed."),
    )

    # --- The Art. 33(5) register entry -------------------------------------

    register_entry_reference = models.CharField(
        _("Register entry reference"),
        max_length=100,
        blank=True,
        default="",
        help_text=_(
            "External reference, for organisations that also keep the "
            "Art. 33(5) register outside Cairn. Recording the pointer is what "
            "keeps the two registers reconcilable."
        ),
    )
    qualified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="qualified_data_breaches",
        verbose_name=_("Qualified by"),
        help_text=_("Who reached the verdict. Stamped by the transition."),
    )
    qualified_at = models.DateTimeField(
        # Write-once, stamped by the confirm or the rule-out transition only
        # (RG-INC-12, gate G-05). Excluded from every form, read-only in every
        # serializer, absent from every MCP writable-field list.
        _("Qualified at"),
        null=True,
        blank=True,
        help_text=_("When the verdict was reached. Never editable by hand."),
    )

    history = HistoricalRecords()

    class Meta(BaseModel.Meta):
        verbose_name = _("Personal data breach")
        verbose_name_plural = _("Personal data breaches")
        # The OneToOne supplies the one-record-per-incident uniqueness; no
        # additional constraint is needed.
        constraints = [
            # The database half of the Art. 34(3) rule : the transition gate
            # refuses the verdict and the constraint refuses the row, so neither
            # a raw SQL insert nor a `QuerySet.update()` can leave an exemption
            # asserted with no written justification.
            models.CheckConstraint(
                condition=(
                    models.Q(article_34_exemption=Art34Ground.NONE)
                    | ~models.Q(article_34_exemption_justification="")
                ),
                name="pdbr_exemption_has_justification",
            ),
        ]

    def __str__(self):
        if self.incident_id:
            return f"{self.reference} - {self.incident.reference}"
        return self.reference

    # --- Permissions -------------------------------------------------------

    @property
    def workflow_perm_namespace(self):
        """Gate this entity on the ``incidents.notification`` feature.

        The derived ``incidents.personaldatabreach`` matches no feature in
        ``PERMISSION_REGISTRY``, so every transition would be refused for
        everyone holding the real codenames. Qualifying a breach is part of the
        same duty of care as deciding what to notify, and the module keeps
        exactly six features for its whole life (RG-INC-39).
        """
        return "incidents.notification"

    # --- Read-only display helpers (API / assistant output) ----------------

    @property
    def incident_reference(self):
        """Reference of the incident this record qualifies."""
        return self.incident.reference if self.incident_id else ""

    @property
    def incident_title(self):
        """Title of the incident this record qualifies."""
        return self.incident.title if self.incident_id else ""

    @property
    def lead_authority_name(self):
        """The Art. 56 lead supervisory authority, when one is determined."""
        return self.lead_authority.display_name if self.lead_authority_id else ""

    @property
    def controller_supplier_name(self):
        """The controller notified under Art. 33(2), when there is one."""
        return self.controller_supplier.name if self.controller_supplier_id else ""

    @property
    def qualified_by_name(self):
        """Who reached the verdict (read-only output)."""
        return self.qualified_by.display_name if self.qualified_by_id else ""

    @property
    def acts_as_processor(self):
        """Whether the Art. 33(2) duty applies instead of Art. 33(1) and 34.

        Read by the UI to spell the consequence out in words rather than leaving
        an enum code on screen : the distinction is the sharpest point in the
        entity and getting it wrong is the difference between a compliant
        response and an unlawful one.
        """
        return self.controller_role == ControllerRole.PROCESSOR

    @property
    def has_article_33_3_content(self):
        """Whether the Art. 33(3)(a)-(d) minimum content is present (G-01)."""
        return all(
            (getattr(self, field) or "").strip() for field in ARTICLE_33_3_FIELDS
        )

    # --- Validation --------------------------------------------------------

    def clean(self):
        """Coherence the breach file cannot be read without."""
        super().clean()
        _validate_string_list(self.data_categories, "data_categories")
        _validate_string_list(self.data_subject_categories, "data_subject_categories")

        errors = {}
        # G-04, restated as a field error so the form says it before the
        # transition does. Also a DB `CheckConstraint`.
        if (
            self.article_34_exemption != Art34Ground.NONE
            and not self.article_34_exemption_justification.strip()
        ):
            errors["article_34_exemption_justification"] = _(
                "An Art. 34(3) exemption must carry its written justification."
            )
        if errors:
            raise ValidationError(errors)

    # --- Write-once stamps (RG-INC-12, gate G-05) --------------------------

    def save(self, *args, **kwargs):
        """Refuse any change to the qualification stamp once it is set.

        The stored row is re-read, so the guard covers the web form, the DRF
        serializer, the MCP update tool and the Django admin at once rather than
        being reproduced in four places.

        What bypasses this, stated rather than glossed : ``QuerySet.update()``,
        ``bulk_update()``, raw SQL and a ``manage.py shell`` session never call
        ``save()``. ``HistoricalRecords`` is what turns that prevention gap into
        detection - an out-of-band change leaves a historical row - and this is
        an application-level guarantee, not an immutability the schema provides.
        """
        if not self._state.adding and self.pk:
            stored = type(self)._base_manager.filter(pk=self.pk).only(
                "qualified_at"
            ).first()
            if (
                stored is not None
                and stored.qualified_at is not None
                and self.qualified_at != stored.qualified_at
            ):
                raise ValidationError(
                    {"qualified_at": _("The qualification timestamp is written once.")}
                )
        return super().save(*args, **kwargs)

    # --- Lifecycle ---------------------------------------------------------

    def transition_to(
        self, target, user=None, comment=None, *, enforce_permission=False, save=True
    ):
        """Apply the Art. 33 / Art. 34 gates, stamp the verdict, then move.

        The whole body runs in one transaction, so a refusal raised after the
        obligations were regenerated rolls that regeneration back with the move
        that triggered it.

        Gates raise :class:`core.lifecycle.LifecycleError` rather than a bare
        ``ValidationError`` : that is the exception the generic stepper endpoint
        (``core/workflow_views.py``) catches and turns into a message, and the
        DRF mixin catches both, so it is the one that behaves correctly on all
        three write surfaces.

        The permission half of gate G-03 is not re-implemented here : both
        verdict edges carry ``permission_action="approve"`` in
        ``incidents/constants.py``, and both carry ``requires_comment``, so the
        approver check and the mandatory comment are enforced by
        ``validate_transition`` on every surface that passes
        ``enforce_permission=True``.
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
            self._check_transition_gates(current, target)
            self._stamp_transition(target, user)
            result = super().transition_to(
                target, user, comment=comment,
                enforce_permission=enforce_permission, save=save,
            )
            self._apply_side_effects(current, target, user)
        return result

    def _check_transition_gates(self, current, target):
        """Refuse the moves a breach file must never contain."""
        if target == STEP_CONFIRMED:
            # G-01 (RG-INC-41) : the full Art. 33(3)(a)-(d) set. Checked on
            # every edge into `confirmed`, including the reopen from
            # `documented` : a record whose content has since been emptied is
            # not one an amendment can be drafted from either.
            missing = [
                field
                for field in ARTICLE_33_3_FIELDS
                if not (getattr(self, field) or "").strip()
            ]
            if missing:
                raise LifecycleError(
                    str(_(
                        "Confirming a breach requires the full Art. 33(3)(a) to "
                        "(d) content : nature, DPO contact, likely consequences "
                        "and measures taken."
                    ))
                )
            # G-02 : `None` is not a verdict. The DPO is made to say yes or no,
            # in writing, because Art. 34(1) turns on it.
            if self.high_risk_to_rights is None:
                raise LifecycleError(
                    str(_(
                        "Confirming a breach requires the Art. 34 determination "
                        "on whether it is likely to result in a high risk to "
                        "the rights and freedoms of natural persons."
                    ))
                )
            # G-04 : an exemption asserted with no written justification is not
            # an exemption. Also a DB `CheckConstraint`.
            if (
                self.article_34_exemption != Art34Ground.NONE
                and not self.article_34_exemption_justification.strip()
            ):
                raise LifecycleError(
                    str(_(
                        "An Art. 34(3) exemption must carry its written "
                        "justification."
                    ))
                )

        # G-06 : `draft` and `under_qualification` are both deletable, so the
        # restore bookend is the one edge that could walk a qualified record
        # back into a deletable step and destroy the GDPR qualification of a
        # real incident. Refused for any row the immutable ledger shows has ever
        # been opened. Mirrors the incident's G-07.
        if current == STEP_ARCHIVED and target == STEP_DRAFT and self._has_left_draft():
            raise LifecycleError(
                str(_(
                    "A qualification that was opened cannot be restored to "
                    "draft."
                ))
            )

    def _stamp_transition(self, target, user):
        """Stamp the verdict (RG-INC-12, gate G-05).

        Write-once, and deliberately **never re-stamped by a reopen** : the
        stamp records when the qualification was first pronounced and by whom,
        and the immutable ``core.LifecycleEvent`` ledger records every later
        verdict with its own actor and time. Re-stamping would overwrite the
        first pronouncement with the last, which is exactly the fact an
        inspector asks about when an exclusion was later reversed.
        """
        if target not in (STEP_CONFIRMED, STEP_NOT_A_BREACH):
            return
        if self.qualified_at is None:
            self.qualified_at = timezone.now()
        if self.qualified_by_id is None and user is not None:
            self.qualified_by = user

    def _apply_side_effects(self, current, target, user):
        """Re-run obligation generation once the GDPR verdict is settled.

        Two template conditions can only now be evaluated : ``controller_roles``
        against a settled ``controller_role``, which is what makes the Art. 33(1)
        obligation appear for a controller and the Art. 33(2) obligation appear
        for a processor - and what stops both appearing for either - and
        ``requires_high_risk`` against a non-null Art. 34 verdict.

        Generation is idempotent : obligations already created at triage are
        found by an explicit lookup, left untouched with their snapshot, and an
        obligation that has already left the *to decide* step is never revisited.

        The reverse never happens : **confirming a breach never removes an
        obligation**. If triage generated an Art. 33(1) obligation and the
        qualification later establishes that the organisation was a processor,
        that obligation is closed through its own ``not_required`` decision with
        the qualification cited as the mandatory rationale (RG-INC-25). An
        obligation once believed to exist and later found not to leaves a
        recorded decision, never a gap.
        """
        if target == STEP_CONFIRMED and current == STEP_UNDER_QUALIFICATION:
            self.incident.generate_notification_obligations(user)

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

    # --- Creation ----------------------------------------------------------

    @classmethod
    @transaction.atomic
    def open_qualification(cls, incident, user=None, **fields):
        """Create the record and open its qualification, in one act.

        **A qualification is never created in ``under_qualification``.**
        ``BaseModel.save()`` calls ``_ensure_initial_step()`` and the lifecycle's
        initial step is ``draft``, so every insert lands there whatever the
        caller intended. Assigning ``workflow_state="under_qualification"`` at
        insert would stick - the snap only fires on a blank or unknown value -
        but it would leave **no** ``core.LifecycleEvent``, so the register would
        hold a qualification nobody is recorded as having opened. And leaving
        the row in ``draft`` is worse still : ``draft`` is deletable, the record
        would not appear in the *awaiting qualification* bucket the DPO works
        from, and the GDPR qualification of a real incident would be invisible
        until someone thought to look for it.

        Returns the existing record untouched when one already exists, including
        one already in ``not_a_breach`` : reopening a ruled-out qualification is
        a deliberate transition, never a side effect.
        """
        existing = cls.objects.filter(incident=incident).first()
        if existing is not None:
            return existing
        breach = cls(incident=incident, created_by=user, **fields)
        breach.save()
        breach.transition_to(
            STEP_UNDER_QUALIFICATION, user, enforce_permission=False
        )
        return breach
