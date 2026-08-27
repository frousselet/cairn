# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""Choice lists, lifecycle step codes and transitions for module 6 (incidents).

This module is the single source of truth for every incident state literal.
Reports, KPIs, pickers and deletion logic never compare against a string from
here : they go through ``reportable()`` / ``linkable()`` / ``deletable_states()``
(RG-INC-37). The step and transition tuples below are what
``incidents/lifecycles.py`` generates the registered lifecycles from.

Step labels deliberately avoid English strings that already exist as bare
``msgid``s in the catalogue with a different sense. ``lifecycle_from_json``
re-wraps stored labels with bare ``gettext_lazy``, so a label carrying a
``msgctxt`` loses its context after the ``post_migrate`` round-trip and would
resolve to the wrong French word. Enum labels have no such constraint and use
``pgettext_lazy`` where they collide.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy


# ── Shared enumerations ────────────────────────────────────

class DetectionSource(models.TextChoices):
    """How the event or incident came to light. Shared by both entities."""

    INTERNAL_MONITORING = "internal_monitoring", pgettext_lazy("incident", "Internal monitoring")
    SOC_ALERT = "soc_alert", pgettext_lazy("incident", "SOC or SIEM alert")
    EMPLOYEE_REPORT = "employee_report", pgettext_lazy("incident", "Employee report")
    CUSTOMER_REPORT = "customer_report", pgettext_lazy("incident", "Customer report")
    SUPPLIER_NOTIFICATION = "supplier_notification", pgettext_lazy("incident", "Supplier notification")
    AUTHORITY_NOTIFICATION = "authority_notification", pgettext_lazy("incident", "Authority notification")
    RESEARCHER = "researcher", pgettext_lazy("incident", "Security researcher")
    AUDIT = "audit", pgettext_lazy("incident", "Audit")
    PENETRATION_TEST = "penetration_test", pgettext_lazy("incident", "Penetration test")
    THREAT_INTEL = "threat_intel", pgettext_lazy("incident", "Threat intelligence")
    OTHER = "other", pgettext_lazy("incident", "Other")


class TrafficLightProtocol(models.TextChoices):
    """FIRST TLP v2.0 handling caveat."""

    CLEAR = "clear", "TLP:CLEAR"
    GREEN = "green", "TLP:GREEN"
    AMBER = "amber", "TLP:AMBER"
    AMBER_STRICT = "amber_strict", "TLP:AMBER+STRICT"
    RED = "red", "TLP:RED"


class SecurityEventClass(models.TextChoices):
    """What a reported occurrence turned out to be (ISO 27001 A.5.25)."""

    EVENT = "event", pgettext_lazy("incident", "Security event")
    WEAKNESS = "weakness", pgettext_lazy("incident", "Security weakness")
    INCIDENT = "incident", pgettext_lazy("incident", "Security incident")


class EventTriageDecision(models.TextChoices):
    """The named, recorded outcome of the A.5.25 assessment.

    `duplicate` and `false_positive` are deliberately distinct : an auditor
    asking why an event was not escalated gets a different answer from each,
    and conflating them loses the one that matters. A blank value means the
    assessment has not concluded, so no member stands for "undecided".
    """

    INCIDENT = "incident", pgettext_lazy("incident", "Confirmed as an incident")
    WEAKNESS = "weakness", pgettext_lazy("incident", "Confirmed as a weakness")
    DUPLICATE = "duplicate", pgettext_lazy("incident", "Duplicate of another report")
    FALSE_POSITIVE = "false_positive", pgettext_lazy("incident", "False positive")
    NO_ACTION = "no_action", pgettext_lazy("incident", "No action required")


