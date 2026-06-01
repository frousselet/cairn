from django.db import models
from django.utils.translation import gettext_lazy as _


class Methodology(models.TextChoices):
    ISO27005 = "iso27005", _("ISO 27005")
    EBIOS_RM = "ebios_rm", _("EBIOS RM")


class AssessmentStatus(models.TextChoices):
    DRAFT = "draft", _("Draft")
    IN_PROGRESS = "in_progress", _("In progress")
    COMPLETED = "completed", _("Completed")
    VALIDATED = "validated", _("Validated")
    ARCHIVED = "archived", _("Archived")


class CriteriaStatus(models.TextChoices):
    DRAFT = "draft", _("Draft")
    ACTIVE = "active", _("Active")
    ARCHIVED = "archived", _("Archived")


class ScaleType(models.TextChoices):
    LIKELIHOOD = "likelihood", _("Likelihood")
    IMPACT = "impact", _("Impact")


class RiskSourceType(models.TextChoices):
    ISO27005_ANALYSIS = "iso27005_analysis", _("ISO 27005 analysis")
    EBIOS_STRATEGIC = "ebios_strategic", _("EBIOS strategic scenario")
    EBIOS_OPERATIONAL = "ebios_operational", _("EBIOS operational scenario")
    INCIDENT = "incident", _("Incident")
    AUDIT = "audit", _("Audit")
    COMPLIANCE = "compliance", _("Compliance")
    MANUAL = "manual", _("Manual entry")


class TreatmentDecision(models.TextChoices):
    ACCEPT = "accept", _("Accept")
    MITIGATE = "mitigate", _("Mitigate")
    TRANSFER = "transfer", _("Transfer")
    AVOID = "avoid", _("Avoid")
    NOT_DECIDED = "not_decided", _("Not decided")


class RiskPriority(models.TextChoices):
    LOW = "low", _("Low")
    MEDIUM = "medium", _("Medium")
    HIGH = "high", _("High")
    CRITICAL = "critical", _("Critical")


class RiskStatus(models.TextChoices):
    IDENTIFIED = "identified", _("Identified")
    ANALYZED = "analyzed", _("Analyzed")
    EVALUATED = "evaluated", _("Evaluated")
    TREATMENT_PLANNED = "treatment_planned", _("Treatment planned")
    TREATMENT_IN_PROGRESS = "treatment_in_progress", _("Treatment in progress")
    TREATED = "treated", _("Treated")
    ACCEPTED = "accepted", _("Accepted")
    CLOSED = "closed", _("Closed")
    MONITORING = "monitoring", _("Monitoring")


class TreatmentType(models.TextChoices):
    MITIGATE = "mitigate", _("Mitigate")
    TRANSFER = "transfer", _("Transfer")
    AVOID = "avoid", _("Avoid")


class TreatmentPlanStatus(models.TextChoices):
    PLANNED = "planned", _("Planned")
    IN_PROGRESS = "in_progress", _("In progress")
    COMPLETED = "completed", _("Completed")
    CANCELLED = "cancelled", _("Cancelled")
    OVERDUE = "overdue", _("Overdue")


class ActionStatus(models.TextChoices):
    PLANNED = "planned", _("Planned")
    IN_PROGRESS = "in_progress", _("In progress")
    COMPLETED = "completed", _("Completed")
    CANCELLED = "cancelled", _("Cancelled")


class AcceptanceStatus(models.TextChoices):
    ACTIVE = "active", _("Active")
    EXPIRED = "expired", _("Expired")
    REVOKED = "revoked", _("Revoked")
    RENEWED = "renewed", _("Renewed")


class ThreatType(models.TextChoices):
    DELIBERATE = "deliberate", _("Deliberate")
    ACCIDENTAL = "accidental", _("Accidental")
    ENVIRONMENTAL = "environmental", _("Environmental")
    OTHER = "other", _("Other")


class ThreatOrigin(models.TextChoices):
    HUMAN_INTERNAL = "human_internal", _("Human internal")
    HUMAN_EXTERNAL = "human_external", _("Human external")
    NATURAL = "natural", _("Natural")
    TECHNICAL = "technical", _("Technical")
    OTHER = "other", _("Other")


