# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""factory-boy factories for module 8 (controls).

Every factory produces a row in its lifecycle's `draft` step. Tests walk rows
forward with the helpers below, through the recorded transitions, never by
assigning `workflow_state`.
"""
import factory

from accounts.tests.factories import UserFactory
from controls.constants import (
    CONTROL_IMPLEMENTED,
    RUN_IN_REVIEW,
    RUN_VALIDATED,
    TEST_ACTIVE,
    RunResult,
)
from controls.models import Control, ControlTest, ControlTestRun


class ControlFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Control
        skip_postgeneration_save = True

    name = factory.Sequence(lambda n: f"Control {n}")
    description = "Multi-factor authentication is enforced on every remote access."
    owner = factory.SubFactory(UserFactory)
    created_by = factory.SelfAttribute("owner")


class ControlTestFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ControlTest

    control = factory.SubFactory(ControlFactory)
    name = factory.Sequence(lambda n: f"Test {n}")
    procedure = "Pick 25 remote logins and check each used a second factor."
    acceptance_criteria = "Every sampled login used a second factor."
    frequency_months = 3
    tester = factory.SubFactory(UserFactory)
    created_by = factory.SelfAttribute("tester")


class ControlTestRunFactory(factory.django.DjangoModelFactory):
    """Needs an active test : build it with `active_test()`."""

    class Meta:
        model = ControlTestRun

    test = factory.LazyFunction(lambda: active_test())
    performed_by = factory.LazyAttribute(lambda o: o.test.tester or UserFactory())
    created_by = factory.SelfAttribute("performed_by")


def implemented_control(user=None, **kwargs):
    control = ControlFactory(**kwargs)
    control.transition_to(CONTROL_IMPLEMENTED, user or control.owner)
    control.refresh_from_db()
    return control


def active_test(control=None, user=None, **kwargs):
    control = control or implemented_control()
    test = ControlTestFactory(control=control, **kwargs)
    test.transition_to(TEST_ACTIVE, user or control.owner)
    test.refresh_from_db()
    return test


def validated_run(test=None, result=RunResult.PASS, reviewer=None, **kwargs):
    """Record, submit and validate a run; the reviewer differs from the performer."""
    test = test or active_test()
    run = ControlTestRunFactory(test=test, result=result, observations=kwargs.pop("observations", "Observed."), **kwargs)
    run.transition_to(RUN_IN_REVIEW, run.performed_by)
    run.transition_to(RUN_VALIDATED, reviewer or UserFactory())
    run.refresh_from_db()
    return run
