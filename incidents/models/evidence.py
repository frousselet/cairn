# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""The A.5.28 evidence register and its append-only chain of custody.

Two entities, deliberately in one file because neither is readable without the
other : :class:`IncidentEvidence` holds *what was acquired* - the artefact, its
acquisition metadata and its fingerprint - and :class:`EvidenceCustodyEvent`
holds *who held it, when, where, and did the hash still match*, which is the
half of ISO/IEC 27001:2022 A.5.28 a register of files alone never answers.

Three properties of this file are load-bearing and none of them is decorative:

1. **Sealing freezes the acquisition metadata.** ``IncidentEvidence.save()``
   re-reads the stored row and refuses any change to the six acquisition fields
   once ``sealed_at`` is set (RG-INC-20), so the guard covers the web form, the
   DRF serializer, the MCP update tool and the Django admin alike.
2. **Destruction is a transition, never a ``DELETE``** (RG-INC-24). The row, the
   hash and the ledger survive the artefact ; erasing them would erase the proof
   that the organisation ever held the item, which is exactly the fact A.5.28
   asks it to be able to show.
3. **The ledger is append-only.** ``EvidenceCustodyEvent.save()`` refuses a
   second write and ``delete()`` refuses outright.

As everywhere else in the module, this is **prevention at application level and
detection via** ``HistoricalRecords`` : ``QuerySet.update()``, ``bulk_update()``,
raw SQL and a ``manage.py shell`` session bypass ``save()`` entirely. The honest
claim is that tampering is prevented on every supported path and detectable on
the rest, not that the register is immutable.

