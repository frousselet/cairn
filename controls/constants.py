# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""Constants of module 8 (controls) : choices, lifecycle steps and transitions.

The step and transition tables are the single source of truth of the three
lifecycles registered in ``controls/lifecycles.py`` (RG-CTL-17). Each table
declares its ``draft`` and ``archived`` steps explicitly : when they are absent,
``lifecycle_from_state_flags`` appends generic bookends whose edges carry no
``permission_action``, which would open an unguarded archive / restore path.
Step tuples are ``(code, label, counts_in_reports, linkable, deletable,
is_initial, is_terminal, tone)``; transitions are ``(source, target, label,
requires_comment, permission_action)``.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

REFERENCE_PREFIXES = {
    "Control": "CTRL",
    "ControlTest": "CTST",
    "ControlTestRun": "CTRN",
}


class ControlTheme(models.TextChoices):
    """ISO/IEC 27002:2022 themes."""

    ORGANIZATIONAL = "organizational", pgettext_lazy("control theme", "Organizational")
    PEOPLE = "people", pgettext_lazy("control theme", "People")
    PHYSICAL = "physical", pgettext_lazy("control theme", "Physical")
    TECHNOLOGICAL = "technological", pgettext_lazy("control theme", "Technological")


class ControlNature(models.TextChoices):
    """ISO/IEC 27002:2022 control type attribute."""

    PREVENTIVE = "preventive", pgettext_lazy("control nature", "Preventive")
    DETECTIVE = "detective", pgettext_lazy("control nature", "Detective")
    CORRECTIVE = "corrective", pgettext_lazy("control nature", "Corrective")


class ControlAutomation(models.TextChoices):
    MANUAL = "manual", pgettext_lazy("control automation", "Manual")
    SEMI_AUTOMATED = "semi_automated", pgettext_lazy("control automation", "Semi-automated")
    AUTOMATED = "automated", pgettext_lazy("control automation", "Automated")


class ControlEffectiveness(models.TextChoices):
    """RG-CTL-14 : derived, never declared."""

    EFFECTIVE = "effective", pgettext_lazy("finding", "Effective")
    PARTIALLY_EFFECTIVE = "partially_effective", pgettext_lazy("finding", "Partially effective")
    NOT_EFFECTIVE = "not_effective", pgettext_lazy("finding", "Not effective")
    NOT_TESTED = "not_tested", pgettext_lazy("control effectiveness", "Not tested")


class ControlTestMethod(models.TextChoices):
    INQUIRY = "inquiry", pgettext_lazy("test method", "Inquiry")
    OBSERVATION = "observation", pgettext_lazy("test method", "Observation")
    INSPECTION = "inspection", pgettext_lazy("test method", "Inspection")
    REPERFORMANCE = "reperformance", pgettext_lazy("test method", "Reperformance")
    AUTOMATED = "automated", pgettext_lazy("test method", "Automated")


class RunResult(models.TextChoices):
    PASS = "pass", pgettext_lazy("test result", "Pass")
    PARTIAL = "partial", pgettext_lazy("test result", "Partial")
    FAIL = "fail", pgettext_lazy("test result", "Fail")


# ── Control ─────────────────────────────────────────────────

CONTROL_DRAFT = "draft"
CONTROL_PLANNED = "planned"
CONTROL_IMPLEMENTED = "implemented"
CONTROL_RETIRED = "archived"

CONTROL_STATES = [
    (CONTROL_DRAFT, pgettext_lazy("control", "Proposed"), False, False, True, True, False, "neutral"),
    (CONTROL_PLANNED, pgettext_lazy("control", "Planned"), True, True, False, False, False, "info"),
    (CONTROL_IMPLEMENTED, pgettext_lazy("control", "Implemented"), True, True, False, False, False, "success"),
    (CONTROL_RETIRED, pgettext_lazy("control", "Retired"), False, False, False, False, True, "muted"),
]