class ResponseActionType(models.TextChoices):
    """Operational steps taken during the response (A.5.26)."""

    CONTAINMENT = "containment", pgettext_lazy("incident", "Containment")
    ERADICATION = "eradication", pgettext_lazy("incident", "Eradication")
    RECOVERY = "recovery", pgettext_lazy("incident", "Recovery")
    EVIDENCE_COLLECTION = "evidence_collection", pgettext_lazy("incident", "Evidence collection")
    COMMUNICATION = "communication", pgettext_lazy("incident", "Communication")
    ESCALATION = "escalation", pgettext_lazy("incident", "Escalation")
    WORKAROUND = "workaround", pgettext_lazy("incident", "Workaround")
    OTHER = "other", pgettext_lazy("incident", "Other")


class ResponseActionStatus(models.TextChoices):
    """Plain status column, deliberately not a lifecycle : see the spec.

    A containment step lives for minutes. An eight-step approval lifecycle
    designed for audit-gap remediation would be absurd here, and the row is a
    child of the incident rather than a governed domain element of its own.
    """

    PLANNED = "planned", pgettext_lazy("incident", "Planned")
    IN_PROGRESS = "in_progress", pgettext_lazy("incident", "In progress")
    DONE = "done", pgettext_lazy("incident", "Done")
    BLOCKED = "blocked", pgettext_lazy("incident", "Blocked")
    CANCELLED = "cancelled", pgettext_lazy("incident", "Cancelled")


class TimelineEntryKind(models.TextChoices):
    """What kind of act a chronology line records."""

    OBSERVATION = "observation", pgettext_lazy("incident", "Observation")
    ACTION = "action", pgettext_lazy("incident", "Action")
    DECISION = "decision", pgettext_lazy("incident", "Decision")
    COMMUNICATION = "communication", pgettext_lazy("incident", "Communication")
    ESCALATION = "escalation", pgettext_lazy("incident", "Escalation")
    EVIDENCE = "evidence", pgettext_lazy("incident", "Evidence")
    EXTERNAL_INPUT = "external_input", pgettext_lazy("incident", "External input")
    CORRECTION = "correction", pgettext_lazy("incident", "Correction")
    SYSTEM = "system", pgettext_lazy("incident", "System")


class TimelineEntrySource(models.TextChoices):
    """Where a chronology or custody row came from.

    `lifecycle` is the one the UI styles differently and the API filters on :
    it marks a row the platform appended from a transition, which nobody typed.
    """

    MANUAL = "manual", pgettext_lazy("incident", "Recorded by hand")
    LIFECYCLE = "lifecycle", pgettext_lazy("incident", "Appended from a transition")
    SYSTEM = "system", pgettext_lazy("incident", "Recorded by the platform")
    IMPORT = "import", pgettext_lazy("incident", "Imported")


class EvidenceType(models.TextChoices):
    DISK_IMAGE = "disk_image", pgettext_lazy("incident", "Disk image")
    MEMORY_DUMP = "memory_dump", pgettext_lazy("incident", "Memory dump")
    LOG_EXTRACT = "log_extract", pgettext_lazy("incident", "Log extract")
    NETWORK_CAPTURE = "network_capture", pgettext_lazy("incident", "Network capture")
    SCREENSHOT = "screenshot", pgettext_lazy("incident", "Screenshot")
    EMAIL = "email", pgettext_lazy("incident", "Email")
    DOCUMENT = "document", pgettext_lazy("incident", "Document")
    DATABASE_EXPORT = "database_export", pgettext_lazy("incident", "Database export")
    MALWARE_SAMPLE = "malware_sample", pgettext_lazy("incident", "Malware sample")
    PHYSICAL_DEVICE = "physical_device", pgettext_lazy("incident", "Physical device")
    WITNESS_STATEMENT = "witness_statement", pgettext_lazy("incident", "Witness statement")
    OTHER = "other", pgettext_lazy("incident", "Other")


class HashAlgorithm(models.TextChoices):
    SHA256 = "sha256", "SHA-256"
    SHA512 = "sha512", "SHA-512"
    SHA1 = "sha1", pgettext_lazy("incident", "SHA-1 (legacy)")
    MD5 = "md5", pgettext_lazy("incident", "MD5 (legacy)")


