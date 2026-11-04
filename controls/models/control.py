# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""A security control the organisation operates (ISO/IEC 27001:2022 6.1.3, 8.1, 9.1).

A durable practice, not a task (RG-CTL-01). Its effectiveness is derived from
the validated runs of its active tests (RG-CTL-14), never declared.
See docs/specs/m8-controls/control.md.
"""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy
from simple_history.models import HistoricalRecords

from context.models.base import ScopedModel
from controls.constants import (
    CONTROL_DRAFT,
    CONTROL_IMPLEMENTED,
    CONTROL_RETIRED,
    REFERENCE_PREFIXES,
    TEST_ACTIVE,
    TEST_RETIRED,
    ControlAutomation,
    ControlEffectiveness,
    ControlNature,
    ControlTheme,
    RunResult,
)


def effectiveness_from_results(results):
    """RG-CTL-14 : the verdict for the latest result of each active test.

    ``results`` holds one entry per active test : its latest validated
    result, or ``None`` when the test has no validated run yet.
    """
    if not results:
        return ControlEffectiveness.NOT_TESTED
    if RunResult.FAIL in results:
        return ControlEffectiveness.NOT_EFFECTIVE
    if RunResult.PARTIAL in results:
        return ControlEffectiveness.PARTIALLY_EFFECTIVE
    if all(result == RunResult.PASS for result in results):
        return ControlEffectiveness.EFFECTIVE
    return ControlEffectiveness.NOT_TESTED


class Control(ScopedModel):
    """A control of the register."""

    REFERENCE_PREFIX = REFERENCE_PREFIXES["Control"]
    LIFECYCLE_NAME = "control"

    name = models.CharField(_("Name"), max_length=255)
    description = models.TextField(_("Description"))
    theme = models.CharField(
        _("Theme"), max_length=20, choices=ControlTheme.choices, default=ControlTheme.TECHNOLOGICAL,
    )
    nature = models.CharField(
        _("Nature"), max_length=20, choices=ControlNature.choices, default=ControlNature.PREVENTIVE,
    )
    automation = models.CharField(
        _("Automation"), max_length=20, choices=ControlAutomation.choices, default=ControlAutomation.MANUAL,
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="owned_controls", verbose_name=_("Owner"),
    )
    implemented_on = models.DateField(_("Implemented on"), null=True, blank=True)
    # Derived (RG-CTL-14), stored for filters, the SoA and the KPIs.
    effectiveness = models.CharField(
        _("Effectiveness"), max_length=20, choices=ControlEffectiveness.choices,
        default=ControlEffectiveness.NOT_TESTED, db_index=True, editable=False,
    )
    effectiveness_updated_at = models.DateTimeField(
        _("Effectiveness updated at"), null=True, blank=True, editable=False,
    )

    requirements = models.ManyToManyField(
        "compliance.Requirement", blank=True, related_name="controls", verbose_name=_("Requirements"),
    )
    risks = models.ManyToManyField(
        "risks.Risk", blank=True, related_name="controls", verbose_name=_("Risks"),
    )
    treatment_plans = models.ManyToManyField(
        "risks.RiskTreatmentPlan", blank=True, related_name="controls", verbose_name=_("Treatment plans"),
    )
    pacs_measures = models.ManyToManyField(
        "risks.PACSMeasure", blank=True, related_name="controls", verbose_name=_("PACS measures"),
    )
    support_assets = models.ManyToManyField(
        "assets.SupportAsset", blank=True, related_name="controls", verbose_name=_("Support assets"),
    )
    objectives = models.ManyToManyField(
        "context.Objective", blank=True, related_name="controls", verbose_name=_("Objectives"),
    )
    policies = models.ManyToManyField(
        "documents.Policy", blank=True, related_name="controls", verbose_name=_("Documents"),
    )
    history = HistoricalRecords()

    class Meta(ScopedModel.Meta):
        ordering = ["reference"]
        verbose_name = pgettext_lazy("control", "Control")
        verbose_name_plural = pgettext_lazy("control", "Controls")

    def __str__(self):
        return f"{self.reference} : {self.name}"

    @property
    def workflow_perm_namespace(self):
        return "controls.control"

    # --- Derived state (RG-CTL-14, RG-CTL-15) -----------------------------

    @property
    def active_tests(self):
        return self.tests.filter(workflow_state=TEST_ACTIVE)

    @property
    def next_test_due(self):
        return self.active_tests.exclude(next_due_date=None).aggregate(
            due=models.Min("next_due_date")
        )["due"]

    @property
    def is_test_overdue(self):
        due = self.next_test_due
        return due is not None and due < timezone.localdate()

    @property
    def is_effectiveness_stale(self):
        return self.is_test_overdue and self.effectiveness != ControlEffectiveness.NOT_TESTED

    @property
    def is_retired(self):
        return self.workflow_state == CONTROL_RETIRED

    def compute_effectiveness(self):
        results = [test.latest_result for test in self.active_tests]
        return effectiveness_from_results(results)

    def recompute_effectiveness(self):
        """Idempotent; writes (with a history entry) only on change."""
        value = self.compute_effectiveness()
        if value == self.effectiveness:
            return False
        self.effectiveness = value
        self.effectiveness_updated_at = timezone.now()
        self.save(update_fields=["effectiveness", "effectiveness_updated_at", "updated_at"])
        return True

    # --- Integrity --------------------------------------------------------

    def clean(self):
        super().clean()
        if self.implemented_on and self.implemented_on > timezone.localdate():
            raise ValidationError({"implemented_on": _("The implementation date cannot be in the future.")})

    # --- Lifecycle side effects (RG-CTL-02, RG-CTL-03) --------------------

    def transition_to(self, target, user=None, comment=None, *, enforce_permission=False, save=True):
        from core.lifecycle import DomainRefusalError

        with transaction.atomic():
            type(self).objects.select_for_update().filter(pk=self.pk).first()
            if target == CONTROL_IMPLEMENTED:
                if self.implemented_on and self.implemented_on > timezone.localdate():
                    raise DomainRefusalError(_("The implementation date cannot be in the future."))
                if self.implemented_on is None:
                    self.implemented_on = timezone.localdate()
            result = super().transition_to(target, user, comment=comment, enforce_permission=enforce_permission, save=save)
            if target == CONTROL_IMPLEMENTED and save:
                type(self).objects.filter(pk=self.pk).update(implemented_on=self.implemented_on)
            if target == CONTROL_RETIRED and save:
                # RG-CTL-03 : the active tests retire with the control.
                for test in self.tests.exclude(workflow_state=TEST_RETIRED):
                    test.transition_to(
                        TEST_RETIRED, user,
                        comment=str(_("Control %(ref)s retired")) % {"ref": self.reference},
                        enforce_permission=False,
                    )
        return result