class ThreatCategory(models.TextChoices):
    MALWARE = "malware", _("Malware")
    SOCIAL_ENGINEERING = "social_engineering", _("Social engineering")
    UNAUTHORIZED_ACCESS = "unauthorized_access", _("Unauthorized access")
    DENIAL_OF_SERVICE = "denial_of_service", _("Denial of service")
    DATA_BREACH = "data_breach", _("Data breach")
    PHYSICAL_ATTACK = "physical_attack", _("Physical attack")
    ESPIONAGE = "espionage", _("Espionage")
    FRAUD = "fraud", _("Fraud")
    SABOTAGE = "sabotage", _("Sabotage")
    HUMAN_ERROR = "human_error", _("Human error")
    SYSTEM_FAILURE = "system_failure", _("System failure")
    NETWORK_FAILURE = "network_failure", _("Network failure")
    POWER_FAILURE = "power_failure", _("Power failure")
    NATURAL_DISASTER = "natural_disaster", _("Natural disaster")
    FIRE = "fire", _("Fire")
    WATER_DAMAGE = "water_damage", _("Water damage")
    THEFT = "theft", _("Theft")
    VANDALISM = "vandalism", _("Vandalism")
    SUPPLY_CHAIN = "supply_chain", _("Supply chain")
    INSIDER_THREAT = "insider_threat", _("Insider threat")
    RANSOMWARE = "ransomware", _("Ransomware")
    APT = "apt", _("Advanced persistent threat (APT)")
    OTHER = "other", _("Other")


class ThreatStatus(models.TextChoices):
    ACTIVE = "active", _("Active")
    INACTIVE = "inactive", _("Inactive")


class VulnerabilityCategory(models.TextChoices):
    CONFIGURATION_WEAKNESS = "configuration_weakness", _("Configuration weakness")
    MISSING_PATCH = "missing_patch", _("Missing patch")
    DESIGN_FLAW = "design_flaw", _("Design flaw")
    CODING_ERROR = "coding_error", _("Coding error")
    WEAK_AUTHENTICATION = "weak_authentication", _("Weak authentication")
    INSUFFICIENT_LOGGING = "insufficient_logging", _("Insufficient logging")
    LACK_OF_ENCRYPTION = "lack_of_encryption", _("Lack of encryption")
    PHYSICAL_VULNERABILITY = "physical_vulnerability", _("Physical vulnerability")
    ORGANIZATIONAL_WEAKNESS = "organizational_weakness", _("Organizational weakness")
    HUMAN_FACTOR = "human_factor", _("Human factor")
    OBSOLESCENCE = "obsolescence", _("Obsolescence")
    INSUFFICIENT_BACKUP = "insufficient_backup", _("Insufficient backup")
    NETWORK_EXPOSURE = "network_exposure", _("Network exposure")
    THIRD_PARTY_DEPENDENCY = "third_party_dependency", _("Third-party dependency")


class Severity(models.TextChoices):
    LOW = "low", _("Low")
    MEDIUM = "medium", _("Medium")
    HIGH = "high", _("High")
    CRITICAL = "critical", _("Critical")


class VulnerabilityStatus(models.TextChoices):
    IDENTIFIED = "identified", _("Identified")
    CONFIRMED = "confirmed", _("Confirmed")
    MITIGATED = "mitigated", _("Mitigated")
    ACCEPTED = "accepted", _("Accepted")
    CLOSED = "closed", _("Closed")


# ── Default 5×5 risk matrix scales (ISO 27005) ──────────────

DEFAULT_LIKELIHOOD_SCALES = [
    (1, _("Very unlikely")),
    (2, _("Unlikely")),
    (3, _("Possible")),
    (4, _("Likely")),
    (5, _("Very likely")),
]

DEFAULT_IMPACT_SCALES = [
    (1, _("Negligible")),
    (2, _("Minor")),
    (3, _("Moderate")),
    (4, _("Major")),
    (5, _("Severe")),
]