class CustodyAction(models.TextChoices):
    """One handling act on an evidence item.

    There is deliberately no `retained` value : moving an item into its
    retention period changes how the platform governs it, not who is holding
    it, so the two Retain transitions append no custody row.
    """

    COLLECTED = "collected", pgettext_lazy("incident", "Collected")
    SEALED = "sealed", pgettext_lazy("incident", "Sealed")
    TRANSFERRED = "transferred", pgettext_lazy("incident", "Transferred")
    ACCESSED = "accessed", pgettext_lazy("incident", "Accessed")
    COPIED = "copied", pgettext_lazy("incident", "Copied")
    ANALYSED = "analysed", pgettext_lazy("incident", "Analysed")
    INTEGRITY_VERIFIED = "integrity_verified", pgettext_lazy("incident", "Integrity verified")
    RELEASED = "released", pgettext_lazy("incident", "Released")
    RETURNED = "returned", pgettext_lazy("incident", "Returned")
    DESTROYED = "destroyed", pgettext_lazy("incident", "Destroyed")


class RootCauseMethod(models.TextChoices):
    FIVE_WHYS = "five_whys", pgettext_lazy("incident", "Five whys")
    ISHIKAWA = "ishikawa", pgettext_lazy("incident", "Ishikawa diagram")
    FAULT_TREE = "fault_tree", pgettext_lazy("incident", "Fault tree analysis")
    TIMELINE_ANALYSIS = "timeline_analysis", pgettext_lazy("incident", "Timeline reconstruction")
    BARRIER_ANALYSIS = "barrier_analysis", pgettext_lazy("incident", "Barrier analysis")
    OTHER = "other", pgettext_lazy("incident", "Other")


class NotificationRegime(models.TextChoices):
    """The legal or contractual basis an obligation arises from."""

    GDPR_ART33_AUTHORITY = "gdpr_art33_authority", "GDPR Art. 33(1)"
    GDPR_ART34_DATA_SUBJECT = "gdpr_art34_data_subject", "GDPR Art. 34"
    GDPR_ART33_2_CONTROLLER = "gdpr_art33_2_controller", "GDPR Art. 33(2)"
    NIS2_EARLY_WARNING = "nis2_early_warning", "NIS2 Art. 23(4)(a)"
    NIS2_NOTIFICATION = "nis2_notification", "NIS2 Art. 23(4)(b)"
    NIS2_INTERMEDIATE = "nis2_intermediate", "NIS2 Art. 23(4)(c)"
    NIS2_FINAL = "nis2_final", "NIS2 Art. 23(4)(d)"
    NIS2_RECIPIENTS = "nis2_recipients", "NIS2 Art. 23(1)"
    DORA_INITIAL = "dora_initial", "DORA Art. 19 - initial"
    DORA_INTERMEDIATE = "dora_intermediate", "DORA Art. 19 - intermediate"
    DORA_FINAL = "dora_final", "DORA Art. 19 - final"
    EPRIVACY = "eprivacy", "ePrivacy Art. 4(3)"
    CRA = "cra", "Cyber Resilience Act Art. 14"
    SECTOR_REGULATOR = "sector_regulator", pgettext_lazy("incident", "Sector regulator")
    LAW_ENFORCEMENT = "law_enforcement", pgettext_lazy("incident", "Law enforcement")
    CERT_CSIRT = "cert_csirt", "CERT / CSIRT"
    CONTRACTUAL_CUSTOMER = "contractual_customer", pgettext_lazy("incident", "Contractual - customer")
    CONTRACTUAL_SUPPLIER = "contractual_supplier", pgettext_lazy("incident", "Contractual - supplier")
    INSURER = "insurer", pgettext_lazy("incident", "Insurer")
    INTERNAL_MANAGEMENT = "internal_management", pgettext_lazy("incident", "Internal management")
    PUBLIC_COMMUNICATION = "public_communication", pgettext_lazy("incident", "Public communication")
    OTHER = "other", pgettext_lazy("incident", "Other")