CONTROL_TRANSITIONS = [
    (CONTROL_DRAFT, CONTROL_PLANNED, pgettext_lazy("control", "Plan"), False, "approve"),
    (CONTROL_DRAFT, CONTROL_IMPLEMENTED, pgettext_lazy("control", "Declare implemented"), False, "approve"),
    (CONTROL_PLANNED, CONTROL_IMPLEMENTED, pgettext_lazy("control", "Declare implemented"), False, "approve"),
    (CONTROL_IMPLEMENTED, CONTROL_PLANNED, pgettext_lazy("control", "Back to planned"), True, "update"),
    (CONTROL_PLANNED, CONTROL_RETIRED, pgettext_lazy("control", "Retire"), True, "approve"),
    (CONTROL_IMPLEMENTED, CONTROL_RETIRED, pgettext_lazy("control", "Retire"), True, "approve"),
    (CONTROL_DRAFT, CONTROL_RETIRED, pgettext_lazy("control", "Retire"), True, "update"),
]

# ── ControlTest ─────────────────────────────────────────────

TEST_DRAFT = "draft"
TEST_ACTIVE = "active"
TEST_RETIRED = "archived"

TEST_STATES = [
    (TEST_DRAFT, _("Draft"), False, False, True, True, False, "neutral"),
    (TEST_ACTIVE, pgettext_lazy("control", "Active"), True, True, False, False, False, "success"),
    (TEST_RETIRED, pgettext_lazy("control", "Retired"), False, False, False, False, True, "muted"),
]

TEST_TRANSITIONS = [
    (TEST_DRAFT, TEST_ACTIVE, _("Activate"), False, "approve"),
    (TEST_ACTIVE, TEST_RETIRED, pgettext_lazy("control", "Retire"), True, "approve"),
    (TEST_DRAFT, TEST_RETIRED, pgettext_lazy("control", "Retire"), True, "update"),
]

# ── ControlTestRun ──────────────────────────────────────────

RUN_DRAFT = "draft"
RUN_IN_REVIEW = "in_review"
RUN_VALIDATED = "validated"
RUN_WITHDRAWN = "archived"

RUN_STATES = [
    (RUN_DRAFT, pgettext_lazy("control test run", "In progress"), False, False, True, True, False, "neutral"),
    (RUN_IN_REVIEW, _("In review"), False, False, False, False, False, "info"),
    (RUN_VALIDATED, pgettext_lazy("control test run", "Validated"), True, False, False, False, False, "success"),
    (RUN_WITHDRAWN, pgettext_lazy("control test run", "Withdrawn"), False, False, False, False, True, "muted"),
]

RUN_TRANSITIONS = [
    (RUN_DRAFT, RUN_IN_REVIEW, _("Submit for review"), False, "update"),
    (RUN_IN_REVIEW, RUN_DRAFT, pgettext_lazy("control test run", "Send back"), True, "approve"),
    (RUN_IN_REVIEW, RUN_VALIDATED, pgettext_lazy("control test run", "Validate"), False, "approve"),
    (RUN_VALIDATED, RUN_WITHDRAWN, pgettext_lazy("control test run", "Withdraw"), True, "approve"),
    (RUN_DRAFT, RUN_WITHDRAWN, pgettext_lazy("control test run", "Cancel"), True, "update"),
]

# Tests and reminders
DEFAULT_TEST_FREQUENCY_MONTHS = 12
MAX_TEST_FREQUENCY_MONTHS = 36
TEST_DUE_REMINDER_DAYS = 14
OVERDUE_REMINDER_INTERVAL_DAYS = 7

# Evidence (RG-CTL-13)
EVIDENCE_MAX_BYTES = 25 * 1024 * 1024
ALLOWED_EVIDENCE_EXTENSIONS = [
    "pdf", "doc", "docx", "xls", "xlsx", "csv", "txt", "log", "json", "xml",
    "eml", "msg", "png", "jpg", "jpeg", "zip", "gz", "7z", "odt", "ods",
]