DEFAULT_RISK_LEVELS = {
    1: {"name": _("Low"), "color": "#4caf50"},
    2: {"name": _("Moderate-Low"), "color": "#8bc34a"},
    3: {"name": _("Moderate"), "color": "#ffc107"},
    4: {"name": _("Moderate-High"), "color": "#ff9800"},
    5: {"name": _("High"), "color": "#e53935"},
}

# Symmetric matrix: risk_level = f(L + I - 1), so cell (L,I) == cell (I,L)
DEFAULT_RISK_MATRIX = {
    (5, 1): 3, (5, 2): 4, (5, 3): 4, (5, 4): 5, (5, 5): 5,
    (4, 1): 3, (4, 2): 3, (4, 3): 4, (4, 4): 4, (4, 5): 5,
    (3, 1): 2, (3, 2): 3, (3, 3): 3, (3, 4): 4, (3, 5): 4,
    (2, 1): 2, (2, 2): 2, (2, 3): 3, (2, 4): 3, (2, 5): 4,
    (1, 1): 1, (1, 2): 2, (1, 3): 2, (1, 4): 3, (1, 5): 3,
}


# EBIOS RM (ANSSI v1.5) constants - workshops W0 and W1

class EbiosWorkshopNumber(models.IntegerChoices):
    W0 = 0, _("Workshop 0 - Study framework")
    W1 = 1, _("Workshop 1 - Security baseline")
    W2 = 2, _("Workshop 2 - Risk sources")
    W3 = 3, _("Workshop 3 - Strategic scenarios")
    W4 = 4, _("Workshop 4 - Operational scenarios")
    W5 = 5, _("Workshop 5 - Risk treatment")


class EbiosWorkshopStatus(models.TextChoices):
    NOT_STARTED = "not_started", _("Not started")
    IN_PROGRESS = "in_progress", _("In progress")
    UNDER_REVIEW = "under_review", _("Under review")
    VALIDATED = "validated", _("Validated")
    REJECTED = "rejected", _("Rejected")


class EbiosIterationType(models.TextChoices):
    STRATEGIC = "strategic", _("Strategic cycle")
    OPERATIONAL = "operational", _("Operational cycle")


class EbiosStudyFrameworkStatus(models.TextChoices):
    DRAFT = "draft", _("Draft")
    VALIDATED = "validated", _("Validated")


class EbiosBaselineStatus(models.TextChoices):
    DRAFT = "draft", _("Draft")
    IN_PROGRESS = "in_progress", _("In progress")
    COMPLETED = "completed", _("Completed")


class DICCriterion(models.TextChoices):
    CONFIDENTIALITY = "confidentiality", _("Confidentiality")
    INTEGRITY = "integrity", _("Integrity")
    AVAILABILITY = "availability", _("Availability")


class BaselineGapStatus(models.TextChoices):
    IDENTIFIED = "identified", _("Identified")
    ACCEPTED = "accepted", _("Accepted")
    IN_REMEDIATION = "in_remediation", _("In remediation")
    REMEDIATED = "remediated", _("Remediated")


# Total number of workshops produced for every EBIOS RM assessment (W0..W5)
EBIOS_WORKSHOP_COUNT = 6


# EBIOS RM workshop W2 - Risk sources and targeted objectives

class RiskSourceCategory(models.TextChoices):
    STATE = "state", _("State")
    ORGANIZED_CRIME = "organized_crime", _("Organized crime")
    TERRORIST = "terrorist", _("Terrorist")
    ACTIVIST = "activist", _("Activist / hacktivist")
    COMPETITOR = "competitor", _("Competitor")
    EMPLOYEE = "employee", _("Internal employee")
    SERVICE_PROVIDER = "service_provider", _("Service provider")
    AMATEUR = "amateur", _("Amateur / script kiddie")
    NATURAL = "natural", _("Natural phenomenon")
    OTHER = "other", _("Other")


class TargetedObjectiveCategory(models.TextChoices):
    LUCRATIVE = "lucrative", _("Lucrative")
    STRATEGIC = "strategic", _("Strategic")
    TERRORIST = "terrorist", _("Terrorist")
    IDEOLOGICAL = "ideological", _("Ideological")
    REVENGE = "revenge", _("Revenge")
    LUDIC = "ludic", _("Ludic")
    OTHER = "other", _("Other")