class NotificationRecipientKind(models.TextChoices):
    SUPERVISORY_AUTHORITY = "supervisory_authority", pgettext_lazy("incident", "Supervisory authority")
    CSIRT = "csirt", "CSIRT"
    COMPETENT_AUTHORITY = "competent_authority", pgettext_lazy("incident", "Competent authority")
    FINANCIAL_REGULATOR = "financial_regulator", pgettext_lazy("incident", "Financial regulator")
    LAW_ENFORCEMENT = "law_enforcement", pgettext_lazy("incident", "Law enforcement")
    DATA_SUBJECT = "data_subject", pgettext_lazy("incident", "Data subjects")
    CUSTOMER = "customer", pgettext_lazy("incident", "Customer")
    CONTROLLER = "controller", pgettext_lazy("incident", "Controller")
    SUPPLIER = "supplier", pgettext_lazy("incident", "Supplier")
    INSURER = "insurer", pgettext_lazy("incident", "Insurer")
    INTERNAL = "internal", pgettext_lazy("incident", "Internal")
    PUBLIC = "public", pgettext_lazy("incident", "Public")


class NotificationDecision(models.TextChoices):
    """Whether the obligation is owed. `undecided` is a real, visible state.

    An unanswered obligation must be visible rather than absent : GDPR
    Art. 33(1) permits omission only on a judgement, and a judgement nobody
    made is not the same as a judgement that concluded nothing is owed.
    """

    UNDECIDED = "undecided", pgettext_lazy("incident", "Not yet decided")
    REQUIRED = "required", pgettext_lazy("incident", "Required")
    NOT_REQUIRED = "not_required", pgettext_lazy("incident", "Not required")


class ClockAnchor(models.TextChoices):
    """Which timestamp starts a statutory clock."""

    OCCURRED_AT = "occurred_at", pgettext_lazy("incident", "Occurrence")
    DETECTED_AT = "detected_at", pgettext_lazy("incident", "Technical detection")
    AWARENESS_AT = "awareness_at", pgettext_lazy("incident", "Awareness")
    SIGNIFICANCE_DETERMINED_AT = "significance_determined_at", pgettext_lazy("incident", "Significance determination")
    PREVIOUS_STAGE = "previous_stage", pgettext_lazy("incident", "Previous filing")


class NotificationChannel(models.TextChoices):
    PORTAL = "portal", pgettext_lazy("incident", "Online portal")
    EMAIL = "email", pgettext_lazy("incident", "Email")
    POSTAL = "postal", pgettext_lazy("incident", "Postal mail")
    PHONE = "phone", pgettext_lazy("incident", "Telephone")
    API = "api", "API"
    IN_PERSON = "in_person", pgettext_lazy("incident", "In person")
    PUBLIC_NOTICE = "public_notice", pgettext_lazy("incident", "Public notice")


class FilingOutcome(models.TextChoices):
    SENT = "sent", pgettext_lazy("incident", "Sent")
    ACKNOWLEDGED = "acknowledged", pgettext_lazy("incident", "Acknowledged")
    REJECTED = "rejected", pgettext_lazy("incident", "Rejected")
    INFORMATION_REQUESTED = "information_requested", pgettext_lazy("incident", "Information requested")
    SUPERSEDED = "superseded", pgettext_lazy("incident", "Superseded")


class AuthorityType(models.TextChoices):
    SUPERVISORY_AUTHORITY = "supervisory_authority", pgettext_lazy("incident", "Data protection supervisory authority")
    CSIRT = "csirt", "CSIRT"
    COMPETENT_AUTHORITY = "competent_authority", pgettext_lazy("incident", "Competent authority")
    SECTOR_REGULATOR = "sector_regulator", pgettext_lazy("incident", "Sector regulator")
    FINANCIAL_REGULATOR = "financial_regulator", pgettext_lazy("incident", "Financial regulator")
    LAW_ENFORCEMENT = "law_enforcement", pgettext_lazy("incident", "Law enforcement")
    OTHER = "other", pgettext_lazy("incident", "Other")


