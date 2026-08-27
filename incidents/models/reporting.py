# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""The regulatory catalogue : who we owe filings to, and what we owe them.

Two entities, deliberately in one file because neither is readable without the
other : :class:`ReportingAuthority` answers *who is this body and how do we
file with it*, and :class:`ReportingObligationTemplate` answers *what is owed,
when, and under which conditions*. They share a governance posture as well as a
subject : both are module configuration rather than operational records, both
run the core ``default`` 4-state lifecycle, both gate on
``incidents.response_plan`` (RG-INC-39), and both are deliberately instance-wide
rather than scoped (RG-INC-38) - the CNIL is the CNIL for every scope of the
ISMS, and a legal obligation is a property of the organisation and its
jurisdiction, not of an ISMS scope.

Three properties of this file are load-bearing:

**Obligations are expressed as data, not as code.** NIS2 transposition, the
DORA technical standards and every sector regime differ per jurisdiction and
per entity type. A French energy operator and a German bank owe different
filings, on different clocks, to different bodies, and neither of them should
need a release of Cairn to say so.

**Only a validated row generates anything** (RG-INC-30). Both entities are
filtered through ``reportable()``, never through an ``is_active`` boolean and
never against a state literal (RG-INC-37). A draft template is a work in
progress, not a legal position, and a portal URL nobody has checked is worse
than no catalogue at all because the dashboard then reads green.

**A template's terms are snapshotted onto every obligation it generates**
(RG-INC-30, :meth:`ReportingObligationTemplate.obligation_terms`). Editing a
template in 2027 changes what future incidents generate and changes nothing
about a filing already made in 2025. Without that, a breach file printed for an
inspector would cite an article that did not exist when the filing was made -
not a cosmetic defect, but a fabricated record.