class Relevance(models.TextChoices):
    LOW = "low", _("Low")
    MEDIUM = "medium", _("Medium")
    HIGH = "high", _("High")
    CRITICAL = "critical", _("Critical")


# ANSSI threat level scale (V1..V4). Stored as integers so they can be filtered
# and compared by the matrix in RiskCriteria.
class ThreatLevelV(models.IntegerChoices):
    V1 = 1, _("V1 - Minimal")
    V2 = 2, _("V2 - Significant")
    V3 = 3, _("V3 - Strong")
    V4 = 4, _("V4 - Maximal")


# ANSSI Grid A: niveau de menace SR = grid(motivation 1..4, resources 1..4)
# Keys: (motivation, resources) -> ThreatLevelV.value
# Reference: M4bis spec §2.8 Grid A. Activity may add one level (capped at V4).
ANSSI_THREAT_LEVEL_GRID = {
    (1, 1): 1, (1, 2): 1, (1, 3): 2, (1, 4): 2,
    (2, 1): 1, (2, 2): 2, (2, 3): 3, (2, 4): 3,
    (3, 1): 2, (3, 2): 3, (3, 3): 3, (3, 4): 4,
    (4, 1): 2, (4, 2): 3, (4, 3): 4, (4, 4): 4,
}


def compute_anssi_threat_level(motivation, resources, activity=None, grid=None):
    """Return the ANSSI threat level (1..4) from (motivation, resources, activity).

    `motivation` and `resources` are integers in 1..4. `activity` is optional
    (1..4); when >= 3 it adds one level, capped at V4. Pass a custom `grid`
    (dict) to override the default ANSSI grid (used by criteria_snapshot when
    the assessment carries a paramétrable grid in RiskCriteria).
    """
    if motivation is None or resources is None:
        return None
    g = grid or ANSSI_THREAT_LEVEL_GRID
    base = g.get((int(motivation), int(resources)))
    if base is None:
        return None
    if activity and int(activity) >= 3:
        base = min(base + 1, ThreatLevelV.V4)
    return int(base)


# EBIOS RM workshop W3 - Ecosystem stakeholders and strategic scenarios

class EcosystemStakeholderCategory(models.TextChoices):
    SUPPLIER = "supplier", _("Supplier")
    PARTNER = "partner", _("Partner")
    SUBCONTRACTOR = "subcontractor", _("Subcontractor")
    CUSTOMER = "customer", _("Customer")
    REGULATOR = "regulator", _("Regulator")
    SHARED_INFRASTRUCTURE = "shared_infrastructure", _("Shared infrastructure")
    CLIENT_EMPLOYEE = "client_employee", _("Client employee")
    OTHER = "other", _("Other")


class ThreatZone(models.TextChoices):
    CONTROL = "control", _("Control zone")
    MONITORING = "monitoring", _("Monitoring zone")
    DANGER = "danger", _("Danger zone")


# ANSSI ecosystem threat zone thresholds.
# threat_level = (dependency * penetration) / (maturity * trust), each input in 1..4.
# The result lies in ]0.0625, 16.0]. Defaults below are taken from M4bis spec §2.6
# Annex C. Override per assessment via RiskCriteria.risk_matrix["ebios_ecosystem_thresholds"].
DEFAULT_ECOSYSTEM_THRESHOLDS = {
    "control": 0.5,     # threat_level < 0.5  => control zone (green)
    "monitoring": 1.5,  # 0.5 <= threat_level < 1.5 => monitoring zone (orange)
                        # threat_level >= 1.5 => danger zone (red)
}


def compute_ecosystem_threat_level(dependency, penetration, maturity, trust):
    """Return the raw threat level for an ecosystem stakeholder.

    Formula (M4bis spec §2.6): (dependency * penetration) / (maturity * trust).
    Returns None if any input is missing or if the denominator is zero.
    """
    if None in (dependency, penetration, maturity, trust):
        return None
    denominator = float(maturity) * float(trust)
    if denominator <= 0:
        return None
    return (float(dependency) * float(penetration)) / denominator