class ControllerRole(models.TextChoices):
    """GDPR capacity, which alone decides which obligations exist at all."""

    CONTROLLER = "controller", pgettext_lazy("incident", "Controller")
    JOINT_CONTROLLER = "joint_controller", pgettext_lazy("incident", "Joint controller")
    PROCESSOR = "processor", pgettext_lazy("incident", "Processor")


class Art34Ground(models.TextChoices):
    """GDPR Art. 34(3) grounds for not informing data subjects."""

    NONE = "none", pgettext_lazy("incident", "None relied on")
    ENCRYPTION = "encryption", pgettext_lazy("incident", "Art. 34(3)(a) : data unintelligible")
    SUBSEQUENT_MEASURES = "subsequent_measures", pgettext_lazy("incident", "Art. 34(3)(b) : high risk no longer likely")
    DISPROPORTIONATE_EFFORT = "disproportionate_effort", pgettext_lazy("incident", "Art. 34(3)(c) : disproportionate effort")


# ── Incident lifecycle ─────────────────────────────────────
# (code, label, counts_in_reports, linkable, deletable, is_initial, is_terminal, tone)
#
# `draft` and `archived` are declared EXPLICITLY so nothing is auto-wired.
# The generated bookends carry no `permission_action` and no `requires_comment`,
# which would leave an archive -> restore -> delete path out of any deletable
# step (RG-INC-07). Declaring them here forces the hand-written edges below.

INCIDENT_STATES = [
    ("draft", _("Draft"), False, False, True, False, False, "neutral"),
    ("detected", _("Detected"), True, False, False, True, False, "secondary"),
    ("triaged", _("Triaged"), True, True, False, False, False, "info"),
    ("investigating", _("Investigating"), True, True, False, False, False, "primary"),
    ("contained", _("Contained"), True, True, False, False, False, "warning"),
    ("eradicated", _("Eradicated"), True, True, False, False, False, "primary"),
    ("recovered", _("Recovered"), True, True, False, False, False, "success"),
    ("post_incident_review", _("Post-incident review"), True, True, False, False, False, "info"),
    ("closed", _("Incident closed"), True, False, False, False, True, "dark"),
    ("reclassified", _("Reclassified as event"), False, False, False, False, True, "muted"),
    ("archived", _("Archived"), False, False, False, False, False, "muted"),
]

# (source, target, label, requires_comment, permission_action)
INCIDENT_TRANSITIONS = [
    ("draft", "detected", _("Declare the incident"), False, "create"),
    ("detected", "triaged", _("Complete triage"), False, "update"),
    ("triaged", "investigating", _("Start investigation"), False, "update"),
    ("investigating", "contained", _("Record containment"), False, "update"),
    ("contained", "eradicated", _("Record eradication"), False, "update"),
    ("eradicated", "recovered", _("Record recovery"), False, "update"),
    ("recovered", "post_incident_review", _("Open the post-incident review"), False, "update"),
    ("post_incident_review", "closed", _("Close the incident"), True, "validate"),
    # Rework paths : an incident that reopens is common and must stay auditable.
    ("recovered", "investigating", _("Reopen the investigation"), True, "update"),
    ("closed", "investigating", _("Reopen a closed incident"), True, "validate"),
    ("post_incident_review", "investigating", _("Send back to investigation"), True, "update"),
    # Honest off-ramp : it was declared, and it turned out not to be an incident.
    ("detected", "reclassified", _("Reclassify as an event"), True, "validate"),
    ("triaged", "reclassified", _("Reclassify as an event"), True, "validate"),
    ("investigating", "reclassified", _("Reclassify as an event"), True, "validate"),
    # Hand-declared bookends, gated. Never left to the generator.
    ("*", "archived", _("Archive"), True, "validate"),
    ("archived", "draft", _("Restore"), False, "validate"),
]

INCIDENT_DELETABLE_STATES = ["draft"]


# ── SecurityEvent lifecycle ────────────────────────────────

