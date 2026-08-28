# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""Tests for the compliance management commands.

``recalculate_compliance`` shipped for a while with a ``select_related`` on the
assessment's ``framework``, a single-valued relation that had since become the
``frameworks`` many-to-many. Nothing exercised the command, so it raised
``FieldError`` on every invocation without failing a build. These tests are the
missing coverage : they run the command for real rather than asserting on its
internals.
"""

from io import StringIO

import pytest
from django.core.management import call_command

from compliance.tests.factories import (
    AssessmentResultFactory, ComplianceAssessmentFactory, FrameworkFactory,
    RequirementFactory,
)


@pytest.mark.django_db
class TestRecalculateCompliance:
    def test_runs_with_no_assessment(self):
        out = StringIO()
        call_command("recalculate_compliance", stdout=out)
        assert "Recalculated 0 assessment(s)." in out.getvalue()

    def test_runs_over_an_assessment_with_frameworks(self):
        framework = FrameworkFactory()
        RequirementFactory(framework=framework)
        assessment = ComplianceAssessmentFactory(frameworks=[framework])

        out = StringIO()
        call_command("recalculate_compliance", stdout=out)

        output = out.getvalue()
        assert "Recalculated 1 assessment(s)." in output
        assert str(assessment) in output

    def test_recalculated_counts_are_persisted(self):
        framework = FrameworkFactory()
        requirement = RequirementFactory(framework=framework)
        assessment = ComplianceAssessmentFactory(frameworks=[framework])
        AssessmentResultFactory(assessment=assessment, requirement=requirement)

        call_command("recalculate_compliance", stdout=StringIO())

        assessment.refresh_from_db()
        assert assessment.total_requirements >= 1