Every audit gate lives in :meth:`IncidentEvidence.transition_to` (RG-INC-08),
never on the ``Transition`` object : ``lifecycle_to_json`` drops ``form_class``
/ ``allowed_roles`` / ``allowed_users`` by design and ``get_lifecycle()``
prefers the ``post_migrate``-seeded ``LifecycleDefinition`` row, so a gate
declared that way is green in an in-memory unit test and silently dead on every
migrated database.
"""

import hashlib
import uuid

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.core.validators import FileExtensionValidator
from django.db import models, transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy
from simple_history.models import HistoricalRecords

from context.models.base import BaseModel
from core.lifecycle import DomainRefusalError, LifecycleProtectedError
from incidents.constants import (
    EVIDENCE_STATES,
    REFERENCE_PREFIXES,
    CustodyAction,
    EvidenceType,
    HashAlgorithm,
    TimelineEntrySource,
    TrafficLightProtocol,
)


def _evidence_step(code):
    """Resolve a step code **by name** against the single source of truth.

    Reading the codes back out of ``incidents/constants.py`` (RG-INC-37) means
    a rename there raises at import time instead of silently disabling a gate.
    A dead gate on evidence destruction is precisely the class of failure this
    module exists to prevent.
    """
    if code not in {declared for declared, *_flags in EVIDENCE_STATES}:
        raise ImproperlyConfigured(
            f"'{code}' is not a step of the incident_evidence lifecycle."
        )
    return code


STEP_DRAFT = _evidence_step("draft")
STEP_COLLECTED = _evidence_step("collected")
STEP_SECURED = _evidence_step("secured")
STEP_ANALYSED = _evidence_step("analysed")
STEP_RETAINED = _evidence_step("retained")
STEP_RELEASED = _evidence_step("released")
STEP_DESTROYED = _evidence_step("destroyed")
STEP_ARCHIVED = _evidence_step("archived")

#: The acquisition metadata frozen by sealing (RG-INC-20). Exported so the
#: forms, serializers and MCP ``writable_fields`` lists all read the same list
#: rather than each keeping a copy that can drift from the guard below.
EVIDENCE_ACQUISITION_FIELDS = (
    "file",
    "content_hash",
    "hash_algorithm",
    "collected_at",
    "collected_by",
    "collection_method",
)

#: Written by the transition override and by the integrity verification only
#: (GE-06 / RG-INC-12) : excluded from every ``ModelForm``, ``read_only`` in
#: every serializer, absent from every MCP ``writable_fields`` list.
EVIDENCE_TRANSITION_STAMPED_FIELDS = (
    "sealed_at",
    "destruction_authorised_by",
    "last_integrity_check_at",
    "last_integrity_check_ok",
)

#: Handling acts that require a named counterparty (RG-INC-22). A handover to
#: an organisation with no named individual is not a handover.
CUSTODY_ACTIONS_REQUIRING_COUNTERPARTY = (
    CustodyAction.TRANSFERRED,
    CustodyAction.RELEASED,
    CustodyAction.RETURNED,
    CustodyAction.DESTROYED,
)

#: The three-way outcome of an integrity verification. "Not verifiable" is a
#: claim about the infrastructure and must never be collapsed into "mismatch",
#: which is a permanent claim about the artefact (RG-INC-23).
VERIFICATION_MATCH = "match"
VERIFICATION_MISMATCH = "mismatch"
VERIFICATION_NOT_VERIFIABLE = "not_verifiable"

ALLOWED_EVIDENCE_EXTENSIONS = [
    "pdf", "doc", "docx", "xls", "xlsx", "csv", "txt", "log", "json", "xml",
    "eml", "msg", "png", "jpg", "jpeg", "zip", "gz", "7z", "pcap", "pcapng",
    "e01", "dd", "raw", "img", "mem", "vmem",
]

#: Fallback for ``settings.INCIDENT_EVIDENCE_MAX_UPLOAD_BYTES`` (50 MB). Read
#: through :func:`evidence_max_upload_bytes` so a deployment that has not set
#: the environment variable still refuses the same thing on every surface.
DEFAULT_EVIDENCE_MAX_UPLOAD_BYTES = 52428800

#: Read in 8 MB slices : a disk image must never be pulled into memory whole
#: just to be re-hashed.
_HASH_CHUNK_BYTES = 8 * 1024 * 1024


def evidence_max_upload_bytes():
    """Cap on the inline copy of an artefact, in bytes.

    Above it, the item is *registered by reference* : ``file`` stays empty,
    ``storage_location`` names where the artefact actually is, and the platform
    holds the fingerprint of something it does not hold.
    """
    return getattr(
        settings,
        "INCIDENT_EVIDENCE_MAX_UPLOAD_BYTES",
        DEFAULT_EVIDENCE_MAX_UPLOAD_BYTES,
    )


def validate_evidence_upload_size(value):
    """Refuse an inline artefact above the configured cap."""
    limit = evidence_max_upload_bytes()
    if value and value.size and value.size > limit:
        raise ValidationError(
            _(
                "This artefact exceeds the %(limit)d byte inline limit. Register "
                "it by reference : record its storage location, its size and its "
                "hash instead of uploading it."
            )
            % {"limit": limit}
        )


def _evidence_upload_path(instance, filename):
    """``incidents/<incident_id>/evidence/<uuid>/<filename>``.

    The per-row UUID directory means two artefacts sharing a filename never
    collide, and a path never leaks another incident's identifiers.
    """
    return f"incidents/{instance.incident_id}/evidence/{instance.pk}/{filename}"


class IncidentEvidence(BaseModel):
    """One item of the A.5.28 evidence register, with its own custody lifecycle.

    Evidence is the one child of an incident that genuinely needs a lifecycle
    of its own, for three reasons no plain child row can express : deletion must
    be state-dependent (only a ``draft`` registration is a typo worth removing),
    destruction is a permissioned transition rather than a ``DELETE``, and
    sealing is a state rather than a boolean anybody's update path could set.

    It is **not** a ``ScopedModel``. It inherits the incident's tenancy through
    ``scope_parent_lookup``, declared on the model rather than only on the views
    so the generic workflow, history and MCP surfaces enforce it too (RG-INC-38,
    see ``core.scoping``). This is the entity where that inheritance matters
    most : the endpoints it would otherwise leave open are the ones that destroy
    sealed evidence.
    """

    REFERENCE_PREFIX = REFERENCE_PREFIXES["IncidentEvidence"]
    LIFECYCLE_NAME = "incident_evidence"

    # Scope is inherited from the parent incident, so it can never drift out of
    # alignment when the incident is re-scoped. `incident` is required, so no
    # `scope_parent_optional` : there is no such thing as a parentless artefact.
    scope_parent_lookup = "incident__scopes"

    incident = models.ForeignKey(
        "incidents.Incident",
        on_delete=models.PROTECT,
        related_name="evidence_items",
        verbose_name=pgettext_lazy("incident", "Incident"),
        help_text=_(
            "The incident this artefact belongs to. Protected on delete : an "
            "incident holding evidence is never deleted, whatever its own state."
        ),
    )
    title = models.CharField(
        _("Title"),
        max_length=255,
        help_text=_("Evidence label, e.g. 'Memory image - WEB-PRD-02'."),
    )
    description = models.TextField(
        _("Description"),
        blank=True,
        default="",
        help_text=_("What the item is and why it matters to this incident."),
    )
    evidence_type = models.CharField(
        _("Evidence type"),
        max_length=32,
        choices=EvidenceType.choices,
        db_index=True,
        help_text=_(
            "The nature of the item, which drives the acceptable acquisition "
            "method."
        ),
    )
    # Nullable on purpose : a draft registration is the form before the
    # acquisition is confirmed, and gate GE-01 is what makes these two
    # mandatory. A gate checking a column the schema already forbids to be
    # empty is dead code, and the mandatory-ness would then live in the schema
    # where the audit trail cannot see it being satisfied.
    collected_at = models.DateTimeField(
        _("Collected at"),
        null=True,
        blank=True,
        help_text=_(
            "The moment the artefact left the live system. Required to leave "
            "the draft registration, and frozen once the item is sealed."
        ),
    )
    collected_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="collected_evidence",
        verbose_name=_("Collected by"),
        help_text=_(
            "The named acquirer, who is not necessarily whoever registered the "
            "row. Protected on delete : an acquisition attributed to a deleted "
            "account is an acquisition attributed to nobody. Deactivate or "
            "anonymise the user instead."
        ),
    )
    collection_method = models.TextField(
        _("Collection method"),
        blank=True,
        default="",
        help_text=_(
            "Tooling and version, write-blocker, exact command line, witness "
            "present, live or powered-down source. This is the heart of "
            "admissibility : an artefact with a perfect hash and no stated "
            "method is a file, not evidence."
        ),
    )
    source_support_asset = models.ForeignKey(
        "assets.SupportAsset",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="evidence_items",
        verbose_name=_("Source asset"),
        help_text=_(
            "The registered machine, service or device the artefact came off."
        ),
    )
    source_description = models.CharField(
        _("Source"),
        max_length=500,
        blank=True,
        default="",
        help_text=_(
            "Free-text origin when it is not a registered support asset : a "
            "personal device, a third-party service, a printed document, a "
            "physical location."
        ),
    )
    storage_location = models.CharField(
        _("Location"),
        max_length=500,
        blank=True,
        default="",
        help_text=_(
            "Where the item physically or logically resides : safe number, "
            "evidence bag identifier, vault, bucket and object key, forensics "
            "provider case number. This is how bulk artefacts are registered "
            "by reference."
        ),
    )
    file = models.FileField(
        _("File"),
        upload_to=_evidence_upload_path,
        blank=True,
        # The generated path spends 93 characters on the two UUID directories
        # before the filename starts, so the 100-character default would refuse
        # ordinary uploads outright.
        max_length=400,
        validators=[
            FileExtensionValidator(allowed_extensions=ALLOWED_EVIDENCE_EXTENSIONS),
            validate_evidence_upload_size,
        ],
        help_text=_(
            "Optional inline copy of a small artefact. A malware sample and a "
            "seized device are never stored here : they are registered by "
            "reference with a storage location."
        ),
    )
    original_filename = models.CharField(
        _("File name"),
        max_length=255,
        blank=True,
        default="",
        help_text=_(
            "Filename as acquired, preserved because the name is often itself "
            "evidence. Retained after destruction."
        ),
    )
    # PositiveBigIntegerField and not PositiveIntegerField : a disk image passes
    # the 2 GB signed-32-bit ceiling routinely. Recorded even for an artefact
    # held elsewhere, so the register states the scale of what is held.
    file_size = models.PositiveBigIntegerField(
        _("File size (bytes)"),
        default=0,
    )
    content_hash = models.CharField(
        _("Content hash"),
        max_length=128,
        blank=True,
        default="",
        help_text=_(
            "Hex digest of the acquired item : an integrity fingerprint, not a "
            "hash chain. It proves this item has not changed since acquisition "
            "and claims nothing about any other item."
        ),
    )
    hash_algorithm = models.CharField(
        _("Hash algorithm"),
        max_length=16,
        choices=HashAlgorithm.choices,
        default=HashAlgorithm.SHA256,
        help_text=_(
            "Recorded because a 2019 MD5 digest must stay verifiable in 2026."
        ),
    )
    sealed_at = models.DateTimeField(
        _("Sealed at"),
        null=True,
        blank=True,
        help_text=_(
            "Stamped by the sealing transition. After this instant the "
            "acquisition metadata is frozen."
        ),
    )
    last_integrity_check_at = models.DateTimeField(
        _("Last integrity check"),
        null=True,
        blank=True,
        help_text=_(
            "When a verification was last attempted, whatever its outcome, "
            "including one that could not conclude."
        ),
    )
    last_integrity_check_ok = models.BooleanField(
        _("Last integrity check verdict"),
        null=True,
        blank=True,
        help_text=_(
            "Verdict of the last conclusive verification. Empty means never "
            "checked : a verification that could not read the artefact leaves "
            "this unchanged rather than recording a break."
        ),
    )
    tlp = models.CharField(
        _("Handling caveat"),
        max_length=16,
        choices=TrafficLightProtocol.choices,
        default=TrafficLightProtocol.RED,
        help_text=_(
            "Defaults stricter than the incident's : an artefact usually holds "
            "more than the incident summary does. Loosen it deliberately."
        ),
    )
    legal_hold = models.BooleanField(
        _("Legal hold"),
        default=False,
        db_index=True,
        help_text=_(
            "Blocks destruction outright, whatever the retention date says."
        ),
    )
    retention_until = models.DateField(
        _("Retention until"),
        null=True,
        blank=True,
        db_index=True,
        help_text=_(
            "Date after which destruction is permitted. A permission to "
            "destroy, never an instruction : nothing here destroys anything "
            "automatically."
        ),
    )
    admissibility_notes = models.TextField(
        _("Admissibility notes"),
        blank=True,
        default="",
        help_text=_(
            "Which court or authority the item may be produced to, which "
            "chain-of-custody form was countersigned, which counsel was "
            "consulted."
        ),
    )
    destruction_authorised_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="authorised_evidence_destructions",
        verbose_name=_("Destruction authorised by"),
        help_text=_("Stamped by the destruction transition, never editable."),
    )

    history = HistoricalRecords()

    class Meta:
        verbose_name = _("Evidence item")
        verbose_name_plural = _("Evidence items")
        # The register reads in acquisition order within an incident, which is
        # the order a forensics report is written in.
        ordering = ["incident", "collected_at"]
        constraints = [
            # The same artefact is never registered twice against the same
            # incident. `content_hash` is a non-null CharField with a blank
            # default, so two unhashed rows would collide on '' rather than
            # being treated as distinct : the condition exempts them explicitly
            # instead of relying on NULL distinctness.
            models.UniqueConstraint(
                fields=["incident", "content_hash"],
                condition=~models.Q(content_hash=""),
                name="unique_evidence_hash_per_incident",
            ),
            # A sealed item with no fingerprint is not sealed.
            models.CheckConstraint(
                condition=(
                    models.Q(sealed_at__isnull=True) | ~models.Q(content_hash="")
                ),
                name="evidence_sealed_requires_hash",
            ),
        ]

    def __str__(self):
        return f"{self.reference} - {self.title}"

    @property
    def workflow_perm_namespace(self):
        """Mandatory override : the default would grant nobody anything.

        ``app_label.model_name`` spells ``incidents.incidentevidence``, which
        matches no feature in ``accounts.constants.PERMISSION_REGISTRY``, so
        every lifecycle permission check on this entity would silently evaluate
        against a codename nobody holds.
        """
        return "incidents.evidence"

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
    def collected_by_name(self):
        """Display name of the acquirer (read-only output)."""
        return self.collected_by.display_name if self.collected_by_id else ""

    @property
    def source_support_asset_name(self):
        """Name of the registered source asset (read-only output)."""
        return (
            self.source_support_asset.name if self.source_support_asset_id else ""
        )

    @property
    def source_support_asset_reference(self):
        """Reference of the registered source asset (read-only output)."""
        return (
            self.source_support_asset.reference
            if self.source_support_asset_id
            else ""
        )

    @property
    def destruction_authorised_by_name(self):
        """Display name of whoever authorised the disposal (read-only output)."""
        return (
            self.destruction_authorised_by.display_name
            if self.destruction_authorised_by_id
            else ""
        )

    @property
    def has_file(self):
        """Whether Cairn holds the artefact itself.

        The list and the detail page render *Held in Cairn* and *Registered by
        reference* as two visually distinct states, so a reader of a green
        integrity column always knows which of the two claims it is making.
        """
        return bool(self.file and self.file.name)

    @property
    def is_registered_by_reference(self):
        """Whether the platform holds only the fingerprint, not the artefact."""
        return not self.has_file

    @property
    def is_sealed(self):
        """Whether the acquisition metadata is frozen."""
        return self.sealed_at is not None

    @property
    def retention_expired(self):
        """Whether the retention date is set and strictly in the past."""
        if self.retention_until is None:
            return False
        return self.retention_until < timezone.localdate()

    @property
    def is_destroyable(self):
        """Whether GE-04's data conditions are met, for the UI to read.

        Deliberately a mirror of the server-side gate rather than its
        replacement : the gate below is what actually refuses the transition,
        identically for a DRF or MCP caller that never sees a button.
        """
        return not self.legal_hold and self.retention_expired

    # --- Sealing : write-once acquisition metadata (RG-INC-20) -------------

    def save(self, *args, **kwargs):
        """Refuse any change to the acquisition metadata of a sealed item.

        The stored row is re-read and compared field by field, so the guard
        applies to the web form, the DRF serializer, the MCP update tool and
        the Django admin at once rather than being reproduced in four places.
        Sealing itself passes : the stored row is still unsealed at that
        instant, and the freeze applies from the next write onwards.

        What bypasses this, stated rather than glossed : ``QuerySet.update()``,
        ``bulk_update()``, raw SQL and a ``manage.py shell`` session never call
        ``save()``. ``HistoricalRecords`` is what turns that prevention gap into
        detection.
        """
        if not self._state.adding and self.pk:
            self._assert_frozen_fields_unchanged()
        super().save(*args, **kwargs)

    def _assert_frozen_fields_unchanged(self):
        stored = type(self)._base_manager.filter(pk=self.pk).first()
        if stored is None:
            return

        errors = {}
        # GE-06 : the transition stamps are write-once on every path, sealed or
        # not. They are the record of who decided what and when.
        if stored.sealed_at is not None and self.sealed_at != stored.sealed_at:
            errors["sealed_at"] = _("The sealing timestamp is written once.")
        if (
            stored.destruction_authorised_by_id is not None
            and self.destruction_authorised_by_id
            != stored.destruction_authorised_by_id
        ):
            errors["destruction_authorised_by"] = _(
                "The destruction authorisation is written once."
            )

        if stored.sealed_at is not None:
            for field in EVIDENCE_ACQUISITION_FIELDS:
                if field == "file":
                    # The destruction transition is the only path allowed to
                    # clear the artefact after sealing, and it does so itself.
                    if self._destroying:
                        continue
                    if (self.file.name or "") != (stored.file.name or ""):
                        errors["file"] = _(
                            "The artefact of a sealed evidence item cannot be "
                            "replaced. Destruction is a transition, not an edit."
                        )
                    continue
                attname = self._meta.get_field(field).attname
                if getattr(self, attname) != getattr(stored, attname):
                    errors[field] = _(
                        "This field is frozen : the evidence item was sealed on "
                        "%(sealed_at)s."
                    ) % {"sealed_at": stored.sealed_at}
        if errors:
            raise ValidationError(errors)

    @property
    def _destroying(self):
        """Whether the destruction transition is mid-flight on this instance."""
        return getattr(self, "_destruction_in_progress", False)

    # --- Lifecycle ---------------------------------------------------------

    def stage_custody_details(
        self,
        *,
        counterparty=None,
        counterparty_organisation=None,
        location=None,
    ):
        """Carry the counterparty of a release or a disposal into the transition.

        ``BaseModel.transition_to()`` has a fixed signature that the generic
        stepper endpoint, the DRF mixin and the MCP handler all call, so the
        release and destruction forms stage their extra fields on the instance
        first. :meth:`transition_to` also accepts them directly, for a caller
        that has them to hand.
        """
        self._pending_custody = {
            "counterparty": (counterparty or "").strip(),
            "counterparty_organisation": (counterparty_organisation or "").strip(),
            "location": (location or "").strip(),
        }
        return self._pending_custody

    def _custody_details(self, counterparty, counterparty_organisation, location):
        staged = getattr(self, "_pending_custody", {}) or {}
        return {
            "counterparty": (
                counterparty
                if counterparty is not None
                else staged.get("counterparty", "")
            ).strip(),
            "counterparty_organisation": (
                counterparty_organisation
                if counterparty_organisation is not None
                else staged.get("counterparty_organisation", "")
            ).strip(),
            "location": (
                location
                if location is not None
                else staged.get("location", "") or self.storage_location
            ).strip(),
        }

    def transition_to(
        self,
        target,
        user=None,
        comment=None,
        *,
        enforce_permission=False,
        save=True,
        counterparty=None,
        counterparty_organisation=None,
        location=None,
    ):
        """Apply the A.5.28 gates, stamp the write-once fields, then move.

        The whole body runs in one transaction, so a refusal leaves neither a
        stamp nor a ledger row, and a committed transition leaves exactly one
        custody row for every handling act (RG-INC-22).

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
        details = self._custody_details(
            counterparty, counterparty_organisation, location
        )
        with transaction.atomic():
            self._check_transition_gates(current, target, details)
            self._stamp_transition(current, target, user)
            try:
                result = super().transition_to(
                    target, user, comment=comment,
                    enforce_permission=enforce_permission, save=save,
                )
            finally:
                self._destruction_in_progress = False
            self._append_custody_event(current, target, user, comment, details)
        self._pending_custody = {}
        return result

    def _check_transition_gates(self, current, target, details):
        """Refuse the moves the evidence register must never record."""
        # GE-01 : an acquisition with no attributed acquirer, no timestamp or
        # no stated origin is not an acquisition.
        if target == STEP_COLLECTED:
            if not self.evidence_type or self.collected_at is None:
                raise DomainRefusalError(
                    str(_(
                        "Registering an acquisition requires an evidence type "
                        "and a collection timestamp."
                    ))
                )
            if self.collected_by_id is None:
                raise DomainRefusalError(
                    str(_("Registering an acquisition requires a named acquirer."))
                )
            if not self.source_support_asset_id and not self.source_description.strip():
                raise DomainRefusalError(
                    str(_(
                        "Registering an acquisition requires its origin : a "
                        "registered support asset or a described source."
                    ))
                )

        # GE-02 (RG-INC-21) : there is no path to `secured` without both.
        if target == STEP_SECURED:
            if not self.content_hash.strip() or not self.collection_method.strip():
                raise DomainRefusalError(
                    str(_(
                        "Sealing evidence requires a content hash and a stated "
                        "collection method. An artefact with a perfect hash and "
                        "no method is a file, not evidence."
                    ))
                )

        # GE-03 : releasing an artefact to nobody in particular is not a release.
        if target == STEP_RELEASED and not details["counterparty"]:
            raise DomainRefusalError(
                str(_(
                    "Releasing evidence requires the named person receiving "
                    "custody of it."
                ))
            )

        # GE-04 (RG-INC-24) : evaluated server-side, so a DRF or MCP caller that
        # never sees the confirmation modal is refused identically.
        if target == STEP_DESTROYED:
            if self.legal_hold:
                raise DomainRefusalError(
                    str(_(
                        "This evidence item is under legal hold and cannot be "
                        "destroyed, whatever its retention date."
                    ))
                )
            if self.retention_until is None:
                raise DomainRefusalError(
                    str(_(
                        "Destroying evidence requires a retention date, and it "
                        "must have passed."
                    ))
                )
            if not self.retention_expired:
                raise DomainRefusalError(
                    str(_(
                        "The retention period of this evidence item has not "
                        "expired yet."
                    ))
                )
            if not details["counterparty"]:
                raise DomainRefusalError(
                    str(_(
                        "Destroying evidence requires the named disposal "
                        "service, witness or person who performed it."
                    ))
                )

        # GE-05 : the restore bookend is the one edge that could walk a sealed
        # A.5.28 row back into the single deletable step. It is refused for any
        # row the immutable ledger shows has ever left `draft`.
        if current == STEP_ARCHIVED and target == STEP_DRAFT and self._has_left_draft():
            raise DomainRefusalError(
                str(_(
                    "An evidence item that was registered as collected cannot "
                    "be restored to a draft registration."
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

    def _stamp_transition(self, current, target, user):
        """Write the fields the lifecycle owns, and only it (GE-06, RG-INC-12)."""
        if target == STEP_SECURED and self.sealed_at is None:
            self.sealed_at = timezone.now()
        if target == STEP_DESTROYED:
            if self.destruction_authorised_by_id is None and user is not None:
                self.destruction_authorised_by = user
            self._destroy_stored_artefact()

    def _destroy_stored_artefact(self):
        """Clear the stored artefact, keeping the record of what was destroyed.

        ``original_filename``, ``file_size``, ``content_hash`` and
        ``hash_algorithm`` are deliberately retained : the register must still
        be able to state *what* it disposed of. A registered-by-reference item
        goes through the same transition with nothing to clear, and the ledger
        records that the disposal is attested rather than performed by Cairn.

        The bytes are removed **on commit**, not inline : a rolled-back
        destruction must not leave the artefact gone from the volume.
        """
        self._destruction_in_progress = True
        if not self.has_file:
            return
        name = self.file.name
        storage = self.file.storage
        self.file = None
        transaction.on_commit(lambda: storage.delete(name))

    def _append_custody_event(self, current, target, user, comment, details):
        """Append the one ledger row a handling act owes (RG-INC-22).

        Three edges are **not** handling acts and append nothing : the two
        Retain edges, because moving an item into its retention period changes
        how the platform governs it and not who is holding it (there is no
        ``retained`` value in ``CustodyAction``), and the archive and restore
        bookends, which are governance rather than custody.

        ``secured -> analysed`` appends an ``accessed`` row : ``CustodyAction``
        carries no ``analysed`` value, and what the ledger has to record about
        an examination is that somebody handled the artefact. The transition
        comment is carried into ``notes`` so the row says what was examined.
        """
        if target == STEP_COLLECTED:
            EvidenceCustodyEvent.record_lifecycle_act(
                self,
                action=CustodyAction.COLLECTED,
                actor=self.collected_by or user,
                occurred_at=self.collected_at,
                location=self.storage_location,
                notes=comment or "",
            )
        elif target == STEP_SECURED:
            EvidenceCustodyEvent.record_lifecycle_act(
                self,
                action=CustodyAction.SEALED,
                actor=user or self.collected_by,
                # The digest is copied from the now-frozen fingerprint.
                # `integrity_ok` stays null : sealing measures, it does not
                # verify.
                hash_at_event=self.content_hash,
                location=self.storage_location,
                notes=comment or "",
            )
        elif target == STEP_ANALYSED:
            EvidenceCustodyEvent.record_lifecycle_act(
                self,
                action=CustodyAction.ANALYSED,
                actor=user or self.collected_by,
                location=self.storage_location,
                notes=comment or "",
            )
        elif target == STEP_RELEASED:
            EvidenceCustodyEvent.record_lifecycle_act(
                self,
                action=CustodyAction.RELEASED,
                actor=user or self.collected_by,
                counterparty=details["counterparty"],
                counterparty_organisation=details["counterparty_organisation"],
                location=details["location"],
                notes=comment or "",
            )
        elif target == STEP_DESTROYED:
            EvidenceCustodyEvent.record_lifecycle_act(
                self,
                action=CustodyAction.DESTROYED,
                actor=user or self.collected_by,
                counterparty=details["counterparty"],
                counterparty_organisation=details["counterparty_organisation"],
                location=details["location"],
                notes=comment or "",
            )

    # --- Integrity verification (RG-INC-23) --------------------------------

    def verify_integrity(self, actor, *, notes=""):
        """Re-measure the artefact, append the ledger row, return the outcome.

        Three outcomes, and the third is never collapsed into the second:

        - ``match`` : the artefact was read and the digest equals
          ``content_hash``. The verdict is recorded on both rows.
        - ``mismatch`` : the artefact was read and the digest differs. That is a
          chain-of-custody break, it is permanent, and the caller fires
          ``EVIDENCE_INTEGRITY_FAILED``.
        - ``not_verifiable`` : the item is registered by reference, or the file
          is referenced but missing or unreadable. ``integrity_ok`` stays null
          and ``last_integrity_check_ok`` is **left unchanged**.

        The third outcome is structural, not cosmetic. A restored database
        paired with a lost media volume makes every inline artefact unreadable
        at once ; recording that as a mismatch would write a permanent break
        into the append-only ledger of every evidence item in the platform on a
        day when nothing was tampered with, and the rows could never be removed.
        A mismatch is a claim about the artefact ; a missing volume is a claim
        about the infrastructure, and the alert belongs to whoever can remount
        it.

        ``last_integrity_check_at`` is stamped in all three cases : an attempt
        that could not conclude is still a dated attempt, and the register
        should say when it was last tried. Notifying is the caller's job : this
        method owns the measurement and the ledger, not the routing.
        """
        digest, failure = self._measure_digest()
        if digest is None:
            outcome = VERIFICATION_NOT_VERIFIABLE
            integrity_ok = None
        else:
            integrity_ok = digest == self.content_hash.strip().lower()
            outcome = VERIFICATION_MATCH if integrity_ok else VERIFICATION_MISMATCH

        row_notes = notes
        if failure:
            row_notes = f"{notes}\n{failure}".strip() if notes else failure

        with transaction.atomic():
            EvidenceCustodyEvent.objects.create(
                evidence=self,
                action=CustodyAction.INTEGRITY_VERIFIED,
                occurred_at=timezone.now(),
                actor=actor,
                hash_at_event=digest or "",
                integrity_ok=integrity_ok,
                location=self.storage_location,
                notes=row_notes,
                source=TimelineEntrySource.LIFECYCLE,
            )
            self.last_integrity_check_at = timezone.now()
            updated = ["last_integrity_check_at", "updated_at"]
            if integrity_ok is not None:
                self.last_integrity_check_ok = integrity_ok
                updated.append("last_integrity_check_ok")
            self.save(update_fields=updated)
        return outcome

    def _measure_digest(self):
        """Return ``(hex digest, failure reason)``, the digest being None if unread.

        Read in slices : a disk image is never pulled into memory whole just to
        be re-hashed. The legacy algorithms are re-measured because that is what
        the record was made with ; nothing here ever *chooses* one.
        """
        if not self.has_file:
            return None, str(_(
                "The artefact is registered by reference : Cairn holds its "
                "fingerprint, not the item. Verify it at its storage location "
                "and record the result by hand."
            ))
        try:
            digest = hashlib.new(self.hash_algorithm)
            with self.file.open("rb") as handle:
                for chunk in iter(lambda: handle.read(_HASH_CHUNK_BYTES), b""):
                    digest.update(chunk)
        except (OSError, ValueError) as exc:
            return None, str(_(
                "The artefact could not be read : %(error)s. This is a claim "
                "about the storage, not about the item."
            )) % {"error": exc}
        finally:
            if self.file:
                self.file.close()
        return digest.hexdigest().lower(), ""


class EvidenceCustodyEvent(models.Model):
    """One append-only handling act on an evidence item.

    Not a ``BaseModel``, and each reason is load-bearing:

    **No lifecycle.** A custody act has no states : *"14:03, image handed to
    Forensics SARL, seal 44821, hash re-measured, matched"* is never draft,
    never pending, never validated. A lifecycle would wrap an approval workflow
    around a fact that has already happened, and would let a custody row exist
    in a step where it does not count. The entity therefore carries no
    ``workflow_state`` at all and is deliberately invisible to ``reportable()``,
    ``linkable()`` and ``deletable_states()`` : it is always read through its
    parent.

    **No reference prefix.** ``_generate_next_reference()`` scans every existing
    reference sharing a prefix on each insert. That is the wrong shape for a
    ledger taking a row on every transition, every transfer and every re-hash
    across the whole register, for an identifier nobody cites : custody rows are
    cited by their parent's reference and their ``occurred_at``, and addressed
    by UUID everywhere.

    **Never edited, never deleted.** A custody ledger that can be rewritten is
    not a custody ledger. ``save()`` refuses a write against an existing row and
    ``delete()`` refuses outright. A mistake is corrected by appending a further
    row whose ``notes`` state what the earlier one got wrong ; the earlier row
    is never touched.

    There is deliberately **no hash chain** (RG-INC-22). Nothing in Cairn
    hash-chains anything ; an HMAC keyed on ``SECRET_KEY`` would read as
    tampering on every row after a routine key rotation, and a chain would prove
    that the rows were not reordered in the database while saying nothing about
    whether the artefact in the vault is the one that was acquired. That second
    question is what ``hash_at_event`` and a measurement answer.
    """

    # A grandchild of a scoped model chains the lookup (RG-INC-38). A custody
    # ledger names people at other organisations : this is arguably the most
    # sensitive read in the module.
    scope_parent_lookup = "evidence__incident__scopes"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    evidence = models.ForeignKey(
        IncidentEvidence,
        on_delete=models.PROTECT,
        related_name="custody_events",
        verbose_name=pgettext_lazy("incident", "Evidence"),
        help_text=_(
            "The item whose handling is being recorded. Protected on delete, so "
            "an evidence row that has ever been handled can never be deleted, "
            "whatever any other guard does."
        ),
    )
    action = models.CharField(
        _("Action"),
        max_length=32,
        choices=CustodyAction.choices,
        db_index=True,
    )
    occurred_at = models.DateTimeField(
        _("Occurred at"),
        db_index=True,
        help_text=_(
            "Real-world time of the act. This is the ordering key : the ledger "
            "reads in the order things happened, not in the order they were "
            "typed."
        ),
    )
    recorded_at = models.DateTimeField(
        _("Recorded at"),
        auto_now_add=True,
        help_text=_(
            "When the row was logged. A gap with the occurrence time is normal "
            "and is itself evidence of how promptly the ledger was kept."
        ),
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="evidence_custody_events",
        verbose_name=_("Actor"),
        help_text=_(
            "The user performing or witnessing the act. Protected on delete : a "
            "custody act attributed to a deleted account is a custody act "
            "attributed to nobody."
        ),
    )
    counterparty = models.CharField(
        _("Counterparty"),
        max_length=255,
        blank=True,
        default="",
        help_text=_(
            "The named person receiving or relinquishing custody. A handover to "
            "an organisation with no named individual is not a handover."
        ),
    )
    counterparty_organisation = models.CharField(
        _("Counterparty organisation"),
        max_length=255,
        blank=True,
        default="",
        help_text=_(
            "Free text rather than a supplier link : a police force, a bailiff "
            "or a data subject's counsel is not a supplier, and filing them in "
            "the supplier register would pollute it."
        ),
    )
    location = models.CharField(
        _("Location"),
        max_length=500,
        blank=True,
        default="",
        help_text=_(
            "Where the act took place, or where the item went : safe number, "
            "evidence-bag identifier, address, rack, bucket and object key."
        ),
    )
    hash_at_event = models.CharField(
        _("Hash at event"),
        max_length=128,
        blank=True,
        default="",
        help_text=_(
            "The digest measured at this act, not copied from the parent. This "
            "is the column that makes the ledger falsifiable : a row claiming a "
            "verification without a measurement is rejected."
        ),
    )
    integrity_ok = models.BooleanField(
        _("Integrity verdict"),
        null=True,
        blank=True,
        help_text=_(
            "Whether the measured digest matched the parent's. Empty when the "
            "act involved no verification, and also when a verification was "
            "attempted but the artefact could not be read."
        ),
    )
    notes = models.TextField(
        _("Notes"),
        blank=True,
        default="",
        help_text=_(
            "Seal number, transport conditions, packaging, witness names, the "
            "reason a read could not be completed, or what an earlier row got "
            "wrong."
        ),
    )
    source = models.CharField(
        _("Source"),
        max_length=20,
        choices=TimelineEntrySource.choices,
        default=TimelineEntrySource.MANUAL,
        help_text=_(
            "Whether the row was appended by a lifecycle transition or recorded "
            "by hand."
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
        verbose_name = _("Custody event")
        verbose_name_plural = _("Custody events")
        # Two acts can legitimately share an occurrence minute (a transfer
        # recorded by both parties), so the recording time breaks the tie
        # deterministically and the exported ledger is stable between two
        # renders of the same evidence file.
        ordering = ["evidence", "occurred_at", "recorded_at"]

    def __str__(self):
        return f"{self.occurred_at:%Y-%m-%d %H:%M} - {self.get_action_display()}"

    # --- Read-only display helpers (API / assistant output) ----------------

    @property
    def evidence_reference(self):
        """Reference of the item being handled (read-only output)."""
        return self.evidence.reference if self.evidence_id else ""

    @property
    def evidence_name(self):
        """Title of the item being handled (read-only output)."""
        return self.evidence.title if self.evidence_id else ""

    @property
    def incident_reference(self):
        """Reference of the incident the item belongs to (read-only output)."""
        return self.evidence.incident_reference if self.evidence_id else ""

    @property
    def actor_name(self):
        """Display name of whoever performed or witnessed the act."""
        return self.actor.display_name if self.actor_id else ""

    @property
    def is_verification(self):
        """Whether this row is an integrity verification."""
        return self.action == CustodyAction.INTEGRITY_VERIFIED

    @property
    def verification_outcome(self):
        """The three-way verdict of a verification row, or an empty string.

        Rendered as three visually distinct states and never two : a success
        tick, a danger badge for a break, and a warning badge for an artefact
        that could not be read.
        """
        if not self.is_verification:
            return ""
        if self.integrity_ok is None:
            return VERIFICATION_NOT_VERIFIABLE
        return VERIFICATION_MATCH if self.integrity_ok else VERIFICATION_MISMATCH

    @property
    def recording_delay(self):
        """``recorded_at - occurred_at`` : how long the act went unrecorded.

        Derived rather than stored. A transfer that happened on Friday and was
        recorded on Monday is legitimate, and the gap is itself information the
        auditor is entitled to see, so the UI shows both timestamps whenever
        they differ by more than a few minutes and never hides the delay.
        """
        if self.recorded_at is None or self.occurred_at is None:
            return None
        return self.recorded_at - self.occurred_at

    # --- Validation --------------------------------------------------------

    def clean(self):
        """Keep the ledger a chain : forward in time, named, and measured.

        Called from the form, the serializer and the MCP handler. Like
        everything else here it is prevention at application level : a row
        inserted by raw SQL out of order stays detectable when the ledger is
        read, since the export renders ``occurred_at`` and ``recorded_at`` side
        by side.
        """
        super().clean()
        errors = {}

        if self.action in CUSTODY_ACTIONS_REQUIRING_COUNTERPARTY and not (
            self.counterparty or ""
        ).strip():
            errors["counterparty"] = _(
                "This act moves custody : name the person receiving or "
                "relinquishing it."
            )

        if (
            self.is_verification
            and self.integrity_ok is not None
            and not (self.hash_at_event or "").strip()
        ):
            errors["hash_at_event"] = _(
                "A conclusive verification records the digest it measured. A row "
                "claiming a verdict without a measurement is not a verification."
            )
            # A verification that could NOT read the artefact leaves both
            # `integrity_ok` and `hash_at_event` empty on purpose : a missing
            # file is an operational failure, not a chain-of-custody break, and
            # recording it as one would cry wolf on every lost media volume.

        if self.occurred_at and self.evidence_id:
            # Equality is allowed on purpose : two acts genuinely occur in the
            # same minute, and forcing a strict ordering would push operators
            # into falsifying a timestamp to get a row saved.
            latest = (
                EvidenceCustodyEvent.objects.filter(evidence_id=self.evidence_id)
                .exclude(pk=self.pk)
                .order_by("-occurred_at")
                .values_list("occurred_at", flat=True)
                .first()
            )
            if latest is not None and self.occurred_at < latest:
                errors["occurred_at"] = _(
                    "A chain of custody cannot jump backwards : this act "
                    "predates the last recorded one."
                )

        if errors:
            raise ValidationError(errors)

    # --- Append-only guards ------------------------------------------------

    def save(self, *args, **kwargs):
        """Insert only : a chain of custody that can be rewritten is not one.

        Enforced at application level. The bypasses, and what detects them, are
        set out in the class docstring.
        """
        if not self._state.adding:
            raise LifecycleProtectedError(
                "The chain of custody is append-only : correct an entry by "
                "appending a further act stating what the earlier one got wrong."
            )
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """Refuse deletion outright : there is no delete route on any surface."""
        raise LifecycleProtectedError(
            "A custody event is never deleted : the ledger is append-only."
        )

    # --- Appending ---------------------------------------------------------

    @classmethod
    def record_lifecycle_act(
        cls,
        evidence,
        *,
        action,
        actor,
        occurred_at=None,
        counterparty="",
        counterparty_organisation="",
        location="",
        hash_at_event="",
        integrity_ok=None,
        notes="",
    ):
        """Append the one row a parent handling transition owes (RG-INC-22).

        Called from :meth:`IncidentEvidence.transition_to` inside the
        transition's own transaction, so a rolled-back transition leaves no row
        and a committed one leaves precisely one. Written here rather than
        inline at the call site so the shape of an automatic row - its source
        and its ordering timestamp - is decided in one place and cannot drift
        from the hand-recorded rows it sits beside.

        The actor is required : an unattributed act is not a custody act. The
        parent's GE-01 gate guarantees a named acquirer before any handling
        transition is reachable, so the fallback chain always resolves.
        """
        if actor is None:
            raise DomainRefusalError(
                str(_(
                    "Recording a custody act requires the acting user : an "
                    "unattributed handling act is not a chain of custody."
                ))
            )
        return cls.objects.create(
            evidence=evidence,
            action=action,
            occurred_at=occurred_at or timezone.now(),
            actor=actor,
            counterparty=counterparty or "",
            counterparty_organisation=counterparty_organisation or "",
            location=location or "",
            hash_at_event=hash_at_event or "",
            integrity_ok=integrity_ok,
            notes=notes or "",
            source=TimelineEntrySource.LIFECYCLE,
        )
