# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""Constants of module 7 (documents) : choices, lifecycle steps and transitions.

The step and transition tables are the single source of truth of the three
lifecycles registered in ``documents/lifecycles.py`` (RG-DOC-20). Each table
declares its ``draft`` and ``archived`` steps explicitly : when they are absent,
``lifecycle_from_state_flags`` appends generic bookends whose edges carry no
``permission_action``, which would open an unguarded archive / restore path.
Step tuples are ``(code, label, counts_in_reports, linkable, deletable,
is_initial, is_terminal, tone)``; transitions are ``(source, target, label,
requires_comment, permission_action)``.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _

REFERENCE_PREFIXES = {
    "Policy": "PLCY",
    "PolicyVersion": "PLVR",
    "AcknowledgementCampaign": "ACKC",
}


class DocumentType(models.TextChoices):
    POLICY = "policy", _("Policy")
    PROCEDURE = "procedure", _("Procedure")
    STANDARD = "standard", _("Standard")
    GUIDELINE = "guideline", _("Guideline")
    CHARTER = "charter", _("Charter")
    PLAN = "plan", _("Plan")


class AcknowledgementStatus(models.TextChoices):
    PENDING = "pending", _("To acknowledge")
    ACKNOWLEDGED = "acknowledged", _("Acknowledged")
    EXCUSED = "excused", _("Excused")
    EXPIRED = "expired", _("Expired")


class AcknowledgementChannel(models.TextChoices):
    WEB = "web", _("Web")
    API = "api", _("API")
    MCP = "mcp", _("MCP")


# ── Policy (the document) ───────────────────────────────────

POLICY_DRAFT = "draft"
POLICY_ACTIVE = "active"
POLICY_RETIRED = "archived"

POLICY_STATES = [
    (POLICY_DRAFT, _("Draft"), False, False, True, True, False, "neutral"),
    (POLICY_ACTIVE, _("Active"), True, True, False, False, False, "success"),
    (POLICY_RETIRED, _("Retired"), False, False, False, False, True, "muted"),
]

POLICY_TRANSITIONS = [
    (POLICY_DRAFT, POLICY_ACTIVE, _("Activate"), False, "approve"),
    (POLICY_ACTIVE, POLICY_RETIRED, _("Retire"), True, "approve"),
    (POLICY_DRAFT, POLICY_RETIRED, _("Retire"), True, "update"),
]

# ── PolicyVersion ───────────────────────────────────────────

VERSION_DRAFT = "draft"
VERSION_IN_REVIEW = "in_review"
VERSION_IN_FORCE = "in_force"
VERSION_SUPERSEDED = "archived"

VERSION_STATES = [
    (VERSION_DRAFT, _("Draft"), False, False, True, True, False, "neutral"),
    (VERSION_IN_REVIEW, _("In review"), False, False, False, False, False, "info"),
    (VERSION_IN_FORCE, _("In force"), True, True, False, False, False, "success"),
    (VERSION_SUPERSEDED, _("Superseded"), False, False, False, False, True, "muted"),
]

VERSION_TRANSITIONS = [
    (VERSION_DRAFT, VERSION_IN_REVIEW, _("Submit for review"), False, "update"),
    (VERSION_IN_REVIEW, VERSION_DRAFT, _("Send back to draft"), True, "approve"),
    (VERSION_IN_REVIEW, VERSION_IN_FORCE, _("Approve and put in force"), False, "approve"),
    (VERSION_IN_FORCE, VERSION_SUPERSEDED, _("Withdraw"), True, "approve"),
]

# ── AcknowledgementCampaign ─────────────────────────────────

CAMPAIGN_DRAFT = "draft"
CAMPAIGN_RUNNING = "running"
CAMPAIGN_CLOSED = "closed"
CAMPAIGN_ARCHIVED = "archived"

CAMPAIGN_STATES = [
    (CAMPAIGN_DRAFT, _("Draft"), False, False, True, True, False, "neutral"),
    (CAMPAIGN_RUNNING, _("Running"), True, False, False, False, False, "info"),
    (CAMPAIGN_CLOSED, _("Closed"), True, False, False, False, False, "success"),
    (CAMPAIGN_ARCHIVED, _("Archived"), False, False, False, False, True, "muted"),
]

CAMPAIGN_TRANSITIONS = [
    (CAMPAIGN_DRAFT, CAMPAIGN_RUNNING, _("Launch"), False, "approve"),
    (CAMPAIGN_RUNNING, CAMPAIGN_CLOSED, _("Close"), False, "update"),
    (CAMPAIGN_CLOSED, CAMPAIGN_ARCHIVED, _("Archive"), True, "approve"),
    (CAMPAIGN_DRAFT, CAMPAIGN_ARCHIVED, _("Archive"), True, "approve"),
]

# Review cycle
DEFAULT_REVIEW_FREQUENCY_MONTHS = 12
REVIEW_REMINDER_DAYS = 30
ACKNOWLEDGEMENT_REMINDER_DAYS = 7

# PDF rules, shared with contracts (RG-DOC-04 / RG-CTR-02)
PDF_MAX_BYTES = 25 * 1024 * 1024
