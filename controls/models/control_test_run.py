# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""One execution of a control test (ISO/IEC 27001:2022 clause 9.1, 9.2, 10.2).

Frozen once submitted (RG-CTL-09), validated by someone other than its
performer (RG-CTL-11); validation drives the test's next due date and the
control's effectiveness (RG-CTL-12). See docs/specs/m8-controls/control-test-run.md.
"""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

from context.models.base import BaseModel
from controls.constants import (
    REFERENCE_PREFIXES,
    RUN_DRAFT,
    RUN_IN_REVIEW,
    RUN_VALIDATED,
    RUN_WITHDRAWN,
    TEST_ACTIVE,
    RunResult,
)

FROZEN_FIELDS = (
    "test_id", "performed_by_id", "performed_on", "period_start", "period_end",
    "sample_description", "result", "observations",
)


class ControlTestRun(BaseModel):
    """A run of a :class:`~controls.models.control_test.ControlTest`."""

    REFERENCE_PREFIX = REFERENCE_PREFIXES["ControlTestRun"]
    LIFECYCLE_NAME = "control_test_run"
    scope_parent_lookup = "test__control__scopes"

    test = models.ForeignKey(
        "controls.ControlTest", on_delete=models.PROTECT, related_name="runs", verbose_name=_("Test"),
    )
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="control_test_runs",
        verbose_name=_("Performed by"),
    )
    performed_on = models.DateField(_("Performed on"), default=timezone.localdate)
    period_start = models.DateField(_("Period start"), null=True, blank=True)
    period_end = models.DateField(_("Period end"), null=True, blank=True)
    sample_description = models.TextField(_("Sample"), blank=True, default="")
    result = models.CharField(_("Result"), max_length=10, choices=RunResult.choices, blank=True, default="")
    observations = models.TextField(_("Observations"), blank=True, default="")
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="reviewed_control_test_runs", verbose_name=_("Reviewed by"), editable=False,
    )
    reviewed_at = models.DateTimeField(_("Reviewed at"), null=True, blank=True, editable=False)
    history = HistoricalRecords()

    class Meta(BaseModel.Meta):
        ordering = ["-performed_on", "-created_at"]
        verbose_name = _("Test run")
        verbose_name_plural = _("Test runs")

    def __str__(self):
        return f"{self.reference} : {self.test.name} ({self.performed_on.isoformat()})"

    @property
    def workflow_perm_namespace(self):
        return "controls.test"

    @property
    def control(self):
        return self.test.control

    @property
    def is_frozen(self):
        return self.workflow_state not in (RUN_DRAFT, "", None)

    @property
    def needs_finding(self):
        """RG-CTL-16 : a validated partial / failed run without its finding yet."""
        return (
            self.workflow_state == RUN_VALIDATED
            and self.result in (RunResult.PARTIAL, RunResult.FAIL)
            and not self.findings.exists()
        )

    # --- Integrity (RG-CTL-09, RG-CTL-10) ---------------------------------

    def _period_errors(self):
        errors = {}
        today = timezone.localdate()
        if self.performed_on and self.performed_on > today:
            errors["performed_on"] = _("The test date cannot be in the future.")
        if self.period_start and self.period_end and self.period_start > self.period_end:
            errors["period_end"] = _("The period cannot end before it starts.")
        if self.period_end and self.performed_on and self.period_end > self.performed_on:
            errors["period_end"] = _("The period tested cannot end after the test date.")
        return errors

    def clean(self):
        super().clean()
        errors = self._period_errors()
        if self._state.adding and self.test_id and self.test.workflow_state != TEST_ACTIVE:
            errors["test"] = _("Runs can only be recorded against an active test.")
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if self._state.adding and self.test_id:
            from controls.models.control_test import ControlTest

            state = ControlTest.objects.filter(pk=self.test_id).values_list("workflow_state", flat=True).first()
            if state != TEST_ACTIVE:
                raise ValidationError(_("Runs can only be recorded against an active test."))
        elif self.pk:
            stored = type(self).objects.filter(pk=self.pk).values("workflow_state", *FROZEN_FIELDS).first()
            if stored and stored["workflow_state"] != RUN_DRAFT:
                changed = [f for f in FROZEN_FIELDS if stored[f] != getattr(self, f)]
                if changed:
                    raise ValidationError(_("A submitted test run is frozen : its content can no longer be changed."))
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        # Only a draft run is deletable (lifecycle governance); its evidence goes
        # with it, file included, while the run is still open (RG-CTL-13).
        with transaction.atomic():
            for item in self.evidence.all():
                item.delete()
            return super().delete(*args, **kwargs)

    # --- Lifecycle side effects (RG-CTL-10, -11, -12) ---------------------

    def transition_to(self, target, user=None, comment=None, *, enforce_permission=False, save=True):
        from controls.models.control import Control
        from core.lifecycle import DomainRefusalError

        with transaction.atomic():
            control = Control.objects.select_for_update().get(pk=self.test.control_id)
            if target == RUN_IN_REVIEW:
                if not self.result:
                    raise DomainRefusalError(_("Record the result of the test before submitting it."))
                if self.result != RunResult.PASS and not (self.observations or "").strip():
                    raise DomainRefusalError(_("Describe what was found : a partial or failed result needs observations."))
                errors = self._period_errors()
                if errors:
                    raise DomainRefusalError(" ".join(str(e) for e in errors.values()))
            if target == RUN_VALIDATED:
                # RG-CTL-11 : segregation of duties, superusers included. Only the
                # system path (no acting user, e.g. the seed) skips it.
                if user is None and enforce_permission:
                    raise DomainRefusalError(_("A test run is validated by a reviewer."))
                # The recorder too : otherwise anyone could record a run in a
                # colleague's name and validate it themselves.
                if user is not None and user.pk in (self.performed_by_id, self.created_by_id):
                    raise DomainRefusalError(_("The person who performed or recorded a test cannot validate it."))
                self.reviewed_by = user
                self.reviewed_at = timezone.now()
            result = super().transition_to(target, user, comment=comment, enforce_permission=enforce_permission, save=save)
            if not save:
                return result
            if target == RUN_IN_REVIEW and user is not None:
                from accounts.notifications import notify_lifecycle_submitted

                notify_lifecycle_submitted(self, actor=user)
            if target in (RUN_VALIDATED, RUN_WITHDRAWN):
                # RG-CTL-12 : recomputed in the same transaction.
                self.test.recompute_next_due_date()
                control.recompute_effectiveness()
            if target == RUN_VALIDATED and self.result in (RunResult.PARTIAL, RunResult.FAIL):
                from controls.notifications import notify_test_failed

                notify_test_failed(self, control=control, actor=user)
        return result

    # --- Finding (RG-CTL-16) ----------------------------------------------

    def raise_finding(self, user, finding_type, recommendation=""):
        from compliance.constants import FindingSource
        from compliance.models import Finding
        from core.lifecycle import DomainRefusalError

        if self.workflow_state != RUN_VALIDATED or self.result not in (RunResult.PARTIAL, RunResult.FAIL):
            raise DomainRefusalError(_("A finding can only be raised from a validated partial or failed run."))
        with transaction.atomic():
            type(self).objects.select_for_update().filter(pk=self.pk).first()
            if self.findings.exists():
                raise DomainRefusalError(_("A finding was already raised from this run."))
            control = self.test.control
            finding = Finding(
                source=FindingSource.CONTROL_TEST,
                control_test_run=self,
                finding_type=finding_type,
                description=self.observations,
                recommendation=recommendation or "",
                evidence=str(_("Test run %(ref)s of %(test)s (%(control)s), performed on %(date)s.")) % {
                    "ref": self.reference, "test": self.test.name, "control": control.reference,
                    "date": self.performed_on.isoformat(),
                },
                assessor=user,
                created_by=user,
            )
            finding.full_clean(exclude=["reference"])
            finding.save()
            finding.requirements.set(control.requirements.all())
        return finding