Neither entity needs a ``transition_to()`` bookend override, and one must not be
added. The lifecycles this module declares for itself have to hand-declare their
archive and restore edges because ``lifecycle_from_state_flags()`` generates
them with no ``permission_action``, which opens an ``archive -> restore ->
delete`` path around every gate. The core ``default`` lifecycle has neither
problem : its archive edge already carries ``permission_action="approve"`` and
it declares no restore transition at all.
"""

from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy
from simple_history.models import HistoricalRecords

from context.constants import Criticality
from context.models.base import BaseModel
from core.lifecycle import reportable, reportable_states
from incidents.constants import (
    REFERENCE_PREFIXES,
    AuthorityType,
    ClockAnchor,
    ControllerRole,
    NotificationRecipientKind,
    NotificationRegime,
)
from risks.constants import ThreatCategory

#: ``Criticality`` is declared least to most severe, so its declaration order
#: **is** the scale. ``min_severity`` is a floor on that scale and is never
#: compared as a string : "critical" < "low" alphabetically, and a template
#: floored at ``high`` would then match a ``low`` incident.
_SEVERITY_ORDER = list(Criticality.values)


def _severity_rank(value):
    """Position of a severity on the shared scale, or ``-1`` when unset."""
    try:
        return _SEVERITY_ORDER.index(value)
    except ValueError:
        return -1


def _validate_enum_list(value, enum, label):
    """Validate a ``JSONField`` list element by element against ``enum``.

    ``JSONField`` rather than ``ArrayField`` is what lets ``core.settings_test``
    (SQLite in memory) run the module unchanged, and it is also what removes the
    database's own type checking : without this, a typo in a stored code matches
    nothing for ever and reads on screen exactly like a deliberate restriction.
    """
    if value in (None, ""):
        return []
    if not isinstance(value, list):
        raise ValidationError({label: _("This value must be a list.")})
    allowed = set(enum.values)
    unknown = [item for item in value if item not in allowed]
    if unknown:
        raise ValidationError(
            {label: _("Unknown value(s) : %(values)s") % {"values": ", ".join(
                str(item) for item in unknown
            )}}
        )
    if len(set(value)) != len(value):
        raise ValidationError({label: _("This list contains duplicates.")})
    return value


def _breach_of(incident):
    """The incident's GDPR qualification record, or ``None``.

    Resolved through the reverse accessor rather than by importing the model, so
    no import cycle can form between the module's model files. A missing record
    is a legitimate answer : conditions 8 and 10 of the match then evaluate to
    *no match*, which is correct - a GDPR-conditioned template cannot fire on an
    incident that has not been qualified under GDPR at all.
    """
    try:
        return incident.personal_data_breach
    except ObjectDoesNotExist:
        return None


def resolve_incident_jurisdictions(incident):
    """The jurisdictions an incident is attached to, casefolded.

    Stated plainly rather than implied : **nothing in the platform carries a
    structured country today.** ``context.Site`` has a free-text ``address`` and
    ``context.Scope`` has no country column at all, so this resolves the
    incident's own ``jurisdiction_country`` when the model ever grows one and
    otherwise returns an empty set, meaning *unknown*.

    :meth:`ReportingObligationTemplate.matches` is written so that an unknown
    jurisdiction never **suppresses** an obligation. That direction is
    deliberate and is the module's stated position everywhere the two errors are
    weighed against each other : an obligation generated in error is discharged
    through its own ``not_required`` decision, with a named decider, a timestamp
    and a written rationale, and leaves audit evidence. An obligation silently
    never generated leaves an absence nobody can review, and it is
    indistinguishable from having forgotten.
    """
    declared = (getattr(incident, "jurisdiction_country", "") or "").strip()
    return {declared.casefold()} if declared else set()


class ReportingAuthority(BaseModel):
    """One body the organisation may owe a filing to.

    The entity is deliberately small : it answers *who is this body, how do we
    file with it, and is this row trustworthy enough to generate obligations
    from*, and nothing else. What is owed lives on
    :class:`ReportingObligationTemplate`; a particular filing lives on
    ``IncidentNotification``.

    ``portal_url``, ``contact_email``, ``contact_phone``,
    ``notification_language`` and ``procedure`` are exactly the facts nobody has
    time to look up during an incident. Preparing them is part of A.5.24
    planning, not part of the response, and this row is the documented evidence
    for A.5.5 (contact with authorities).
    """

    REFERENCE_PREFIX = REFERENCE_PREFIXES["ReportingAuthority"]

    name = models.CharField(
        _("Name"),
        max_length=255,
        help_text=_("Full legal name of the body, as it signs its decisions."),
    )
    short_name = models.CharField(
        _("Short name"),
        max_length=50,
        blank=True,
        default="",
        help_text=_("Common acronym : CNIL, ANSSI, ACPR, BSI. What the list "
                    "view and every badge actually display."),
    )
    authority_type = models.CharField(
        _("Authority type"),
        max_length=32,
        choices=AuthorityType.choices,
        default=AuthorityType.OTHER,
        db_index=True,
        help_text=_(
            "The principal capacity this body acts in. A single body frequently "
            "wears two hats - ANSSI is both the French competent authority and "
            "the national CSIRT - and the catalogue does not model that as two "
            "rows : the regimes below record what it actually handles."
        ),
    )
    primary_regime = models.CharField(
        _("Primary regime"),
        max_length=32,
        choices=NotificationRegime.choices,
        db_index=True,
        help_text=_(
            "The regime this body principally acts under. A filtering and "
            "display aid only : obligation matching keys off the template's "
            "own regime, never off this field."
        ),
    )
    additional_regimes = models.JSONField(
        _("Additional regimes"),
        default=list,
        blank=True,
        help_text=_("Other regimes the same body handles."),
    )
    jurisdiction_country = models.CharField(
        # "Jurisdiction" and "Country" both already carry the right French in
        # the catalogue, so this label is composed of two existing msgids rather
        # than declaring a colliding new one.
        _("Jurisdiction"),
        max_length=100,
        blank=True,
        default="",
        help_text=_(
            "Country name, ISO code, or the literal EU. Blank means the body is "
            "not jurisdiction-specific."
        ),
    )
    portal_url = models.URLField(
        _("Portal URL"),
        blank=True,
        default="",
        help_text=_(
            "The online notification portal, rendered as the primary action on "
            "the obligation page : one click from the duty to the form that "
            "discharges it."
        ),
    )
    contact_email = models.EmailField(
        # Labelled "Contact email" rather than "Email", which is already a bare
        # msgid in the catalogue : a duplicate entry fails `compilemessages`.
        _("Contact email"),
        blank=True,
        default="",
        help_text=_("Notification mailbox, for regimes filed by email."),
    )
    contact_phone = models.CharField(
        _("Contact phone"),
        max_length=50,
        blank=True,
        default="",
        help_text=_(
            "Emergency line. Several CSIRTs expect a phone call before the "
            "written filing, and that fact belongs in the register rather than "
            "in someone's memory."
        ),
    )
    notification_language = models.CharField(
        _("Notification language"),
        max_length=10,
        blank=True,
        default="",
        help_text=_(
            "Language the filing must be drafted in. A filing rejected for "
            "language is a filing not made, and the clock does not stop."
        ),
    )
    procedure = models.TextField(
        _("Procedure"),
        blank=True,
        default="",
        help_text=_(
            "Which form, which attachments, who signs, what the acknowledgement "
            "looks like, and what the escalation path is when the portal is "
            "down. This is the field that earns the entity its place."
        ),
    )

    history = HistoricalRecords()

    class Meta(BaseModel.Meta):
        verbose_name = _("Reporting authority")
        verbose_name_plural = _("Reporting authorities")
        ordering = ["name"]
        constraints = [
            # Per jurisdiction on purpose : "Data Protection Authority" is a
            # defensible name in a dozen countries, and a group operating in
            # several of them needs one row each. Both columns are non-nullable
            # (`jurisdiction_country` is blank, never NULL), so the constraint
            # behaves identically on PostgreSQL and on SQLite : there is no
            # NULL-distinctness surprise of the kind that makes a unique index
            # over nullable columns silently permit duplicates.
            models.UniqueConstraint(
                fields=["name", "jurisdiction_country"],
                name="unique_authority_per_jurisdiction",
            ),
        ]

    def __str__(self):
        return f"{self.reference} : {self.display_name}"

    # --- Permissions -------------------------------------------------------

    @property
    def workflow_perm_namespace(self):
        """Gate this catalogue on the ``incidents.response_plan`` feature.

        The derived ``incidents.reportingauthority`` matches no feature in
        ``PERMISSION_REGISTRY``, so every lifecycle permission check would
        evaluate against a codename nobody holds and every transition would be
        refused for everyone. The module keeps exactly six features for its
        whole life (RG-INC-39), and a regulatory contact list is configuration,
        governed like the response plan it is prepared alongside.
        """
        return "incidents.response_plan"

    # --- Read-only display helpers (API / assistant output) ----------------

    @property
    def display_name(self):
        """The acronym when there is one : what an operator actually reads."""
        return self.short_name or self.name

    @property
    def default_recipient_kind(self):
        """The recipient kind proposed for a template created against this row.

        Always ``authority`` : ``NotificationRecipientKind`` classifies *who
        receives a filing*, and every body in this catalogue is an authority in
        that sense, whatever capacity ``authority_type`` records. A per-kind
        table here would be a mapping with one value.
        """
        return NotificationRecipientKind.SUPERVISORY_AUTHORITY

    # --- Generation ---------------------------------------------------------

    @classmethod
    def usable(cls):
        """Authorities obligation generation may cite (RG-INC-30).

        Through ``reportable()``, never an ``is_active`` boolean and never a
        state literal (RG-INC-37). A draft authority is a work in progress, not
        a legal contact, and generating a 24-hour obligation against a portal
        URL nobody has checked is worse than generating nothing.
        """
        return reportable(cls.objects.all())

    # --- Validation --------------------------------------------------------

    def clean(self):
        """Reject a regime code that would silently mean nothing."""
        super().clean()
        _validate_enum_list(
            self.additional_regimes, NotificationRegime, "additional_regimes"
        )


class ReportingObligationTemplate(BaseModel):
    """The rule that turns incident facts into an owed deliverable.

    Regime + authority + clock + trigger conditions + content checklist. A
    template generates nothing by itself : it is matched against an incident at
    triage, on a severity raise and on a breach confirmation, and each match
    produces one obligation whose legal terms are snapshotted at creation.

    **Real regulatory rules are disjunctive and conditional; this model is a
    flat conjunction.** The gap is deliberate and is paid for with near-duplicate
    templates rather than with a rule expression language. *"Significant or
    affecting more than N users"* is written as two templates, and the generator
    de-duplicates on ``(incident, regime, recipient)`` so an incident matching
    both still owes one filing. *"Unless the data was encrypted"* is not
    expressed at all : the obligation is generated and the exemption is
    discharged through its own approve-gated ``not_required`` decision, because
    an exemption that is recorded is audit evidence while an exemption that
    suppresses a row is an absence nobody can review.

    A rule expression language would express both. It would also need a parser,
    an evaluator, a test surface, an editing UI, a migration path for stored
    expressions and a way to explain to an operator at 02:00 why a rule did or
    did not fire. The design refuses to build one, and reconsiders only if a
    real regime cannot be expressed at all - not because expressing it takes
    three templates instead of one.
    """

    REFERENCE_PREFIX = REFERENCE_PREFIXES["ReportingObligationTemplate"]

    name = models.CharField(
        _("Name"),
        max_length=255,
        help_text=_(
            "Human label, e.g. NIS2 early warning (24h) - ANSSI. With "
            "near-duplicate variants in the catalogue, this field has to earn "
            "its keep by saying which variant a row is."
        ),
    )
    authority = models.ForeignKey(
        "incidents.ReportingAuthority",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="obligation_templates",
        verbose_name=_("Reporting authority"),
        help_text=_(
            "The body the filing goes to. Null for a recipient that is not an "
            "authority : data subjects, customers, the public."
        ),
    )

    # --- What is owed, and to whom (all snapshotted onto the obligation) ---

    regime = models.CharField(
        _("Regime"),
        max_length=32,
        choices=NotificationRegime.choices,
        db_index=True,
        help_text=_("The legal basis the obligation arises from."),
    )
    recipient_kind = models.CharField(
        _("Recipient kind"),
        max_length=32,
        choices=NotificationRecipientKind.choices,
        help_text=_("Who receives the filing."),
    )
    legal_reference = models.CharField(
        _("Legal reference"),
        max_length=255,
        blank=True,
        default="",
        help_text=_(
            "Article citation, e.g. NIS2 Art. 23(4)(a). The string an auditor "
            "greps the register for."
        ),
    )
    content_requirements = models.TextField(
        _("Content requirements"),
        blank=True,
        default="",
        help_text=_(
            "The legal checklist of what the filing must contain, rendered "
            "next to the drafting field so the drafter never leaves the page to "
            "find out what Art. 33(3) requires."
        ),
    )

    # --- The clock ---------------------------------------------------------

    clock_anchor = models.CharField(
        _("Clock anchor"),
        max_length=32,
        choices=ClockAnchor.choices,
        default=ClockAnchor.AWARENESS_AT,
        help_text=_(
            "Which timestamp starts the statutory clock. Legal awareness is the "
            "correct anchor for GDPR Art. 33(1) and NIS2 Art. 23(4)(a)-(b); "
            "technical detection is never an acceptable anchor for a statutory "
            "clock and exists only for the few contractual clauses genuinely "
            "written against it."
        ),
    )
    clock_hours = models.PositiveIntegerField(
        _("Clock hours"),
        null=True,
        blank=True,
        help_text=_(
            "Statutory delay in hours from the anchor : 24, 72, 720 (one "
            "month). Null if and only if there is no fixed deadline."
        ),
    )
    no_fixed_deadline = models.BooleanField(
        _("No statutory deadline"),
        default=False,
        help_text=_(
            "A without-undue-delay duty with no computable deadline (GDPR "
            "Art. 33(2) and Art. 34(1), NIS2 Art. 23(1) to recipients). "
            "Generated obligations then carry no due date, are never counted "
            "late, and appear in their own bucket rather than vanishing from "
            "every are-we-late query. Never fabricate a deadline for an "
            "obligation that legally has none."
        ),
    )
    depends_on_regime = models.CharField(
        _("Depends on regime"),
        max_length=32,
        choices=NotificationRegime.choices,
        blank=True,
        default="",
        help_text=_(
            "The sibling regime whose first filing anchors this one. NIS2 "
            "Art. 23(4)(d) : the final report is due one month after the "
            "incident notification, not one month after awareness."
        ),
    )

    # --- Trigger conditions (matching inputs, never snapshotted) -----------

    jurisdiction_country = models.CharField(
        _("Jurisdiction"),
        max_length=100,
        blank=True,
        default="",
        help_text=_("Restricts the template to one jurisdiction. Blank means any."),
    )
    min_severity = models.CharField(
        # "Severity" alone is already a bare msgid in the catalogue; the longer
        # label avoids the collision outright and reads better.
        pgettext_lazy("incident", "Minimum severity"),
        max_length=20,
        choices=Criticality.choices,
        blank=True,
        default="",
        help_text=_("Severity floor on the shared scale. Blank means any."),
    )
    requires_significant = models.BooleanField(
        _("Requires a significant incident"),
        default=False,
        help_text=_(
            "NIS2 Art. 23(3). A null verdict is not a match : an undetermined "
            "significance never silently generates or suppresses a duty."
        ),
    )
    requires_personal_data = models.BooleanField(
        _("Requires personal data"),
        default=False,
        help_text=_("Only fires when the incident declares personal data (GDPR)."),
    )
    requires_high_risk = models.BooleanField(
        _("Requires a high risk to rights"),
        default=False,
        help_text=_(
            "GDPR Art. 34(1). Evaluated against the breach qualification's "
            "verdict, and a null verdict is not a match."
        ),
    )
    requires_cross_border = models.BooleanField(
        _("Requires cross-border impact"),
        default=False,
        help_text=_(
            "Operational cross-border impact on the incident, which is not the "
            "same concept as GDPR cross-border processing on the breach record."
        ),
    )
    controller_roles = models.JSONField(
        _("Controller roles"),
        default=list,
        blank=True,
        help_text=_(
            "Restricts a GDPR template by the capacity the organisation was "
            "processing in. Empty means any. This is what separates a "
            "controller's Art. 33(1) duty from a processor's Art. 33(2) duty."
        ),
    )
    applicable_categories = models.JSONField(
        _("Applicable categories"),
        default=list,
        blank=True,
        help_text=_("Restricts the template to certain incident categories. "
                    "Empty means all of them."),
    )

    order = models.IntegerField(
        _("Order"),
        default=0,
        help_text=_(
            "Display and generation order within a regime, so the 24h early "
            "warning is listed above the 72h notification rather than "
            "alphabetically."
        ),
    )

    history = HistoricalRecords()

    class Meta(BaseModel.Meta):
        verbose_name = _("Reporting obligation template")
        verbose_name_plural = _("Reporting obligation templates")
        ordering = ["regime", "order", "name"]
        constraints = [
            # A duplicate guard, not a modelling statement. `authority` is
            # nullable and PostgreSQL treats NULLs as distinct in a unique
            # index, so the guard is split in two conditional constraints rather
            # than declared once with `nulls_distinct=False` : Django raises
            # W047 and drops that clause on backends that do not support it, so
            # `core.settings_test` (SQLite) could never exercise it and the
            # constraint would be untested precisely where a regression would be
            # introduced. The generator is independently idempotent in any case.
            models.UniqueConstraint(
                fields=["regime", "recipient_kind", "authority", "jurisdiction_country"],
                condition=models.Q(authority__isnull=False),
                name="unique_obligation_template",
            ),
            models.UniqueConstraint(
                fields=["regime", "recipient_kind", "jurisdiction_country"],
                condition=models.Q(authority__isnull=True),
                name="unique_obligation_template_without_authority",
            ),
            # The database half of the clock rule : a delay of null hours that
            # does not declare itself deadline-free would generate obligations
            # with no computable due date and no bucket to appear in.
            models.CheckConstraint(
                condition=(
                    models.Q(no_fixed_deadline=True, clock_hours__isnull=True)
                    | models.Q(no_fixed_deadline=False, clock_hours__isnull=False)
                ),
                name="obligation_template_clock_hours_iff_deadline",
            ),
        ]

    def __str__(self):
        return f"{self.reference} : {self.name}"

    # --- Permissions -------------------------------------------------------

    @property
    def workflow_perm_namespace(self):
        """Gate this catalogue on the ``incidents.response_plan`` feature.

        The derived ``incidents.reportingobligationtemplate`` matches no feature
        in ``PERMISSION_REGISTRY`` (RG-INC-39). The ``approve`` gate is the
        point of running a lifecycle here at all : one careless edit to a
        ``clock_hours`` value changes every future deadline in the register.
        """
        return "incidents.response_plan"

    # --- Read-only display helpers (API / assistant output) ----------------

    @property
    def authority_name(self):
        """The body this template files with, or an empty string."""
        return self.authority.display_name if self.authority_id else ""

    @property
    def clock_summary(self):
        """The clock as one sentence, which is what a reviewer actually checks.

        A table of five raw fields is what they skip. Rendered above the raw
        fields on the detail page, never instead of them.
        """
        if self.no_fixed_deadline:
            return _("No statutory deadline : without undue delay")
        anchor = self.get_clock_anchor_display()
        if self.clock_anchor == ClockAnchor.PREVIOUS_STAGE and self.depends_on_regime:
            anchor = _("the filing of %(regime)s") % {
                "regime": NotificationRegime(self.depends_on_regime).label
            }
        return _("%(hours)s h from %(anchor)s") % {
            "hours": self.clock_hours,
            "anchor": anchor,
        }

    # --- Validation --------------------------------------------------------

    def clean(self):
        """Refuse the shapes that would generate a wrong deadline, or none.

        The three list fields are validated element by element : ``JSONField``
        is what keeps the module running on the SQLite test settings, and it is
        also what removes the database's own type checking, so a typo would
        otherwise match nothing for ever while reading on screen exactly like a
        deliberate restriction.
        """
        super().clean()
        _validate_enum_list(self.controller_roles, ControllerRole, "controller_roles")
        _validate_enum_list(
            self.applicable_categories, ThreatCategory, "applicable_categories"
        )

        errors = {}
        if self.no_fixed_deadline and self.clock_hours is not None:
            errors["clock_hours"] = _(
                "An obligation with no statutory deadline carries no delay."
            )
        if not self.no_fixed_deadline and self.clock_hours is None:
            errors["clock_hours"] = _(
                "State the statutory delay in hours, or declare that this "
                "obligation has no fixed deadline."
            )
        if self.clock_anchor == ClockAnchor.PREVIOUS_STAGE and not self.depends_on_regime:
            errors["depends_on_regime"] = _(
                "An obligation anchored on a previous filing must name the "
                "regime whose filing anchors it."
            )
        if self.depends_on_regime and self.depends_on_regime == self.regime:
            errors["depends_on_regime"] = _(
                "An obligation cannot be anchored on its own filing : its "
                "deadline could never be computed."
            )
        if errors:
            raise ValidationError(errors)

    # --- Matching ----------------------------------------------------------

    @classmethod
    def in_force(cls):
        """Templates obligation generation may fire (RG-INC-30).

        Both halves go through ``reportable()`` (RG-INC-37) : the template must
        be validated, and the authority it names - when it names one - must be
        validated too.
        """
        return reportable(cls.objects.select_related("authority")).filter(
            models.Q(authority__isnull=True)
            | models.Q(
                authority__workflow_state__in=reportable_states(ReportingAuthority)
            )
        )

    @classmethod
    def matching_for(cls, incident):
        """The templates an incident owes a filing under, in generation order.

        Returns a list rather than a queryset : four of the ten conditions read
        the incident's breach qualification and its three-state verdicts, which
        are Python comparisons against ``True`` and not database predicates.
        """
        return [
            template
            for template in cls.in_force()
            if template.matches(incident)
        ]

    def matches(self, incident):
        """Whether every declared condition holds for ``incident``.

        A flat conjunction, short-circuiting on the first failure. Three-state
        booleans are compared to ``True`` explicitly, never with a truthiness
        test : ``None`` means *not yet determined*, and an undetermined verdict
        must neither generate an obligation nor suppress one. The operator is
        asked for the verdict, and generation is re-run when it arrives.
        """
        if self.jurisdiction_country:
            jurisdictions = resolve_incident_jurisdictions(incident)
            if jurisdictions and self.jurisdiction_country.casefold() not in jurisdictions:
                return False
        if self.min_severity:
            if _severity_rank(incident.severity) < _severity_rank(self.min_severity):
                return False
        if self.applicable_categories:
            if incident.category not in self.applicable_categories:
                return False
        if self.requires_significant and incident.is_significant is not True:
            return False
        if self.requires_personal_data and not incident.personal_data_involved:
            return False
        if self.requires_cross_border and incident.cross_border_impact is not True:
            return False
        if self.requires_high_risk or self.controller_roles:
            breach = _breach_of(incident)
            if breach is None:
                return False
            if self.requires_high_risk and breach.high_risk_to_rights is not True:
                return False
            if self.controller_roles and breach.controller_role not in self.controller_roles:
                return False
        return True

    # --- The snapshot ------------------------------------------------------

    def obligation_terms(self):
        """The legal terms to write onto an obligation generated from this row.

        Keyed by ``IncidentNotification`` field name, so a generator passes the
        result straight through as its ``defaults``. **Called once, at
        creation** (RG-INC-30) : the terms are never rewritten by a later
        template edit, and an obligation that already exists is left untouched,
        snapshot included.

        What the ``template`` foreign key preserves that the snapshot cannot is
        provenance : the snapshot answers *what were we told we owed*, the FK
        answers *which rule produced this*, and the template's own history
        answers *what did that rule say at the time*. Both are needed, and
        neither substitutes for the other.

        The matching inputs (``min_severity``, the ``requires_*`` flags,
        ``controller_roles``, ``applicable_categories``, ``jurisdiction_country``)
        are deliberately absent : they are not terms of the obligation. Once an
        obligation exists, *why does this exist* is answered by this FK and by
        the incident's own recorded facts, both of which are historised.
        """
        return {
            "template": self,
            "authority": self.authority,
            "regime": self.regime,
            "recipient_kind": self.recipient_kind,
            "obligation_reference": self.legal_reference,
            "clock_anchor": self.clock_anchor,
            "deadline_hours": self.clock_hours,
            "no_fixed_deadline": self.no_fixed_deadline,
            "content_requirements": self.content_requirements,
        }
