# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""How a control is tested (ISO/IEC 27001:2022 clause 9.1).

The next due date is derived (RG-CTL-07). See docs/specs/m8-controls/control-test.md.
"""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models, transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy
from simple_history.models import HistoricalRecords

from context.models.base import BaseModel
from controls.constants import (
    CONTROL_IMPLEMENTED,
    CONTROL_PLANNED,
    DEFAULT_TEST_FREQUENCY_MONTHS,
    MAX_TEST_FREQUENCY_MONTHS,
    REFERENCE_PREFIXES,
    RUN_VALIDATED,
    TEST_ACTIVE,
    TEST_RETIRED,
    ControlTestMethod,
)
from documents.models.policy import add_months


class ControlTest(BaseModel):
    """A test of a :class:`~controls.models.control.Control`."""

    REFERENCE_PREFIX = REFERENCE_PREFIXES["ControlTest"]
    LIFECYCLE_NAME = "control_test"
    scope_parent_lookup = "control__scopes"

    control = models.ForeignKey(
        "controls.Control", on_delete=models.PROTECT, related_name="tests", verbose_name=pgettext_lazy("control", "Control"),
    )
    name = models.CharField(_("Name"), max_length=255)
    objective = models.TextField(_("Objective"), blank=True, default="")
    method = models.CharField(
        _("Method"), max_length=20, choices=ControlTestMethod.choices, default=ControlTestMethod.INSPECTION,
    )
    procedure = models.TextField(_("Procedure"), blank=True, default="")
    acceptance_criteria = models.TextField(_("Acceptance criteria"), blank=True, default="")
    frequency_months = models.PositiveSmallIntegerField(
        _("Frequency (months)"), default=DEFAULT_TEST_FREQUENCY_MONTHS,
        validators=[MinValueValidator(1), MaxValueValidator(MAX_TEST_FREQUENCY_MONTHS)],
    )
    tester = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="control_tests", verbose_name=_("Tester"),
    )
    first_due_date = models.DateField(_("First due date"), null=True, blank=True)
    # Derived (RG-CTL-07), stored for the calendar, the dashboard and the sweep.
    next_due_date = models.DateField(_("Next due"), null=True, blank=True, db_index=True, editable=False)
    activated_on = models.DateField(_("Activated on"), null=True, blank=True, editable=False)
    last_reminded_at = models.DateTimeField(_("Last reminded at"), null=True, blank=True, editable=False)
    history = HistoricalRecords()

    class Meta(BaseModel.Meta):
        ordering = ["control", "name"]
        verbose_name = _("Control test")
        verbose_name_plural = _("Control tests")

    def __str__(self):
        return f"{self.reference} : {self.name}"

    @property
    def workflow_perm_namespace(self):
        return "controls.test"

    # --- Derived state ----------------------------------------------------

    @property
    def is_active(self):
        return self.workflow_state == TEST_ACTIVE

    @property
    def latest_validated_run(self):
        return (
            self.runs.filter(workflow_state=RUN_VALIDATED)
            .order_by("-performed_on", "-reviewed_at", "-created_at")
            .first()
        )

    @property
    def latest_result(self):
        run = self.latest_validated_run
        return run.result if run else None

    @property
    def is_overdue(self):
        return self.is_active and self.next_due_date is not None and self.next_due_date < timezone.localdate()

    def compute_next_due_date(self):
        """RG-CTL-07."""
        if not self.is_active:
            return None
        run = self.latest_validated_run
        if run is not None:
            return add_months(run.performed_on, self.frequency_months)
        return self.first_due_date or self.activated_on or timezone.localdate()

    def recompute_next_due_date(self):
        value = self.compute_next_due_date()
        if value == self.next_due_date:
            return False
        self.next_due_date = value
        type(self).objects.filter(pk=self.pk).update(next_due_date=value)
        return True

    # --- Integrity --------------------------------------------------------

    def clean(self):
        super().clean()
        if self.pk and self.control_id:
            stored = type(self).objects.filter(pk=self.pk).values_list("control_id", flat=True).first()
            if stored and stored != self.control_id and self.runs.exists():
                raise ValidationError({"control": _("A test that has runs cannot move to another control.")})

    def save(self, *args, **kwargs):
        if self.pk and not self._state.adding and self.control_id:
            stored = type(self).objects.filter(pk=self.pk).values_list("control_id", flat=True).first()
            if stored and stored != self.control_id and self.runs.exists():
                raise ValidationError(_("A test that has runs cannot move to another control."))
        # Keep the derived date in step with frequency / first due date edits.
        if self.pk and not self._state.adding:
            self.next_due_date = self.compute_next_due_date()
        super().save(*args, **kwargs)

    # --- Lifecycle side effects (RG-CTL-06, RG-CTL-08) --------------------

    def transition_to(self, target, user=None, comment=None, *, enforce_permission=False, save=True):
        from controls.models.control import Control
        from core.lifecycle import DomainRefusalError

        with transaction.atomic():
            control = Control.objects.select_for_update().get(pk=self.control_id)
            if target == TEST_ACTIVE:
                if control.workflow_state not in (CONTROL_PLANNED, CONTROL_IMPLEMENTED):
                    raise DomainRefusalError(_("Plan or implement the control before activating its tests."))
                if not (self.procedure or "").strip() or not (self.acceptance_criteria or "").strip():
                    raise DomainRefusalError(_("A test needs a procedure and acceptance criteria before it can be activated."))
                self.activated_on = timezone.localdate()
            result = super().transition_to(target, user, comment=comment, enforce_permission=enforce_permission, save=save)
            if save:
                self.recompute_next_due_date()
                if target in (TEST_ACTIVE, TEST_RETIRED):
                    control.recompute_effectiveness()
        return result