def compute_ecosystem_threat_zone(threat_level, thresholds=None):
    """Return the ecosystem ThreatZone enum value from a raw threat_level.

    `thresholds` is a dict with keys "control" and "monitoring"
    (cf. DEFAULT_ECOSYSTEM_THRESHOLDS). Pass None to use the ANSSI defaults.
    """
    if threat_level is None:
        return None
    t = thresholds or DEFAULT_ECOSYSTEM_THRESHOLDS
    if threat_level < t["control"]:
        return ThreatZone.CONTROL
    if threat_level < t["monitoring"]:
        return ThreatZone.MONITORING
    return ThreatZone.DANGER


class AttackPathActionType(models.TextChoices):
    INITIAL_ACCESS = "initial_access", _("Initial access")
    RECONNAISSANCE = "reconnaissance", _("Reconnaissance")
    LATERAL_MOVEMENT = "lateral_movement", _("Lateral movement")
    PRIVILEGE_ESCALATION = "privilege_escalation", _("Privilege escalation")
    DATA_EXFILTRATION = "data_exfiltration", _("Data exfiltration")
    DISRUPTION = "disruption", _("Disruption")
    MANIPULATION = "manipulation", _("Manipulation")
    PERSISTENCE = "persistence", _("Persistence")
    OTHER = "other", _("Other")


class AttackDifficulty(models.TextChoices):
    TRIVIAL = "trivial", _("Trivial")
    EASY = "easy", _("Easy")
    MODERATE = "moderate", _("Moderate")
    DIFFICULT = "difficult", _("Difficult")
    VERY_DIFFICULT = "very_difficult", _("Very difficult")


# EBIOS RM workshop W4 - MITRE ATT&CK tactics (Enterprise Matrix v15)

class MitreAttackTactic(models.TextChoices):
    RECONNAISSANCE = "reconnaissance", _("Reconnaissance")
    RESOURCE_DEVELOPMENT = "resource_development", _("Resource development")
    INITIAL_ACCESS = "initial_access", _("Initial access")
    EXECUTION = "execution", _("Execution")
    PERSISTENCE = "persistence", _("Persistence")
    PRIVILEGE_ESCALATION = "privilege_escalation", _("Privilege escalation")
    DEFENSE_EVASION = "defense_evasion", _("Defense evasion")
    CREDENTIAL_ACCESS = "credential_access", _("Credential access")
    DISCOVERY = "discovery", _("Discovery")
    LATERAL_MOVEMENT = "lateral_movement", _("Lateral movement")
    COLLECTION = "collection", _("Collection")
    COMMAND_AND_CONTROL = "command_and_control", _("Command and control")
    EXFILTRATION = "exfiltration", _("Exfiltration")
    IMPACT = "impact", _("Impact")


# EBIOS RM workshop W5 - Summary and PACS

class EbiosSummaryStatus(models.TextChoices):
    DRAFT = "draft", _("Draft")
    IN_PROGRESS = "in_progress", _("In progress")
    UNDER_REVIEW = "under_review", _("Under review")
    VALIDATED = "validated", _("Validated")


class PACSMeasureType(models.TextChoices):
    GOVERNANCE = "governance", _("Governance")
    PROTECTION = "protection", _("Protection")
    DEFENSE = "defense", _("Defense")
    RESILIENCE = "resilience", _("Resilience")
    AWARENESS = "awareness", _("Awareness")


class PACSMeasureStatus(models.TextChoices):
    PLANNED = "planned", _("Planned")
    IN_PROGRESS = "in_progress", _("In progress")
    COMPLETED = "completed", _("Completed")
    CANCELLED = "cancelled", _("Cancelled")
    OVERDUE = "overdue", _("Overdue")


class PACSMeasurePriority(models.TextChoices):
    LOW = "low", _("Low")
    MEDIUM = "medium", _("Medium")
    HIGH = "high", _("High")
    CRITICAL = "critical", _("Critical")