SECURITY_EVENT_STATES = [
    ("draft", _("Draft"), False, False, True, False, False, "neutral"),
    ("reported", _("Reported"), True, False, True, True, False, "secondary"),
    ("under_assessment", _("Under assessment"), True, False, False, False, False, "info"),
    ("confirmed_incident", _("Promoted to incident"), True, True, False, False, True, "danger"),
    ("confirmed_weakness", _("Confirmed weakness"), True, True, False, False, True, "warning"),
    ("discarded", _("Discarded"), False, False, False, False, True, "muted"),
    ("archived", _("Archived"), False, False, False, False, False, "muted"),
]

SECURITY_EVENT_TRANSITIONS = [
    ("draft", "reported", _("Report the event"), False, "create"),
    ("reported", "under_assessment", _("Start the assessment"), False, "update"),
    ("under_assessment", "confirmed_incident", _("Promote to incident"), True, "validate"),
    ("under_assessment", "confirmed_weakness", _("Record as a weakness"), True, "update"),
    ("under_assessment", "discarded", _("Discard"), True, "validate"),
    ("discarded", "under_assessment", _("Reopen the assessment"), True, "update"),
    ("*", "archived", _("Archive"), True, "validate"),
    ("archived", "draft", _("Restore"), False, "validate"),
]


# ── IncidentEvidence lifecycle ─────────────────────────────

EVIDENCE_STATES = [
    ("draft", _("Draft registration"), False, False, True, False, False, "neutral"),
    ("collected", _("Collected"), True, False, False, True, False, "secondary"),
    ("secured", _("Secured"), True, True, False, False, False, "info"),
    ("analysed", _("Analysed"), True, True, False, False, False, "primary"),
    ("retained", _("Retained in custody"), True, True, False, False, False, "success"),
    ("released", _("Released"), True, False, False, False, True, "dark"),
    ("destroyed", _("Destroyed"), False, False, False, False, True, "muted"),
    ("archived", _("Archived"), False, False, False, False, False, "muted"),
]

EVIDENCE_TRANSITIONS = [
    ("draft", "collected", _("Register the acquisition"), False, "create"),
    ("collected", "secured", _("Seal the evidence"), False, "update"),
    ("secured", "analysed", _("Record analysis"), False, "update"),
    ("secured", "retained", _("Move into retention"), False, "update"),
    ("analysed", "retained", _("Move into retention"), False, "update"),
    ("retained", "released", _("Release to a counterparty"), True, "approve"),
    ("retained", "destroyed", _("Destroy the evidence"), True, "approve"),
    ("*", "archived", _("Archive"), True, "approve"),
    ("archived", "draft", _("Restore"), False, "approve"),
]


# ── IncidentNotification lifecycle ─────────────────────────

NOTIFICATION_STATES = [
    ("draft", _("Draft"), False, False, True, False, False, "neutral"),
    ("assessed", _("To decide"), True, False, True, True, False, "warning"),
    ("required", _("Notification required"), True, False, False, False, False, "info"),
    ("drafted", _("Notification drafted"), True, False, False, False, False, "primary"),
    ("sent", _("Notification sent"), True, False, False, False, False, "success"),
    ("acknowledged", _("Acknowledged by the recipient"), True, False, False, False, False, "dark"),
    ("not_required", _("Notification not required"), True, False, False, False, True, "muted"),
    ("archived", _("Archived"), False, False, False, False, False, "muted"),
]

NOTIFICATION_TRANSITIONS = [
    ("draft", "assessed", _("Register the obligation"), False, "create"),
    ("assessed", "required", _("Decide it is required"), True, "approve"),
    # GDPR Art. 33(1) allows omission only on a judgement. That judgement needs
    # a named decider, a timestamp, a rationale and an approval.
    ("assessed", "not_required", _("Decide it is not required"), True, "approve"),
    ("required", "drafted", _("Draft the notification"), False, "update"),
    ("drafted", "sent", _("Record the filing"), False, "update"),
    ("sent", "acknowledged", _("Record the acknowledgement"), False, "update"),
    ("not_required", "assessed", _("Reopen the decision"), True, "approve"),
    ("*", "archived", _("Archive"), True, "approve"),
    ("archived", "draft", _("Restore"), False, "approve"),
]


