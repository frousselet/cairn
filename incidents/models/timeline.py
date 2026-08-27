# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""The incident chronology : one dated, attributed, append-only entry per act.

This is the single narrative an auditor, a supervisory authority or a court
reads. It is the source of the GDPR Art. 33(3)(a) facts relating to the breach,
of the NIS2 Art. 23(4)(d) final-report description, and of the sequence of
events in the incident register export.

The entity is a plain ``models.Model`` on purpose : no lifecycle, no reference
prefix, no scopes of its own. A narrative line has no states - "10:42 EDR
isolated WEB-PRD-02" is never draft, never pending, never validated - and
giving it a lifecycle would wrap a governance workflow around a sentence and
make the chronology filterable by a step that carries no meaning. It also takes
a row on every parent transition and every responder note during a live
incident, where ``ReferenceGeneratorMixin._generate_next_reference()`` would
scan every existing reference on each insert for an identifier nobody cites.
Entries are cited by their time and their place in the incident file, and are
addressed by UUID on every surface.
"""

import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy
from simple_history.models import HistoricalRecords

from core.lifecycle import LifecycleProtectedError
from incidents.constants import TimelineEntryKind, TimelineEntrySource


class IncidentTimelineEntry(models.Model):
    """One line of an incident's chronology, appended and never rewritten.

    **Append-only is enforced in Python, not by the schema, and the module says
    so rather than claiming an immutability it does not provide.** ``save()``
    refuses any write against an existing row and ``delete()`` refuses
    outright, both raising ``LifecycleProtectedError`` - the house exception
    ``BaseModel.delete()`` already raises when a lifecycle state forbids
    deletion. Every documented write path in Cairn goes through
    ``Model.save()``, so the web forms, the DRF serializers, the MCP tools and
    the Django admin are all covered.

    What is not covered, stated here so nobody discovers it during an audit :
    ``QuerySet.update()`` and ``bulk_update()`` issue SQL without calling
    ``save()``; ``QuerySet.delete()`` and cascade deletion do not call
    ``Model.delete()``, so a cascade from a deleted parent incident removes
    entries without the guard firing (RG-INC-07 keeps that reachable only for a
    ``draft`` incident, which has no narrative worth losing); and raw SQL, a
    ``manage.py shell`` session or direct database access bypass Python
    entirely. ``HistoricalRecords`` is what catches those : an entry whose
    historical trail holds more than one row has been altered, and that is
    visible on the entry's history panel. The honest claim is that tampering
    with the chronology is **prevented on every supported path and detectable
    on the rest**.

    A factual error is fixed by appending a ``correction`` entry pointing at
    ``superseded_entry`` with a stated ``correction_reason``, dated to the
    real-world time of the fact being restated. The superseded entry is never
    modified and never hidden, and a correction may itself be corrected.
    """

    # Never independently scoped (RG-INC-38) : the chronology is read through
    # its incident, always, and inherits that incident's tenancy so it cannot
    # drift when the incident is re-scoped.
    scope_parent_lookup = "incident__scopes"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    incident = models.ForeignKey(
        "incidents.Incident",
        on_delete=models.CASCADE,
        related_name="timeline_entries",
        verbose_name=pgettext_lazy("incident", "Incident"),
    )
    occurred_at = models.DateTimeField(
        _("Occurred at"),
        db_index=True,
        help_text=_(
            "Real-world time of the act being narrated. May be backdated : the "
            "chronology reads in the order things happened, not in the order "
            "they were typed."
        ),
    )
    recorded_at = models.DateTimeField(
        _("Recorded at"),
        auto_now_add=True,
        help_text=_(
            "When the entry was written. A gap with the occurrence time is "
            "normal during a live incident and is itself evidence of tempo."
        ),
    )
    entry_type = models.CharField(
        _("Entry type"),
        max_length=20,
        choices=TimelineEntryKind.choices,
        default=TimelineEntryKind.OBSERVATION,
    )
    summary = models.CharField(
        _("Summary"),
        max_length=500,
        help_text=_(
            "The one-line entry, rendered in the chronology card and exported "
            "verbatim."
        ),
    )
    detail = models.TextField(
        _("Detail"),
        blank=True,
        default="",
        help_text=_(
            "The full account : commands run, output observed, people spoken to."
        ),
    )
    source = models.CharField(
        _("Source"),
        max_length=20,
        choices=TimelineEntrySource.choices,
        default=TimelineEntrySource.MANUAL,
        help_text=_(
            "Whether the line was written by a responder or appended by the "
            "platform on a lifecycle transition."
        ),
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="incident_timeline_entries",
        verbose_name=_("Author"),
        help_text=_(
            "Who wrote the entry. Protected on delete : an account that wrote "
            "incident history stays attributable and is deactivated or "
            "anonymised, never removed."
        ),
    )
    related_action = models.ForeignKey(
        "incidents.IncidentResponseAction",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="timeline_entries",
        verbose_name=_("Related response action"),
        help_text=_("The operational step this entry narrates, when there is one."),
    )
    related_evidence = models.ForeignKey(
        "incidents.IncidentEvidence",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="timeline_entries",
        verbose_name=_("Related evidence"),
        help_text=_("The evidence item this entry narrates, when there is one."),
    )
    superseded_entry = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="corrections",
        verbose_name=_("Supersedes"),
        help_text=_("The earlier entry this one corrects."),
    )
    correction_reason = models.TextField(
        _("Correction reason"),
        blank=True,
        default="",
        help_text=_("A correction with no stated reason is a rewrite."),
    )
    is_evidence = models.BooleanField(
        _("Quote in filings"),
        default=False,
        help_text=_(
            "Include this entry verbatim in generated regulatory filings and "
            "in the incident register export."
        ),
    )
    version = models.PositiveIntegerField(
        _("Version"),
        default=1,
        help_text=_(
            "Row version counter kept for shape consistency with the "
            "platform's other child rows. Never incremented in practice, since "
            "the row is never updated, so a value other than 1 is itself a "
            "signal."
        ),
    )
    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated at"), auto_now=True)

    # Tamper detection, not tamper prevention : see the class docstring.
    history = HistoricalRecords()

    class Meta:
        verbose_name = _("Chronology entry")
        verbose_name_plural = _("Chronology entries")
        # Two responders can legitimately narrate the same minute, so the
        # recording time breaks the tie deterministically and the exported
        # narrative is stable between two renders of the same incident file.
        ordering = ["incident", "occurred_at", "recorded_at"]
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(superseded_entry__isnull=True)
                    | ~models.Q(correction_reason="")
                ),
                name="timeline_correction_has_reason",
            ),
            models.CheckConstraint(
                condition=~models.Q(superseded_entry=models.F("id")),
                name="timeline_entry_not_self_superseding",
            ),
        ]

    def __str__(self):
        return f"{self.occurred_at:%Y-%m-%d %H:%M} : {self.summary}"

    # --- Read-only display helpers (API / assistant output) ----------------

    @property
    def incident_reference(self):
        """Reference of the incident being narrated (read-only output)."""
        return self.incident.reference if self.incident_id else ""

    @property
    def author_name(self):
        """Display name of the entry's author (read-only output)."""
        return self.author.display_name if self.author_id else ""

    @property
    def related_action_reference(self):
        """Reference of the response action this entry narrates."""
        return self.related_action.reference if self.related_action_id else ""

    @property
    def related_evidence_reference(self):
        """Reference of the evidence item this entry narrates."""
        return self.related_evidence.reference if self.related_evidence_id else ""

    @property
    def is_superseded(self):
        """Whether a later entry corrects this one.

        Hits the database, so a list rendering the chronology prefetches
        ``corrections`` rather than reading this per row.
        """
        if self.pk is None:
            return False
        return self.corrections.exists()

    @property
    def recording_delay(self):
        """``recorded_at - occurred_at`` : how long the fact went unwritten.

        Derived rather than stored, and meaningful in its own right : the UI
        shows it whenever the two timestamps differ by more than a few minutes.
        """
        if self.recorded_at is None or self.occurred_at is None:
            return None
        return self.recorded_at - self.occurred_at

    # --- Validation --------------------------------------------------------

    def clean(self):
        """Keep a correction a correction rather than an unexplained restatement."""
        super().clean()
        errors = {}
        if self.superseded_entry_id:
            if not (self.correction_reason or "").strip():
                errors["correction_reason"] = _(
                    "State why the earlier entry is being corrected."
                )
            if self.entry_type != TimelineEntryKind.CORRECTION:
                errors["entry_type"] = _(
                    "An entry superseding another one is a correction."
                )
            if self.superseded_entry_id == self.pk:
                errors["superseded_entry"] = _("An entry cannot correct itself.")
        elif self.entry_type == TimelineEntryKind.CORRECTION:
            errors["superseded_entry"] = _(
                "A correction must name the entry it corrects."
            )
        if errors:
            raise ValidationError(errors)

    # --- Append-only guards ------------------------------------------------

    def save(self, *args, **kwargs):
        """Insert only : an account of an incident that can be rewritten is not evidence.

        Enforced at application level. The bypasses and what detects them are
        set out in the class docstring.
        """
        if not self._state.adding:
            raise LifecycleProtectedError(
                "The incident chronology is append-only : correct an entry by "
                "appending a correction that supersedes it."
            )
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """Refuse deletion outright : there is no delete route on any surface."""
        raise LifecycleProtectedError(
            "A chronology entry is never deleted : it is superseded by a "
            "correction."
        )

    # --- Appending ---------------------------------------------------------

    @classmethod
    def record_transition(cls, incident, *, summary, user, comment="", occurred_at=None):
        """Append the entry that RG-INC-09 owes a parent lifecycle transition.

        Called from ``Incident.transition_to()`` inside the transition's own
        transaction, so a rolled-back transition leaves no entry and a
        committed one always leaves exactly one. Written here rather than
        inline at the call site so the shape of an automatic entry - its kind,
        its source and its ordering timestamp - is decided in one place and
        cannot drift from the hand-written ones it sits beside. The actor is
        required : an unattributed line in the chronology is not evidence.
        """
        return cls.objects.create(
            incident=incident,
            occurred_at=occurred_at or timezone.now(),
            entry_type=TimelineEntryKind.SYSTEM,
            source=TimelineEntrySource.LIFECYCLE,
            summary=str(summary)[:500],
            detail=comment or "",
            author=user,
        )