# ── PostIncidentReview lifecycle ───────────────────────────

REVIEW_STATES = [
    ("draft", _("Draft"), False, False, True, False, False, "neutral"),
    ("scheduled", _("Review scheduled"), True, False, True, True, False, "secondary"),
    ("in_progress", _("Review in progress"), True, False, False, False, False, "info"),
    ("submitted", _("Review submitted"), True, True, False, False, False, "primary"),
    ("approved", _("Review approved"), True, True, False, False, False, "success"),
    ("effectiveness_verified", _("Effectiveness verified"), True, True, False, False, True, "dark"),
    ("cancelled", _("Review cancelled"), False, False, False, False, True, "muted"),
    ("archived", _("Archived"), False, False, False, False, False, "muted"),
]

REVIEW_TRANSITIONS = [
    ("draft", "scheduled", _("Schedule the review"), False, "create"),
    ("scheduled", "in_progress", _("Start the review"), False, "update"),
    ("in_progress", "submitted", _("Submit the review"), False, "update"),
    ("submitted", "approved", _("Approve the review"), True, "validate"),
    ("submitted", "in_progress", _("Send back for rework"), True, "update"),
    # ISO 27001 clause 10.2 d) and f) : the record that the action worked.
    ("approved", "effectiveness_verified", _("Verify effectiveness"), True, "validate"),
    ("scheduled", "cancelled", _("Cancel the review"), True, "validate"),
    ("in_progress", "cancelled", _("Cancel the review"), True, "validate"),
    ("*", "archived", _("Archive"), True, "validate"),
    ("archived", "draft", _("Restore"), False, "validate"),
]


# ── PersonalDataBreach lifecycle ───────────────────────────

BREACH_STATES = [
    ("draft", _("Draft"), False, False, True, False, False, "neutral"),
    ("under_qualification", _("Qualification in progress"), False, False, True, True, False, "warning"),
    ("confirmed", _("Confirmed breach"), True, True, False, False, False, "danger"),
    ("documented", _("Documented under Art. 33(5)"), True, True, False, False, False, "success"),
    ("not_a_breach", _("Not a personal data breach"), False, False, False, False, True, "muted"),
    ("archived", _("Archived"), False, False, False, False, False, "muted"),
]

BREACH_TRANSITIONS = [
    ("draft", "under_qualification", _("Open the qualification"), False, "create"),
    ("under_qualification", "confirmed", _("Confirm the breach"), True, "approve"),
    ("under_qualification", "not_a_breach", _("Rule out a breach"), True, "approve"),
    ("confirmed", "documented", _("Complete the Art. 33(5) record"), False, "approve"),
    ("confirmed", "under_qualification", _("Reopen the qualification"), True, "approve"),
    ("documented", "confirmed", _("Reopen the record"), True, "approve"),
    ("not_a_breach", "under_qualification", _("Reopen a ruled-out qualification"), True, "approve"),
    ("*", "archived", _("Archive"), True, "approve"),
    ("archived", "draft", _("Restore"), False, "approve"),
]


# ── Reference prefixes ─────────────────────────────────────
# Verified free against every REFERENCE_PREFIX in the tree. INCD is one letter
# order away from INDC (context.Indicator) : never copy a neighbouring line in
# the MCP help block when adding these.

REFERENCE_PREFIXES = {
    "Incident": "INCD",
    "SecurityEvent": "EVNT",
    "IncidentResponsePlan": "IRPL",
    "IncidentResponseAction": "IRAC",
    "IncidentEvidence": "EVID",
    "PostIncidentReview": "PIRV",
    "IncidentNotification": "INOT",
    "NotificationFiling": "NFIL",
    "ReportingAuthority": "RGAU",
    "ReportingObligationTemplate": "ROBT",
    "PersonalDataBreach": "PDBR",
}
