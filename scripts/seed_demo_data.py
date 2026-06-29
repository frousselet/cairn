"""Seed the dev database with fictional demo data for Voltara Energy.

Voltara Energy is an imaginary mid-size European renewable energy operator
(wind, solar, hydro) headquartered in Lyon. The dataset covers every module
so the dashboard, calendar and list views look realistic for screenshots.

Run inside the web container:
    docker compose exec -T web python manage.py shell -c "exec(open('scripts/seed_demo_data.py').read())"
"""

from datetime import timedelta
from decimal import Decimal
from urllib.parse import quote

from django.db import transaction
from django.utils import timezone

from accounts.models import CompanySettings, Group, Notification, User
from assets.models import (
    AssetDependency,
    AssetGroup,
    AssetValuation,
    Contract,
    EssentialAsset,
    SiteAssetDependency,
    SiteSupplierDependency,
    Supplier,
    SupplierDependency,
    SupplierRequirement,
    SupplierRequirementReview,
    SupplierType,
    SupplierTypeRequirement,
    SupportAsset,
)
from assets.services.spof_detection import SpofDetector
from compliance.constants import COMPLIANCE_LEVEL_DEFAULTS
from compliance.models import (
    ActionPlanComment,
    ComplianceActionPlan,
    ComplianceAssessment,
    Finding,
    Framework,
    Requirement,
    RequirementMapping,
    Section,
)
from context.models import (
    Activity,
    Indicator,
    IndicatorMeasurement,
    Issue,
    Objective,
    Responsibility,
    Role,
    Scope,
    Site,
    Stakeholder,
    StakeholderExpectation,
    SwotAnalysis,
    SwotItem,
    SwotStrategy,
    Tag,
)
from reports.models.management_review import (
    ManagementReview,
    ManagementReviewDecision,
    ManagementReviewParticipant,
)
from risks.models import (
    AttackPathStep,
    BaselineGap,
    EcosystemStakeholder,
    FearedEvent,
    ISO27005Risk,
    Risk,
    RiskAcceptance,
    RiskAssessment,
    RiskCriteria,
    RiskLevel,
    RiskSource,
    RiskSourceObjectivePair,
    RiskTreatmentPlan,
    ScaleLevel,
    StrategicScenario,
    TargetedObjective,
    Threat,
    TreatmentAction,
    Vulnerability,
)
from trust_center.constants import DocumentAccess, PublicationState
from trust_center.models import (
    DocumentRequest,
    TrustCenterCertification,
    TrustCenterDocument,
    TrustCenterMeasure,
    TrustCenterSettings,
    TrustCenterSubprocessor,
)

import json
import random as _random

TBL = {}
exec(open("scripts/seed_demo_tables.py").read(), TBL)

# Bulk demo content (50+ items per category) generated for Voltara Energy and
# stored as data so this script stays readable. Consumed by the bulk-volume
# section, which wires the foreign keys to the curated objects.
BULK = json.load(open("scripts/seed_bulk_data.json"))
RNG = _random.Random(20260625)  # deterministic sampling for reproducible seeds

NOW = timezone.now()
TODAY = NOW.date()
PASSWORD = "VoltaraDemo!2026"


# All demo dates are derived from TODAY so the dataset never goes stale: audits
# stay completed and in the past, contracts keep realistic horizons, and
# upcoming reviews stay in the near future regardless of when the seed is run.
def days_ago(n):
    return TODAY - timedelta(days=n)


def days_ahead(n):
    return TODAY + timedelta(days=n)


def months_ago(n):
    return TODAY - timedelta(days=round(30.4 * n))


def months_ahead(n):
    return TODAY + timedelta(days=round(30.4 * n))


def years_ago(n):
    return TODAY - timedelta(days=round(365.25 * n))


def years_ahead(n):
    return TODAY + timedelta(days=round(365.25 * n))


def semester_label(d):
    """`H1 YYYY` / `H2 YYYY` for a date, for management-review titles."""
    return f"H{1 if d.month <= 6 else 2} {d.year}"


# Real city coordinates per country so every supplier hero map renders a marker
# at a plausible location on a fresh seed. The supplier map uses the stored
# latitude/longitude first and only falls back to geocoding the address text, so
# seeding both keeps the maps working offline and pin-accurate.
SUPPLIER_CITIES = {
    "France": ("Paris", 48.8566, 2.3522),
    "Germany": ("Berlin", 52.5200, 13.4050),
    "Netherlands": ("Amsterdam", 52.3676, 4.9041),
    "Ireland": ("Dublin", 53.3498, -6.2603),
    "Spain": ("Madrid", 40.4168, -3.7038),
    "Sweden": ("Stockholm", 59.3293, 18.0686),
    "Switzerland": ("Zurich", 47.3769, 8.5417),
    "Austria": ("Vienna", 48.2082, 16.3738),
    "Denmark": ("Copenhagen", 55.6761, 12.5683),
    "Norway": ("Oslo", 59.9139, 10.7522),
    "Finland": ("Helsinki", 60.1699, 24.9384),
}


def supplier_location(country):
    """A plausible (address, latitude, longitude) for a supplier in `country`.

    The street is generated; the city and base coordinates are real, with a
    small jitter so markers do not all stack on the exact city centre.
    """
    city, lat, lon = SUPPLIER_CITIES.get(country, SUPPLIER_CITIES["France"])
    street = RNG.choice([
        "Innovation Avenue", "Technology Park", "Business Center", "Commerce Square",
        "Industrial Estate", "Office Quarter", "Enterprise Way", "Market Street",
    ])
    address = f"{RNG.randint(1, 200)} {street}, {city}, {country}"
    return (
        address,
        round(lat + RNG.uniform(-0.04, 0.04), 6),
        round(lon + RNG.uniform(-0.04, 0.04), 6),
    )


def approved(user):
    """Kwargs marking a default-lifecycle object as validated."""
    return {
        "created_by": user,
        "is_approved": True,
        "approved_by": user,
        "approved_at": NOW,
    }


with transaction.atomic():
    # ------------------------------------------------------------------ users
    print("Users and groups...")
    elise = User.objects.create_superuser(
        email="elise.moreau@voltara.example", password=PASSWORD,
        first_name="Elise", last_name="Moreau",
    )
    elise.job_title = "Chief Information Security Officer"
    elise.department = "Security"
    elise.language = "en"
    elise.save()

    def mk_user(email, first, last, job, dept, creator=None):
        u = User.objects.create_user(
            email=email, password=PASSWORD, first_name=first, last_name=last,
            job_title=job, department=dept, language="en",
            created_by=creator or elise,
        )
        return u

    david = mk_user("david.morel@voltara.example", "David", "Morel", "Chief Information Officer", "IT")
    marc = mk_user("marc.lefevre@voltara.example", "Marc", "Lefevre", "IT Operations Manager", "IT")
    amelia = mk_user("amelia.rossi@voltara.example", "Amelia", "Rossi", "Data Protection Officer", "Legal")
    thomas = mk_user("thomas.barre@voltara.example", "Thomas", "Barre", "OT & SCADA Manager", "Industrial Operations")
    ines = mk_user("ines.dubois@voltara.example", "Ines", "Dubois", "Compliance Officer", "Security")
    julien = mk_user("julien.petit@voltara.example", "Julien", "Petit", "Risk Analyst", "Security")
    sofia = mk_user("sofia.lindqvist@voltara.example", "Sofia", "Lindqvist", "Internal Auditor", "Audit")

    Group.objects.get(name="Administrateur").users.add(david)
    Group.objects.get(name="RSSI / DPO").users.add(elise, amelia)
    Group.objects.get(name="Contributeur").users.add(marc, thomas, ines, julien)
    Group.objects.get(name="Auditeur").users.add(sofia)

    cs = CompanySettings.get()
    cs.name = "Voltara Energy"
    cs.address = "18 quai Rambaud\n69002 Lyon, France"
    cs.save()

    # ------------------------------------------------------------------- tags
    print("Tags...")
    tag_scada = Tag.objects.create(name="SCADA", color="#b45309")
    tag_gdpr = Tag.objects.create(name="GDPR", color="#1E3A8A")
    tag_nis2 = Tag.objects.create(name="NIS2", color="#0e7490")
    tag_cloud = Tag.objects.create(name="Cloud", color="#475569")
    tag_critical = Tag.objects.create(name="Critical infrastructure", color="#b91c1c")
    tag_thirdparty = Tag.objects.create(name="Third party", color="#6d28d9")

    # ----------------------------------------------------------------- scopes
    print("Scopes and sites...")
    scope_group = Scope.objects.create(
        name="Voltara Group",
        description="Group-wide information security management system covering corporate IT, industrial operations and customer services.",
        boundaries="All entities operating under the Voltara Energy brand in France.",
        geographic_scope="France",
        organizational_scope="All departments",
        icon="bi-buildings",
        effective_date=months_ago(18),
        review_date=days_ahead(17),
        workflow_state="in_force",
        **approved(elise),
    )
    scope_group.managers.set([elise])
    scope_group.tags.set([tag_critical])

    scope_it = Scope.objects.create(
        name="Corporate IT",
        description="Corporate information systems: ERP, collaboration, customer portal and end-user computing.",
        parent_scope=scope_group,
        icon="bi-pc-display",
        effective_date=months_ago(18),
        workflow_state="in_force",
        **approved(elise),
    )
    scope_it.managers.set([marc])

    scope_ot = Scope.objects.create(
        name="Industrial Operations (OT)",
        description="Industrial control systems for the wind, solar and hydro production fleet: SCADA, PLCs, historian.",
        parent_scope=scope_group,
        icon="bi-lightning-charge",
        effective_date=months_ago(18),
        workflow_state="in_force",
        **approved(elise),
    )
    scope_ot.managers.set([thomas])
    scope_ot.tags.set([tag_scada, tag_critical])

    scope_cust = Scope.objects.create(
        name="Customer Services",
        description="Customer-facing processes: contracting, billing, support and the self-service portal.",
        parent_scope=scope_group,
        icon="bi-people",
        effective_date=months_ago(13),
        workflow_state="in_force",
        **approved(elise),
    )
    scope_cust.managers.set([ines])

    scope_rnd = Scope.objects.create(
        name="R&D Innovation Lab",
        description="Experimental perimeter for grid storage and forecasting research projects.",
        parent_scope=scope_group,
        icon="bi-lightbulb",
        workflow_state="validation",
        created_by=marc,
    )
    all_scopes = [scope_group, scope_it, scope_ot, scope_cust]

    site_hq = Site.objects.create(
        name="Lyon HQ", type="headquarters",
        address="18 quai Rambaud, 69002 Lyon, France", **approved(elise),
    )
    site_dc = Site.objects.create(
        name="Roubaix Datacenter", type="datacenter",
        address="Parc des Moulins, 59100 Roubaix, France",
        description="Colocation datacenter hosting production IT workloads.", **approved(elise),
    )
    site_wind = Site.objects.create(
        name="Normandy Wind Farm", type="factory",
        address="Plateau du Neubourg, 27110 Le Neubourg, France",
        description="48-turbine onshore wind farm with local control room.", **approved(elise),
    )
    site_solar = Site.objects.create(
        name="Provence Solar Plant", type="factory",
        address="Route de la Durance, 04100 Manosque, France", **approved(elise),
    )
    site_hydro = Site.objects.create(
        name="Alpine Hydro Station", type="factory",
        address="Vallee de la Romanche, 38220 Livet-et-Gavet, France", **approved(elise),
    )
    site_office = Site.objects.create(
        name="Bordeaux Regional Office", type="office",
        address="12 cours du Medoc, 33300 Bordeaux, France", **approved(elise),
    )
    all_sites = [site_hq, site_dc, site_wind, site_solar, site_hydro, site_office]
    for s in all_sites:
        s.scopes.set([scope_group])
    site_wind.scopes.add(scope_ot)
    site_solar.scopes.add(scope_ot)
    site_hydro.scopes.add(scope_ot)
    site_dc.scopes.add(scope_it)
    scope_group.included_sites.set(all_sites)
    scope_ot.included_sites.set([site_wind, site_solar, site_hydro])
    scope_it.included_sites.set([site_hq, site_dc, site_office])

    # ------------------------------------------------------------ stakeholders
    print("Stakeholders, issues, expectations...")
    sh_regulator = Stakeholder.objects.create(
        name="Energy Regulatory Commission", type="external", category="regulators",
        description="National regulator overseeing energy market operators.",
        influence_level="high", interest_level="high",
        contact_email="contact@regulator.example", **approved(elise),
    )
    sh_anssi = Stakeholder.objects.create(
        name="National Cybersecurity Agency", type="external", category="regulators",
        description="NIS2 competent authority for essential entities.",
        influence_level="high", interest_level="medium", **approved(elise),
    )
    sh_grid = Stakeholder.objects.create(
        name="National Grid Operator", type="external", category="partners",
        description="Transmission system operator; real-time interconnection with dispatch.",
        influence_level="high", interest_level="high", **approved(elise),
    )
    sh_customers = Stakeholder.objects.create(
        name="Industrial Customers", type="external", category="customers",
        description="B2B customers under long-term power purchase agreements.",
        influence_level="medium", interest_level="high", **approved(elise),
    )
    sh_employees = Stakeholder.objects.create(
        name="Employees & Works Council", type="internal", category="employees",
        influence_level="medium", interest_level="medium", **approved(elise),
    )
    sh_excom = Stakeholder.objects.create(
        name="Executive Committee", type="internal", category="executive_management",
        influence_level="high", interest_level="high", **approved(elise),
    )
    sh_insurer = Stakeholder.objects.create(
        name="Cyber Insurance Provider", type="external", category="insurers",
        influence_level="medium", interest_level="medium", **approved(elise),
    )
    for sh in [sh_regulator, sh_anssi, sh_grid, sh_customers, sh_employees, sh_excom, sh_insurer]:
        sh.scopes.set([scope_group])

    StakeholderExpectation.objects.create(
        stakeholder=sh_anssi, type="requirement", priority="critical",
        description="Significant incidents reported within 24 hours (NIS2 early warning).",
    )
    StakeholderExpectation.objects.create(
        stakeholder=sh_customers, type="expectation", priority="high",
        description="99.9% availability of contracted energy delivery and customer portal.",
    )
    StakeholderExpectation.objects.create(
        stakeholder=sh_insurer, type="requirement", priority="high",
        description="Multi-factor authentication enforced on all remote and privileged access.",
    )
    StakeholderExpectation.objects.create(
        stakeholder=sh_excom, type="requirement", priority="critical",
        description="ISO/IEC 27001 certification obtained within the next 12 months.",
    )

    issue_nis2 = Issue.objects.create(
        name="NIS2 enforcement deadline", type="external", category="regulatory",
        description="Voltara qualifies as an essential entity; full compliance evidence is expected at the next supervision cycle.",
        impact_level="critical", trend="degrading", status="active",
        source="Legal watch", review_date=months_ahead(2), **approved(elise),
    )
    issue_ransomware = Issue.objects.create(
        name="Ransomware wave targeting energy operators", type="external", category="technological",
        description="Sector CERT reports a sustained increase in ransomware intrusions affecting European utilities.",
        impact_level="high", trend="degrading", status="active", **approved(elise),
    )
    issue_market = Issue.objects.create(
        name="Energy market price volatility", type="external", category="economic",
        impact_level="medium", trend="stable", status="monitored", **approved(elise),
    )
    issue_scada = Issue.objects.create(
        name="Aging SCADA infrastructure", type="internal", category="technical",
        description="Part of the supervision stack runs on systems close to end of support.",
        impact_level="high", trend="stable", status="active", **approved(elise),
    )
    issue_talent = Issue.objects.create(
        name="Cybersecurity talent shortage", type="internal", category="human_resources",
        impact_level="medium", trend="degrading", status="active", **approved(elise),
    )
    issue_esg = Issue.objects.create(
        name="Climate commitments and ESG reporting", type="external", category="environmental",
        impact_level="medium", trend="improving", status="monitored", **approved(elise),
    )
    for i in [issue_nis2, issue_ransomware, issue_market, issue_scada, issue_talent, issue_esg]:
        i.scopes.set([scope_group])
    issue_nis2.related_stakeholders.set([sh_anssi, sh_regulator])
    issue_ransomware.related_stakeholders.set([sh_insurer])
    issue_scada.related_stakeholders.set([sh_grid])

    # --------------------------------------------------------------- objectives
    print("Objectives, SWOT, roles, activities...")
    obj_iso = Objective.objects.create(
        name="Achieve ISO/IEC 27001 certification", category="compliance", type="compliance",
        description="Pass the stage 1 and stage 2 certification audits on the group ISMS scope.",
        owner=elise, status="active", target_value="100", current_value="72", unit="%",
        measurement_frequency="quarterly", progress_percentage=72,
        target_date=months_ahead(6), review_date=days_ago(3), **approved(elise),
    )
    obj_phishing = Objective.objects.create(
        name="Phishing click rate below 5%", category="confidentiality", type="security",
        owner=elise, status="active", target_value="5", current_value="4.8", unit="%",
        measurement_frequency="monthly", progress_percentage=85,
        target_date=months_ahead(6), **approved(elise),
    )
    obj_mfa = Objective.objects.create(
        name="100% MFA coverage on privileged access", category="confidentiality", type="security",
        owner=marc, status="active", target_value="100", current_value="97", unit="%",
        measurement_frequency="monthly", progress_percentage=97,
        target_date=months_ahead(3), **approved(elise),
    )
    obj_scada = Objective.objects.create(
        name="SCADA availability at 99.95%", category="availability", type="business",
        owner=thomas, status="active", target_value="99.95", current_value="99.91", unit="%",
        measurement_frequency="monthly", progress_percentage=90,
        target_date=months_ahead(6), **approved(elise),
    )
    obj_nis2 = Objective.objects.create(
        name="NIS2 compliance programme completed", category="compliance", type="compliance",
        owner=amelia, status="active", target_value="100", current_value="55", unit="%",
        measurement_frequency="quarterly", progress_percentage=55,
        target_date=days_ahead(111), **approved(elise),
    )
    obj_edr = Objective.objects.create(
        name="EDR deployed on all workstations", category="integrity", type="security",
        owner=marc, status="achieved", target_value="100", current_value="100", unit="%",
        measurement_frequency="monthly", progress_percentage=100,
        target_date=months_ago(3), **approved(elise),
    )
    for o in [obj_iso, obj_phishing, obj_mfa, obj_scada, obj_nis2, obj_edr]:
        o.scopes.set([scope_group])
    obj_nis2.related_issues.set([issue_nis2])
    obj_iso.related_stakeholders.set([sh_excom])

    swot_analysis_date = months_ago(4)
    swot = SwotAnalysis.objects.create(
        name=f"{swot_analysis_date.year} Security posture SWOT",
        description="Annual strategic review of the security programme ahead of the certification audit.",
        analysis_date=swot_analysis_date,
        review_date=swot_analysis_date + timedelta(days=365),
        validated_by=elise, validated_at=NOW, **approved(elise),
    )
    swot.scopes.set([scope_group])
    swot_items = [
        ("strength", "Dedicated 24x7 SOC with managed detection on IT and a maturing OT coverage", "high"),
        ("strength", "Strong OT engineering culture and documented operating procedures on plants", "medium"),
        ("weakness", "Legacy SCADA components close to end of support in two plants", "high"),
        ("weakness", "Single production datacenter without an active recovery site", "high"),
        ("opportunity", "NIS2 programme unlocks budget for OT segmentation and monitoring", "high"),
        ("opportunity", "Cloud migration simplifies patching and disaster recovery", "medium"),
        ("threat", "Ransomware groups actively targeting European energy operators", "high"),
        ("threat", "Supply chain compromise through industrial vendors' remote access", "high"),
    ]
    for order, (quadrant, desc, impact) in enumerate(swot_items, 1):
        SwotItem.objects.create(
            swot_analysis=swot, quadrant=quadrant, description=desc,
            impact_level=impact, order=order,
        )
    SwotStrategy.objects.create(
        swot_analysis=swot, quadrant="so", order=1,
        description="Use the SOC maturity and NIS2 budget to extend detection coverage to all OT segments.",
    )
    SwotStrategy.objects.create(
        swot_analysis=swot, quadrant="wt", order=2,
        description="Prioritise segmentation and immutable backups to contain ransomware impact on legacy SCADA.",
    )

    role_ciso = Role.objects.create(
        name="Chief Information Security Officer", type="governance", is_mandatory=True,
        source_standard="ISO/IEC 27001:2022 clause 5.3", **approved(elise),
    )
    role_ciso.assigned_users.set([elise])
    role_dpo = Role.objects.create(
        name="Data Protection Officer", type="governance", is_mandatory=True,
        source_standard="GDPR article 37", **approved(elise),
    )
    role_dpo.assigned_users.set([amelia])
    role_soc = Role.objects.create(
        name="SOC Manager", type="operational", is_mandatory=True,
        description="Leads detection and response operations; recruitment in progress.",
        **approved(elise),
    )
    role_irl = Role.objects.create(
        name="Incident Response Lead", type="operational", **approved(elise),
    )
    role_irl.assigned_users.set([marc])
    role_bcm = Role.objects.create(
        name="Business Continuity Manager", type="governance", is_mandatory=True,
        source_standard="ISO 22301", **approved(elise),
    )
    role_bcm.assigned_users.set([david])
    for r in [role_ciso, role_dpo, role_soc, role_irl, role_bcm]:
        r.scopes.set([scope_group])

    act_generation = Activity.objects.create(
        name="Electricity generation", type="core_business", criticality="critical",
        description="Operation of the wind, solar and hydro production fleet.",
        owner=thomas, status="active", **approved(elise),
    )
    act_trading = Activity.objects.create(
        name="Energy trading & forecasting", type="core_business", criticality="high",
        owner=david, status="active", **approved(elise),
    )
    act_billing = Activity.objects.create(
        name="Customer billing", type="support", criticality="high",
        owner=ines, status="active", **approved(elise),
    )
    act_maintenance = Activity.objects.create(
        name="Plant maintenance", type="core_business", criticality="high",
        owner=thomas, status="active", **approved(elise),
    )
    act_itsm = Activity.objects.create(
        name="IT service management", type="support", criticality="medium",
        owner=marc, status="active", **approved(elise),
    )
    act_reporting = Activity.objects.create(
        name="Regulatory reporting", type="management", criticality="medium",
        owner=amelia, status="active", **approved(elise),
    )
    for a in [act_generation, act_trading, act_billing, act_maintenance, act_itsm, act_reporting]:
        a.scopes.set([scope_group])
    act_generation.scopes.add(scope_ot)
    act_maintenance.scopes.add(scope_ot)
    act_billing.scopes.add(scope_cust)
    act_generation.related_objectives.set([obj_scada])
    act_reporting.related_stakeholders.set([sh_regulator, sh_anssi])

    Responsibility.objects.create(
        role=role_ciso, raci_type="accountable",
        description="Owns the ISMS, the risk register and the security budget.",
    )
    Responsibility.objects.create(
        role=role_dpo, raci_type="accountable",
        description="Maintains the records of processing and handles data subject requests.",
        related_activity=act_billing,
    )
    Responsibility.objects.create(
        role=role_irl, raci_type="responsible",
        description="Coordinates incident triage, containment and post-incident reviews.",
    )
    Responsibility.objects.create(
        role=role_bcm, raci_type="responsible",
        description="Maintains continuity plans for generation and dispatch activities.",
        related_activity=act_generation,
    )

    # ------------------------------------------------------------------ assets
    print("Suppliers and assets...")
    st_cloud = SupplierType.objects.create(
        name="Cloud & hosting provider", description="IaaS, PaaS and colocation suppliers.",
    )
    st_mssp = SupplierType.objects.create(
        name="Managed security services", description="SOC, detection and response providers.",
    )
    st_industrial = SupplierType.objects.create(
        name="Industrial equipment vendor", description="Turbine, PLC and SCADA vendors.",
    )
    st_saas = SupplierType.objects.create(
        name="SaaS vendor", description="Software-as-a-service business applications.",
    )
    st_facility = SupplierType.objects.create(
        name="Facility services", description="Maintenance, cleaning and physical services.",
    )
    str_iso_cert = SupplierTypeRequirement.objects.create(
        supplier_type=st_cloud, title="Valid ISO/IEC 27001 certification",
        description="Certificate covering the hosting scope, renewed annually.",
    )
    str_eu_data = SupplierTypeRequirement.objects.create(
        supplier_type=st_cloud, title="EU data residency",
        description="All customer data stored and processed within the EU.",
    )
    str_soc2 = SupplierTypeRequirement.objects.create(
        supplier_type=st_mssp, title="Independent assurance report (SOC 2 type II)",
    )
    str_patch_sla = SupplierTypeRequirement.objects.create(
        supplier_type=st_industrial, title="Security patch SLA on industrial firmware",
        description="Critical vulnerabilities patched or mitigated within 30 days.",
    )
    str_dpa = SupplierTypeRequirement.objects.create(
        supplier_type=st_saas, title="GDPR data processing agreement",
    )

    sup_cloudnord = Supplier.objects.create(
        name="CloudNord", type=st_cloud, criticality="critical",
        description="IaaS and colocation provider hosting production workloads.",
        contact_name="Account team", contact_email="account@cloudnord.example",
        country="France", contract_reference="CTR-2024-031",
        address="2 Rue Kellermann, 59100 Roubaix, France",
        latitude=50.6916, longitude=3.2014,
        contract_start_date=months_ago(28), contract_end_date=months_ahead(8),
        owner=marc, status="active", **approved(elise),
    )
    sup_sentinel = Supplier.objects.create(
        name="SentinelWatch", type=st_mssp, criticality="high",
        description="24x7 managed SOC operating the SIEM platform.",
        country="France", contract_reference="CTR-2023-104",
        address="92 Avenue des Champs-Elysees, 75008 Paris, France",
        latitude=48.8698, longitude=2.3079,
        contract_start_date=years_ago(3), contract_end_date=days_ahead(2),
        owner=elise, status="active", **approved(elise),
    )
    sup_turbintech = Supplier.objects.create(
        name="TurbinTech GmbH", type=st_industrial, criticality="high",
        description="Turbine vendor with permanent remote maintenance access.",
        country="Germany", contract_reference="CTR-2022-018",
        address="Dreekamp 5, 26605 Aurich, Germany",
        latitude=53.4719, longitude=7.4828,
        contract_start_date=years_ago(4.5), contract_end_date=years_ahead(2.5),
        owner=thomas, status="active", **approved(elise),
    )
    sup_paycore = Supplier.objects.create(
        name="PayCore", type=st_saas, criticality="high",
        description="Payment processing service for customer invoicing.",
        country="Netherlands", contract_reference="CTR-2024-077",
        address="Simon Carmiggeltstraat 6-50, 1011 DJ Amsterdam, Netherlands",
        latitude=52.3743, longitude=4.9009,
        contract_start_date=months_ago(22), contract_end_date=months_ahead(14),
        owner=ines, status="active", **approved(elise),
    )
    sup_hrline = Supplier.objects.create(
        name="HRline", type=st_saas, criticality="medium",
        description="HR information system (SaaS).",
        country="France", address="32 Rue de la Republique, 69002 Lyon, France",
        latitude=45.7640, longitude=4.8357,
        contract_start_date=years_ago(3.5),
        contract_end_date=months_ahead(6), owner=amelia, status="active", **approved(elise),
    )
    sup_facil = Supplier.objects.create(
        name="FacilEnergie Services", type=st_facility, criticality="low",
        description="Facility maintenance for the Lyon HQ; contract renewal under negotiation.",
        country="France", contract_reference="CTR-2021-090",
        address="47 Cours Emile Zola, 69100 Villeurbanne, France",
        latitude=45.7679, longitude=4.8795,
        contract_start_date=years_ago(5), contract_end_date=days_ago(59),
        owner=david, status="active", **approved(elise),
    )
    all_suppliers = [sup_cloudnord, sup_sentinel, sup_turbintech, sup_paycore, sup_hrline, sup_facil]
    for s in all_suppliers:
        s.scopes.set([scope_group])
        s.tags.set([tag_thirdparty])

    # ── Contracts (Documents) ────────────────────────────────
    print("Contracts...")
    _demo_pdf = (
        b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
        b"2 0 obj<</Type/Pages/Kids[]/Count 0>>endobj\ntrailer<</Root 1 0 R>>\n%%EOF\n"
    )

    def _attach_pdf(contract, name):
        contract.file_content = _demo_pdf
        contract.file_name = name
        contract.content_type = "application/pdf"
        contract.save(update_fields=["file_content", "file_name", "content_type"])

    ctr_cloudnord = Contract.objects.create(
        label="CloudNord IaaS master services agreement", status="under_review",
        start_date=months_ago(28), end_date=months_ahead(8),
        amount=480000, currency="EUR",
        notes="Production hosting and colocation. Under periodic renewal review.",
        **approved(elise),
    )
    ctr_cloudnord.scopes.set([scope_group])
    ctr_cloudnord.suppliers.set([sup_cloudnord])
    ctr_cloudnord.clients.set([sh_customers])
    ctr_cloudnord.tags.set([tag_thirdparty])
    _attach_pdf(ctr_cloudnord, "cloudnord-msa-2024.pdf")

    ctr_cloudnord_amendment = Contract.objects.create(
        label="Amendment 1 - additional region (Gravelines)", status="active",
        start_date=months_ago(6), end_date=months_ahead(8),
        amount=60000, currency="EUR", parent=ctr_cloudnord,
        notes="Adds a second availability region for disaster recovery.",
        **approved(elise),
    )
    ctr_cloudnord_amendment.scopes.set([scope_group])
    ctr_cloudnord_amendment.suppliers.set([sup_cloudnord])
    _attach_pdf(ctr_cloudnord_amendment, "cloudnord-amendment-1.pdf")

    ctr_sentinel = Contract.objects.create(
        label="SentinelWatch managed SOC agreement", status="active",
        start_date=years_ago(3), end_date=days_ahead(2),
        amount=240000, currency="EUR",
        notes="24x7 SOC. Expiring soon, renewal in progress.",
        **approved(elise),
    )
    ctr_sentinel.scopes.set([scope_group])
    ctr_sentinel.suppliers.set([sup_sentinel])
    ctr_sentinel.tags.set([tag_thirdparty])

    ctr_sentinel_renewal = Contract.objects.create(
        label="SentinelWatch managed SOC agreement (2026 renewal)", status="active",
        start_date=days_ahead(2), end_date=years_ahead(3),
        amount=255000, currency="EUR", supersedes=ctr_sentinel,
        notes="Renewal that cancels and replaces the 2023 SOC agreement.",
        **approved(elise),
    )
    ctr_sentinel_renewal.scopes.set([scope_group])
    ctr_sentinel_renewal.suppliers.set([sup_sentinel])
    ctr_sentinel_renewal.tags.set([tag_thirdparty])

    ctr_facil = Contract.objects.create(
        label="FacilEnergie facility maintenance (archived)", status="archived",
        start_date=years_ago(5), end_date=days_ago(59),
        amount=85000, currency="EUR",
        notes="Not renewed; replaced by an internal facilities team.",
        **approved(elise),
    )
    ctr_facil.scopes.set([scope_group])
    ctr_facil.suppliers.set([sup_facil])

    ctr_paycore = Contract.objects.create(
        label="PayCore payment processing agreement", status="signing",
        start_date=days_ahead(20), amount=120000, currency="EUR",
        notes="New payment processing contract, awaiting signature by both parties.",
        **approved(elise),
    )
    ctr_paycore.scopes.set([scope_group])
    ctr_paycore.suppliers.set([sup_paycore])
    ctr_paycore.tags.set([tag_thirdparty])

    sr_cloud_iso_due = months_ahead(11)
    sr_cloud_iso = SupplierRequirement.objects.create(
        supplier=sup_cloudnord, source_type_requirement=str_iso_cert,
        title="Valid ISO/IEC 27001 certification", compliance_status="compliant",
        evidence=f"Certificate FR-27001-2210, valid until {sr_cloud_iso_due:%Y-%m}.",
        due_date=sr_cloud_iso_due, verified_at=NOW, verified_by=ines,
    )
    SupplierRequirement.objects.create(
        supplier=sup_cloudnord, source_type_requirement=str_eu_data,
        title="EU data residency", compliance_status="compliant",
        evidence="Contractual annex D; all regions located in France.",
        verified_at=NOW, verified_by=ines,
    )
    sr_sentinel_soc2 = SupplierRequirement.objects.create(
        supplier=sup_sentinel, source_type_requirement=str_soc2,
        title="Independent assurance report (SOC 2 type II)",
        compliance_status="partially_compliant",
        evidence="Latest assurance report received; scope excludes the OT monitoring service.",
    )
    SupplierRequirement.objects.create(
        supplier=sup_turbintech, source_type_requirement=str_patch_sla,
        title="Security patch SLA on industrial firmware",
        compliance_status="non_compliant",
        evidence="Current contract has no security patching commitment.",
        due_date=days_ahead(94),
    )
    SupplierRequirement.objects.create(
        supplier=sup_paycore, source_type_requirement=str_dpa,
        title="GDPR data processing agreement", compliance_status="compliant",
        verified_at=NOW, verified_by=amelia,
    )
    SupplierRequirement.objects.create(
        supplier=sup_hrline, source_type_requirement=str_dpa,
        title="GDPR data processing agreement", compliance_status="not_assessed",
    )
    SupplierRequirementReview.objects.create(
        supplier_requirement=sr_cloud_iso, review_date=days_ago(169),
        reviewer=ines, result="compliant",
        comment="Certificate verified against the accreditation registry.",
    )
    SupplierRequirementReview.objects.create(
        supplier_requirement=sr_sentinel_soc2, review_date=days_ago(115),
        reviewer=ines, result="partially_compliant",
        comment="OT monitoring still out of the assurance scope; uplift requested.",
    )
    SupplierRequirementReview.objects.create(
        supplier_requirement=sr_sentinel_soc2, review_date=days_ago(4),
        reviewer=ines, result="not_assessed",
        comment="Scheduled review of the latest report covering the OT extension.",
    )

    ea_control = EssentialAsset.objects.create(
        name="Energy production control", type="business_process", category="core_process",
        description="Real-time supervision and control of the production fleet.",
        owner=thomas, custodian=marc,
        confidentiality_level=2, integrity_level=4, availability_level=4,
        availability_justification="Loss of supervision forces production curtailment within minutes.",
        max_tolerable_downtime="15 minutes", recovery_time_objective="30 minutes",
        recovery_point_objective="5 minutes", data_classification="restricted",
        status="active", **approved(elise),
    )
    ea_billing = EssentialAsset.objects.create(
        name="Customer billing & invoicing", type="business_process", category="core_process",
        owner=ines, confidentiality_level=3, integrity_level=4, availability_level=3,
        data_classification="confidential", status="active", **approved(elise),
    )
    ea_custdata = EssentialAsset.objects.create(
        name="Customer personal data", type="information", category="personal_data",
        description="Identity, contact and consumption data of 240k customers.",
        owner=amelia, confidentiality_level=4, integrity_level=3, availability_level=2,
        data_classification="confidential", personal_data=True,
        personal_data_categories=["identity", "contact", "billing", "consumption"],
        regulatory_constraints="GDPR; energy sector data retention rules.",
        status="active", **approved(elise),
    )
    ea_forecast = EssentialAsset.objects.create(
        name="Production forecasting models", type="information", category="strategic_data",
        owner=david, confidentiality_level=3, integrity_level=3, availability_level=2,
        data_classification="confidential", status="active", **approved(elise),
    )
    ea_telemetry = EssentialAsset.objects.create(
        name="SCADA telemetry & historian data", type="information", category="operational_data",
        owner=thomas, confidentiality_level=2, integrity_level=4, availability_level=4,
        data_classification="internal", status="active", **approved(elise),
    )
    ea_hr = EssentialAsset.objects.create(
        name="Employee HR data", type="information", category="personal_data",
        owner=amelia, confidentiality_level=4, integrity_level=3, availability_level=2,
        personal_data=True, personal_data_categories=["identity", "payroll", "health"],
        data_classification="restricted", status="active", **approved(elise),
    )
    ea_trading = EssentialAsset.objects.create(
        name="Energy trading positions", type="information", category="financial_data",
        owner=david, confidentiality_level=4, integrity_level=4, availability_level=3,
        data_classification="restricted", status="active", **approved(elise),
    )
    essential_assets = [ea_control, ea_billing, ea_custdata, ea_forecast, ea_telemetry, ea_hr, ea_trading]
    for ea in essential_assets:
        ea.scopes.set([scope_group])
    ea_control.scopes.add(scope_ot)
    ea_telemetry.scopes.add(scope_ot)
    ea_billing.scopes.add(scope_cust)
    ea_custdata.scopes.add(scope_cust)
    ea_control.related_activities.set([act_generation])
    ea_telemetry.related_activities.set([act_generation, act_maintenance])
    ea_billing.related_activities.set([act_billing])
    ea_trading.related_activities.set([act_trading])
    ea_custdata.tags.set([tag_gdpr])
    ea_hr.tags.set([tag_gdpr])
    ea_control.tags.set([tag_scada, tag_critical])

    sa_scada = SupportAsset.objects.create(
        name="SCADA supervision servers", type="hardware", category="server",
        description="Redundant pair of supervision servers in the wind farm control room.",
        owner=thomas, location="Normandy Wind Farm", environment="production",
        exposure_level="internal", operating_system="Windows Server 2019",
        acquisition_date=years_ago(5), end_of_life_date=years_ahead(3),
        status="active", **approved(elise),
    )
    sa_historian = SupportAsset.objects.create(
        name="Plant historian database", type="software", category="database",
        description="Single-instance process historian aggregating telemetry from all plants.",
        owner=thomas, environment="production", exposure_level="internal",
        software_version="9.2", status="active", **approved(elise),
    )
    sa_portal = SupportAsset.objects.create(
        name="Customer portal", type="software", category="application",
        description="Self-service portal for contracts, invoices and consumption data.",
        owner=ines, environment="production", exposure_level="internet_facing",
        supplier=sup_cloudnord, status="active", **approved(elise),
    )
    sa_erp = SupportAsset.objects.create(
        name="ERP & billing platform", type="software", category="application",
        owner=marc, environment="production", exposure_level="internal",
        software_version="2024.2", status="active", **approved(elise),
    )
    sa_ad = SupportAsset.objects.create(
        name="Active Directory", type="software", category="middleware",
        owner=marc, environment="production", exposure_level="internal",
        status="active", **approved(elise),
    )
    sa_vpn = SupportAsset.objects.create(
        name="Perimeter VPN gateway", type="hardware", category="network_equipment",
        description="Remote access gateway for employees and third-party maintainers.",
        owner=marc, environment="production", exposure_level="internet_facing",
        manufacturer="NetSecure", model_name="NS-4400", software_version="10.2.1",
        status="active", **approved(elise),
    )
    sa_plc = SupportAsset.objects.create(
        name="Wind turbine PLCs", type="hardware", category="iot_device",
        description="Programmable controllers embedded in the 48 turbines.",
        owner=thomas, location="Normandy Wind Farm", environment="production",
        exposure_level="internal", manufacturer="TurbinTech", status="active", **approved(elise),
    )
    sa_laptops = SupportAsset.objects.create(
        name="Corporate laptop fleet", type="hardware", category="laptop",
        description="Around 800 managed laptops with EDR and disk encryption.",
        owner=marc, status="active", **approved(elise),
    )
    sa_backup = SupportAsset.objects.create(
        name="Immutable backup vault", type="hardware", category="storage",
        owner=marc, location="Roubaix Datacenter", environment="production",
        status="active", **approved(elise),
    )
    sa_collab = SupportAsset.objects.create(
        name="Collaboration suite", type="software", category="saas_application",
        owner=marc, exposure_level="internet_facing", status="active", **approved(elise),
    )
    sa_metering = SupportAsset.objects.create(
        name="Legacy metering gateway", type="hardware", category="network_equipment",
        description="End-of-life gateway collecting meter data at the hydro station; replacement planned.",
        owner=thomas, location="Alpine Hydro Station", environment="production",
        end_of_life_date=months_ago(3), status="active", **approved(elise),
    )
    sa_wan = SupportAsset.objects.create(
        name="MPLS WAN", type="network", category="wan",
        owner=marc, environment="production", status="active", **approved(elise),
    )
    sa_siem = SupportAsset.objects.create(
        name="SOC SIEM platform", type="software", category="security_tool",
        owner=elise, environment="production", supplier=sup_sentinel,
        status="active", **approved(elise),
    )
    support_assets = [sa_scada, sa_historian, sa_portal, sa_erp, sa_ad, sa_vpn, sa_plc,
                      sa_laptops, sa_backup, sa_collab, sa_metering, sa_wan, sa_siem]
    for sa in support_assets:
        sa.scopes.set([scope_group])
    for sa in [sa_scada, sa_historian, sa_plc, sa_metering]:
        sa.scopes.add(scope_ot)
        sa.tags.add(tag_scada)
    sa_portal.scopes.add(scope_cust)
    sa_portal.tags.add(tag_cloud)
    sa_collab.tags.add(tag_cloud)

    deps = [
        (ea_control, sa_scada, "runs_on", "critical", "partial", False,
         "Supervision runs on the redundant SCADA pair."),
        (ea_control, sa_plc, "managed_by", "critical", "none", True,
         "Turbine control depends on vendor PLCs with no fallback."),
        (ea_control, sa_historian, "stored_in", "high", "none", True,
         "Setpoint history needed for safe restart procedures."),
        (ea_telemetry, sa_historian, "stored_in", "critical", "none", True,
         "Single-instance historian, no replica."),
        (ea_telemetry, sa_scada, "transmitted_by", "high", "partial", False, ""),
        (ea_billing, sa_erp, "runs_on", "high", "partial", False, ""),
        (ea_billing, sa_wan, "transmitted_by", "medium", "full", False, ""),
        (ea_billing, sa_backup, "protected_by", "medium", "full", False, ""),
        (ea_custdata, sa_erp, "stored_in", "high", "partial", False, ""),
        (ea_custdata, sa_portal, "transmitted_by", "high", "partial", False, ""),
        (ea_forecast, sa_historian, "stored_in", "medium", "none", False,
         "Forecast models consume historian feeds."),
        (ea_trading, sa_erp, "stored_in", "critical", "partial", False, ""),
        (ea_hr, sa_collab, "stored_in", "medium", "partial", False, ""),
    ]
    for ea, sa, dtype, crit, redundancy, spof, desc in deps:
        AssetDependency.objects.create(
            essential_asset=ea, support_asset=sa, dependency_type=dtype,
            criticality=crit, redundancy_level=redundancy,
            is_single_point_of_failure=spof, description=desc,
            created_by=julien, is_approved=True, approved_by=elise, approved_at=NOW,
        )

    for sa, sup, dtype, crit, redundancy, spof in [
        (sa_portal, sup_cloudnord, "hosts", "critical", "none", True),
        (sa_erp, sup_cloudnord, "hosts", "high", "partial", False),
        (sa_siem, sup_sentinel, "manages", "high", "none", True),
        (sa_plc, sup_turbintech, "maintains", "high", "partial", False),
        (sa_portal, sup_paycore, "provides", "high", "partial", False),
    ]:
        SupplierDependency.objects.create(
            support_asset=sa, supplier=sup, dependency_type=dtype,
            criticality=crit, redundancy_level=redundancy,
            is_single_point_of_failure=spof,
            created_by=julien, is_approved=True, approved_by=elise, approved_at=NOW,
        )

    for sa, site, dtype, crit, redundancy in [
        (sa_scada, site_wind, "hosted_at", "critical", "none"),
        (sa_historian, site_dc, "hosted_at", "high", "none"),
        (sa_erp, site_dc, "hosted_at", "high", "partial"),
        (sa_vpn, site_hq, "located_at", "high", "none"),
        (sa_metering, site_hydro, "located_at", "medium", "none"),
    ]:
        SiteAssetDependency.objects.create(
            support_asset=sa, site=site, dependency_type=dtype,
            criticality=crit, redundancy_level=redundancy,
            created_by=julien, is_approved=True, approved_by=elise, approved_at=NOW,
        )

    for site, sup, dtype, crit in [
        (site_dc, sup_cloudnord, "hosts", "critical"),
        (site_wind, sup_turbintech, "maintains", "high"),
        (site_hq, sup_facil, "maintains", "medium"),
    ]:
        SiteSupplierDependency.objects.create(
            site=site, supplier=sup, dependency_type=dtype, criticality=crit,
            created_by=julien, is_approved=True, approved_by=elise, approved_at=NOW,
        )

    grp_ot = AssetGroup.objects.create(
        name="OT infrastructure", type="hardware", owner=thomas, status="active",
        description="Industrial control assets across the production plants.",
        **approved(elise),
    )
    grp_ot.members.set([sa_scada, sa_plc, sa_metering])
    grp_cloud = AssetGroup.objects.create(
        name="Cloud & SaaS services", type="software", owner=marc, status="active",
        **approved(elise),
    )
    grp_cloud.members.set([sa_portal, sa_collab, sa_siem])
    grp_euc = AssetGroup.objects.create(
        name="End-user computing", type="hardware", owner=marc, status="active",
        **approved(elise),
    )
    grp_euc.members.set([sa_laptops])
    for g in [grp_ot, grp_cloud, grp_euc]:
        g.scopes.set([scope_group])

    val_custdata_old = years_ago(1)
    val_custdata_new = months_ago(5)
    AssetValuation.objects.create(
        essential_asset=ea_custdata, evaluation_date=val_custdata_old,
        confidentiality_level=3, integrity_level=3, availability_level=2,
        evaluated_by=amelia, context=f"{val_custdata_old.year} annual review",
        justification="Initial valuation at confidential level.",
    )
    AssetValuation.objects.create(
        essential_asset=ea_custdata, evaluation_date=val_custdata_new,
        confidentiality_level=4, integrity_level=3, availability_level=2,
        evaluated_by=amelia, context=f"{val_custdata_new.year} annual review",
        justification="Raised confidentiality after the portal exposure assessment.",
    )
    AssetValuation.objects.create(
        essential_asset=ea_telemetry, evaluation_date=days_ago(136),
        confidentiality_level=2, integrity_level=4, availability_level=4,
        evaluated_by=thomas, context="EBIOS RM workshop 1",
        justification="Integrity and availability drive safe plant operation.",
    )

    # -------------------------------------------------------------- compliance
    print("Frameworks and requirements...")

    def build_framework(meta, sections_table, category_per_section=None, default_priority="medium"):
        fw = Framework.objects.create(**meta)
        fw.scopes.set([scope_group])
        reqs = {}
        for s_idx, (sec_ref, sec_name, items) in enumerate(sections_table, 1):
            section = Section.objects.create(
                framework=fw, reference=sec_ref, name=sec_name, order=s_idx,
            )
            for r_idx, (num, title) in enumerate(items, 1):
                category = (category_per_section or {}).get(sec_ref, "organizational")
                reqs[num] = Requirement.objects.create(
                    framework=fw, section=section, requirement_number=num,
                    name=title,
                    description=f"{title}. Implemented and maintained as part of the Voltara ISMS.",
                    type="mandatory", category=category, priority=default_priority,
                    owner=elise, **approved(elise),
                )
        return fw, reqs

    fw_iso, iso_reqs = build_framework(
        dict(
            name="ISO/IEC 27001:2022", short_name="ISO 27001",
            description="Information security management systems: requirements (Annex A controls).",
            type="standard", category="information_security", framework_version="2022",
            issuing_body="ISO/IEC", is_mandatory=True, owner=elise, status="active",
            effective_date=months_ago(18), review_date=days_ago(39),
            **approved(elise),
        ),
        TBL["ISO27001_SECTIONS"],
        category_per_section={"A.5": "organizational", "A.6": "human", "A.7": "physical", "A.8": "technical"},
    )
    fw_nis2, nis2_reqs = build_framework(
        dict(
            name="NIS2 Directive (EU) 2022/2555", short_name="NIS2",
            description="Measures for a high common level of cybersecurity across the Union.",
            type="regulation", category="sector_specific", jurisdiction="European Union",
            issuing_body="European Union", is_mandatory=True, owner=amelia, status="active",
            effective_date=months_ago(20), **approved(elise),
        ),
        TBL["NIS2_SECTIONS"],
        category_per_section={"Art. 20": "organizational", "Art. 21": "organizational", "Art. 23": "organizational"},
        default_priority="high",
    )
    fw_gdpr, gdpr_reqs = build_framework(
        dict(
            name="General Data Protection Regulation", short_name="GDPR",
            description="Regulation (EU) 2016/679 on the protection of personal data.",
            type="law", category="privacy", jurisdiction="European Union",
            issuing_body="European Union", is_mandatory=True, owner=amelia, status="active",
            effective_date=years_ago(8), **approved(elise),
        ),
        TBL["GDPR_SECTIONS"],
        category_per_section={"Ch. II": "legal", "Ch. III": "legal", "Ch. IV": "organizational"},
    )
    fw_vsb, vsb_reqs = build_framework(
        dict(
            name="Voltara Security Baseline", short_name="VSB",
            description="Internal minimum security requirements applicable to all systems.",
            type="internal_policy", category="internal", framework_version="3.1",
            issuing_body="Voltara Energy", owner=elise, status="active",
            effective_date=months_ago(10), **approved(elise),
        ),
        TBL["BASELINE_SECTIONS"],
        category_per_section={"VSB-1": "technical", "VSB-2": "technical", "VSB-3": "organizational"},
    )
    fw_nis2.tags.set([tag_nis2])
    fw_gdpr.tags.set([tag_gdpr])

    for num in ["A.8.4", "A.8.28", "A.8.30"]:
        r = iso_reqs[num]
        r.is_applicable = False
        r.applicability_justification = "No in-house software development within the certification scope."
        r.save()
    for num in ["A.5.15", "A.5.24", "A.8.7", "A.8.13", "A.8.22", "A.5.19"]:
        r = iso_reqs[num]
        r.priority = "high"
        r.save()

    mappings = [
        (iso_reqs["A.5.24"], nis2_reqs["NIS2-21.b"], "equivalent", "full",
         "Both require an incident management capability with defined responsibilities."),
        (iso_reqs["A.5.30"], nis2_reqs["NIS2-21.c"], "partial_overlap", "partial",
         "ICT readiness for business continuity partially covers the NIS2 continuity measure."),
        (iso_reqs["A.5.19"], nis2_reqs["NIS2-21.d"], "partial_overlap", "partial",
         "Supplier relationship security underpins the NIS2 supply chain measure."),
        (iso_reqs["A.8.5"], nis2_reqs["NIS2-21.j"], "equivalent", "full",
         "Secure authentication maps to the NIS2 multi-factor authentication measure."),
        (iso_reqs["A.6.3"], nis2_reqs["NIS2-21.g"], "equivalent", "full",
         "Awareness and training requirements are aligned."),
        (iso_reqs["A.8.24"], nis2_reqs["NIS2-21.h"], "equivalent", "full",
         "Cryptography policies cover the NIS2 encryption measure."),
        (iso_reqs["A.5.34"], gdpr_reqs["GDPR-32"], "related", "partial",
         "PII protection control supports the GDPR security of processing obligation."),
        (iso_reqs["A.8.13"], vsb_reqs["VSB-2.1"], "includes", "full",
         "The internal backup rule operationalises the Annex A backup control."),
    ]
    for src, tgt, mtype, coverage, justification in mappings:
        RequirementMapping.objects.create(
            source_requirement=src, target_requirement=tgt, mapping_type=mtype,
            coverage_level=coverage, justification=justification, created_by=ines,
        )

    print("Assessments and results...")
    ISO_RESULT_OVERRIDES = {
        "major_non_conformity": ["A.5.26", "A.8.22"],
        "minor_non_conformity": ["A.5.18", "A.5.20", "A.5.21", "A.6.5", "A.7.4", "A.8.8", "A.8.12", "A.8.19"],
        "observation": ["A.8.17", "A.5.13", "A.7.7", "A.8.33", "A.5.28", "A.6.7"],
        "improvement_opportunity": ["A.8.15", "A.5.7", "A.8.16", "A.5.23"],
        "strength": ["A.6.3", "A.8.13", "A.5.24"],
        "not_assessed": ["A.5.32", "A.5.33", "A.5.35", "A.5.36", "A.7.13", "A.7.14", "A.8.34"],
    }
    FINDING_TEXT = {
        "A.5.26": "Incident response procedures exist for IT but have never been exercised on the OT environment.",
        "A.8.22": "The office IT network and the industrial control segments are not strictly segregated.",
        "A.5.18": "Quarterly access reviews are performed but the evidence is not retained.",
        "A.5.20": "Two supplier contracts lack the standard security clauses.",
    }

    def apply_results(assessment, requirements_by_num, overrides):
        status_by_num = {}
        for status_value, nums in overrides.items():
            for num in nums:
                status_by_num[num] = status_value
        for res in assessment.results.select_related("requirement"):
            num = res.requirement.requirement_number
            if res.compliance_status == "not_applicable":
                continue
            status_value = status_by_num.get(num, "compliant")
            res.compliance_status = status_value
            res.compliance_level = COMPLIANCE_LEVEL_DEFAULTS[status_value]
            if num in FINDING_TEXT:
                res.finding = FINDING_TEXT[num]
            if status_value == "compliant":
                res.evidence = "Reviewed during the audit interviews and document sampling."
            res.save()
        assessment.recalculate_counts()

    # Every audit is completed and dated in the past, spread across the last
    # ~8 months, so the assessment register always reads as a mature programme
    # with no half-finished or not-yet-started audits on a fresh seed.
    asm_iso_start, asm_iso_end = days_ago(55), days_ago(35)
    asm_iso = ComplianceAssessment.objects.create(
        name=f"ISO 27001 internal audit {asm_iso_end.year}",
        description="Annual internal audit covering the full Annex A control set before the certification audit.",
        assessor=sofia, created_by=sofia,
        assessment_start_date=asm_iso_start, assessment_end_date=asm_iso_end,
        status="completed",
    )
    asm_iso.scopes.set([scope_group])
    asm_iso.frameworks.set([fw_iso])
    asm_iso.sync_results(sofia)
    apply_results(asm_iso, iso_reqs, ISO_RESULT_OVERRIDES)

    asm_gdpr_start, asm_gdpr_end = days_ago(165), days_ago(147)
    asm_gdpr = ComplianceAssessment.objects.create(
        name=f"GDPR compliance review {asm_gdpr_end.year}",
        assessor=amelia, created_by=amelia,
        assessment_start_date=asm_gdpr_start, assessment_end_date=asm_gdpr_end,
        status="completed",
    )
    asm_gdpr.scopes.set([scope_group])
    asm_gdpr.frameworks.set([fw_gdpr])
    asm_gdpr.sync_results(amelia)
    apply_results(asm_gdpr, gdpr_reqs, {
        "minor_non_conformity": ["GDPR-30", "GDPR-35"],
        "observation": ["GDPR-13"],
        "improvement_opportunity": ["GDPR-28"],
    })

    asm_nis2_start, asm_nis2_end = days_ago(225), days_ago(207)
    asm_nis2 = ComplianceAssessment.objects.create(
        name="NIS2 gap assessment",
        assessor=ines, created_by=ines,
        assessment_start_date=asm_nis2_start, assessment_end_date=asm_nis2_end,
        status="completed",
    )
    asm_nis2.scopes.set([scope_group])
    asm_nis2.frameworks.set([fw_nis2])
    asm_nis2.sync_results(ines)
    apply_results(asm_nis2, nis2_reqs, {
        "major_non_conformity": ["NIS2-23.1"],
        "minor_non_conformity": ["NIS2-21.d", "NIS2-21.j", "NIS2-23.2"],
        "improvement_opportunity": ["NIS2-21.f", "NIS2-21.g"],
        "not_assessed": ["NIS2-20.2", "NIS2-23.3"],
    })

    asm_vsb_start, asm_vsb_end = days_ago(100), days_ago(86)
    asm_vsb = ComplianceAssessment.objects.create(
        name=f"Security baseline self-check {semester_label(asm_vsb_end)}",
        assessor=ines, created_by=ines,
        assessment_start_date=asm_vsb_start, assessment_end_date=asm_vsb_end,
        status="completed",
    )
    asm_vsb.scopes.set([scope_group])
    asm_vsb.frameworks.set([fw_vsb])
    asm_vsb.sync_results(ines)
    apply_results(asm_vsb, vsb_reqs, {
        "major_non_conformity": ["VSB-2.3"],
        "minor_non_conformity": ["VSB-1.2", "VSB-3.3"],
    })

    asm_stage1_start, asm_stage1_end = days_ago(20), days_ago(16)
    asm_stage1 = ComplianceAssessment.objects.create(
        name="ISO 27001 certification audit : stage 1",
        description="Stage 1 documentation review by the certification body.",
        assessor=sofia, created_by=elise,
        assessment_start_date=asm_stage1_start, assessment_end_date=asm_stage1_end,
        status="completed",
    )
    asm_stage1.scopes.set([scope_group])
    asm_stage1.frameworks.set([fw_iso])
    asm_stage1.sync_results(sofia)
    apply_results(asm_stage1, iso_reqs, {
        "observation": ["A.5.1", "A.5.37"],
        "improvement_opportunity": ["A.8.9"],
    })

    # Several audits are deliberately left in progress, on different date ranges
    # and assigned to different assessors, so the demo exercises that state and
    # the "my assessments" / calendar views look realistic. Each one has only a
    # fraction of its controls reviewed so far (mostly compliant with a few
    # findings), the rest still pending. Relative dates keep them always ongoing.
    def seed_in_progress_audit(name, description, framework, assessor, start, end,
                               fraction, findings):
        asm = ComplianceAssessment.objects.create(
            name=name, description=description, assessor=assessor, created_by=assessor,
            assessment_start_date=start, assessment_end_date=end, status="in_progress",
        )
        asm.scopes.set([scope_group])
        asm.frameworks.set([framework])
        asm.sync_results(assessor)
        results = list(
            asm.results.select_related("requirement").order_by("requirement__requirement_number")
        )
        for idx, res in enumerate(results[: int(len(results) * fraction)]):
            if res.compliance_status == "not_applicable":
                continue
            status_value = findings.get(idx, "compliant")
            res.compliance_status = status_value
            res.compliance_level = COMPLIANCE_LEVEL_DEFAULTS[status_value]
            if status_value == "compliant":
                res.evidence = "Reviewed during the audit interviews and sampling."
            res.save()
        asm.recalculate_counts()
        return asm

    seed_in_progress_audit(
        "ISO 27001 certification audit : stage 2",
        "Stage 2 certification audit by the certification body, currently under way.",
        fw_iso, sofia, days_ago(5), days_ahead(9), 0.45,
        {3: "minor_non_conformity", 7: "observation",
         12: "minor_non_conformity", 18: "improvement_opportunity"},
    )
    seed_in_progress_audit(
        "NIS2 annual re-assessment",
        "Annual review of the NIS2 measures, in progress.",
        fw_nis2, ines, days_ago(12), days_ahead(16), 0.6,
        {1: "minor_non_conformity", 4: "improvement_opportunity"},
    )
    seed_in_progress_audit(
        "GDPR processing activities review",
        "Periodic review of the records of processing and security of processing, in progress.",
        fw_gdpr, amelia, days_ago(22), days_ahead(3), 0.35,
        {0: "observation", 3: "minor_non_conformity"},
    )

    f_major = Finding.objects.create(
        assessment=asm_iso, finding_type="major_nc", assessor=sofia, created_by=sofia,
        description=FINDING_TEXT["A.5.26"],
        recommendation="Plan and run at least one OT incident response exercise per year.",
        evidence="Interviews with the OT team; exercise log empty for the plants.",
        workflow_state="validated", is_approved=True, approved_by=elise, approved_at=NOW,
    )
    f_major.requirements.set([iso_reqs["A.5.26"], iso_reqs["A.5.29"]])
    f_minor1 = Finding.objects.create(
        assessment=asm_iso, finding_type="minor_nc", assessor=sofia, created_by=sofia,
        description=FINDING_TEXT["A.5.18"],
        recommendation="Retain signed review records for at least three years.",
        workflow_state="validated", is_approved=True, approved_by=elise, approved_at=NOW,
    )
    f_minor1.requirements.set([iso_reqs["A.5.18"]])
    f_minor2 = Finding.objects.create(
        assessment=asm_iso, finding_type="minor_nc", assessor=sofia, created_by=sofia,
        description=FINDING_TEXT["A.5.20"],
        recommendation="Roll out the contractual security annex at the next renewal.",
        workflow_state="validated", is_approved=True, approved_by=elise, approved_at=NOW,
    )
    f_minor2.requirements.set([iso_reqs["A.5.20"]])
    f_obs = Finding.objects.create(
        assessment=asm_iso, finding_type="observation", assessor=sofia, created_by=sofia,
        description="Time synchronisation relies on a single external NTP source.",
        workflow_state="validated", is_approved=True, approved_by=elise, approved_at=NOW,
    )
    f_obs.requirements.set([iso_reqs["A.8.17"]])
    f_improv = Finding.objects.create(
        assessment=asm_iso, finding_type="improvement", assessor=sofia, created_by=sofia,
        description="OT log sources are not yet consolidated on the SIEM.",
        workflow_state="validated", is_approved=True, approved_by=elise, approved_at=NOW,
    )
    f_improv.requirements.set([iso_reqs["A.8.15"]])
    f_strength = Finding.objects.create(
        assessment=asm_iso, finding_type="strength", assessor=sofia, created_by=sofia,
        description="Mature phishing simulation programme with steadily decreasing click rates.",
        workflow_state="validated", is_approved=True, approved_by=elise, approved_at=NOW,
    )
    f_strength.requirements.set([iso_reqs["A.6.3"]])

    print("Action plans...")
    ap_ot_exercise = ComplianceActionPlan.objects.create(
        name="Run OT incident response exercises",
        description="Close the major non-conformity raised by the latest internal audit.",
        gap_description="Incident response has never been exercised on the industrial environment.",
        remediation_plan="Design an OT tabletop scenario, run it with the plant teams, capture lessons learned and update the runbooks.",
        priority="critical", owner=elise, created_by=elise,
        start_date=days_ago(58), target_date=days_ahead(64),
        progress_percentage=35, status="to_implement",
    )
    ap_ot_exercise.scopes.set([scope_ot])
    ap_ot_exercise.findings.set([f_major])
    ap_ot_exercise.requirements.set([iso_reqs["A.5.26"]])
    ap_ot_exercise.assignees.set([thomas, marc])
    c1 = ActionPlanComment.objects.create(
        action_plan=ap_ot_exercise, author=ines,
        content="Tabletop scenario drafted; waiting for a date with the plant operations team.",
    )
    ActionPlanComment.objects.create(
        action_plan=ap_ot_exercise, author=thomas, parent=c1,
        content="Proposed early next month, control room available on a Tuesday.",
    )

    ap_evidence = ComplianceActionPlan.objects.create(
        name="Retain access review evidence",
        gap_description="Quarterly access reviews leave no retained evidence.",
        remediation_plan="Introduce a signed review log stored in the GRC tool with a 3-year retention.",
        priority="high", owner=marc, created_by=ines,
        start_date=days_ago(88), target_date=days_ago(3),
        progress_percentage=80, status="implementation_to_validate",
    )
    ap_evidence.scopes.set([scope_it])
    ap_evidence.findings.set([f_minor1])
    ap_evidence.requirements.set([iso_reqs["A.5.18"]])
    ap_evidence.assignees.set([marc])

    ap_contracts = ComplianceActionPlan.objects.create(
        name="Add security clauses to supplier contracts",
        gap_description="Two supplier contracts lack security and audit clauses.",
        remediation_plan="Negotiate the standard security annex with TurbinTech and FacilEnergie at renewal.",
        priority="high", owner=ines, created_by=ines,
        start_date=days_ago(119), target_date=days_ago(29),
        progress_percentage=60, status="to_implement",
    )
    ap_contracts.scopes.set([scope_group])
    ap_contracts.findings.set([f_minor2])
    ap_contracts.requirements.set([iso_reqs["A.5.20"]])

    ap_ntp = ComplianceActionPlan.objects.create(
        name="Deploy redundant time sources",
        gap_description="Single NTP source for the whole infrastructure.",
        remediation_plan="Add a second independent NTP source and monitor drift.",
        priority="medium", owner=marc, created_by=marc,
        target_date=days_ahead(17), progress_percentage=10, status="to_validate",
    )
    ap_ntp.scopes.set([scope_it])
    ap_ntp.findings.set([f_obs])

    ap_siem_ot = ComplianceActionPlan.objects.create(
        name="Extend SIEM coverage to OT",
        gap_description="No centralised detection on industrial network segments.",
        remediation_plan="Deploy collection probes on OT segments and onboard sources to the managed SOC.",
        priority="high", owner=elise, created_by=elise,
        target_date=days_ahead(124), status="to_define",
    )
    ap_siem_ot.scopes.set([scope_ot])
    ap_siem_ot.findings.set([f_improv])

    ap_nis2_runbook = ComplianceActionPlan.objects.create(
        name="NIS2 incident reporting runbook",
        gap_description="The 24-hour early warning obligation cannot be met reliably today.",
        remediation_plan="Define the notification workflow, templates and on-call escalation to meet the 24h/72h deadlines.",
        priority="critical", owner=amelia, created_by=amelia,
        start_date=days_ago(48), target_date=days_ahead(6),
        progress_percentage=50, status="to_implement",
    )
    ap_nis2_runbook.scopes.set([scope_group])
    ap_nis2_runbook.requirements.set([nis2_reqs["NIS2-23.1"], nis2_reqs["NIS2-23.2"]])

    ap_historian_enc = ComplianceActionPlan.objects.create(
        name="Encrypt historian database at rest",
        gap_description="Telemetry historian stored unencrypted.",
        remediation_plan="Enable transparent data encryption and rotate keys via the HSM.",
        priority="high", owner=thomas, created_by=thomas,
        start_date=days_ago(147), target_date=days_ago(74),
        completion_date=days_ago(79), progress_percentage=100, status="closed",
    )
    ap_historian_enc.scopes.set([scope_ot])

    ap_mfa_contractors = ComplianceActionPlan.objects.create(
        name="Enforce MFA on contractor accounts",
        gap_description="Third-party maintenance accounts authenticated with passwords only.",
        remediation_plan="Issue hardware tokens to maintainers and enforce MFA on the VPN profile.",
        priority="high", owner=marc, created_by=marc,
        start_date=days_ago(164), target_date=days_ago(89),
        completion_date=days_ago(95), progress_percentage=100, status="closed",
    )
    ap_mfa_contractors.scopes.set([scope_it])

    ComplianceActionPlan.objects.create(
        name="Replace legacy metering gateway",
        gap_description="End-of-life gateway at the hydro station.",
        remediation_plan="Superseded by the OT segmentation programme which includes the replacement.",
        priority="medium", owner=thomas, created_by=thomas,
        target_date=days_ahead(94), status="cancelled",
    ).scopes.set([scope_ot])

    # ------------------------------------------------------------------- risks
    print("Risk criteria, threats, vulnerabilities...")
    criteria = RiskCriteria.objects.create(
        name="Voltara corporate risk criteria (5x5)",
        description="Group-wide likelihood and impact scales with a 5-level risk grid.",
        acceptance_threshold=2, is_default=True, **approved(elise),
    )
    criteria.scopes.set([scope_group])
    for lvl, nm, desc in [
        (1, "Rare", "Not expected within 5 years"), (2, "Unlikely", "Could occur within 5 years"),
        (3, "Possible", "Could occur within a year"), (4, "Likely", "Expected within a year"),
        (5, "Almost certain", "Occurs several times a year"),
    ]:
        ScaleLevel.objects.create(criteria=criteria, scale_type="likelihood", level=lvl, name=nm, description=desc)
    for lvl, nm, desc in [
        (1, "Negligible", "No noticeable business effect"), (2, "Minor", "Limited, contained effect"),
        (3, "Moderate", "Degraded operations or local regulatory exposure"),
        (4, "Major", "Production losses, significant regulatory or financial impact"),
        (5, "Severe", "Safety impact, prolonged outage or existential financial impact"),
    ]:
        ScaleLevel.objects.create(criteria=criteria, scale_type="impact", level=lvl, name=nm, description=desc)
    for lvl, nm, color, treat in [
        (1, "Very low", "#4caf50", False), (2, "Low", "#8bc34a", False),
        (3, "Moderate", "#ffc107", False), (4, "High", "#ff9800", True),
        (5, "Critical", "#e53935", True),
    ]:
        RiskLevel.objects.create(criteria=criteria, level=lvl, name=nm, color=color, requires_treatment=treat)
    criteria.rebuild_risk_matrix()

    threat_objs = {}
    THREAT_META = {
        "Ransomware attack": ("human_external", "ransomware", 4),
        "Phishing and credential theft": ("human_external", "social_engineering", 5),
        "Compromise of remote access": ("human_external", "unauthorized_access", 4),
        "Supply chain compromise": ("human_external", "supply_chain", 3),
        "Insider data exfiltration": ("human_internal", "insider_threat", 2),
        "Denial of service on customer portal": ("human_external", "denial_of_service", 3),
        "Sabotage of industrial control systems": ("human_external", "sabotage", 2),
        "Accidental misconfiguration": ("human_internal", "human_error", 4),
        "Loss of key personnel": ("human_internal", "human_error", 3),
        "Datacenter power failure": ("technical", "power_failure", 2),
        "Flooding of hydro control room": ("natural", "water_damage", 1),
    }
    for name, ttype, desc in TBL["THREATS"]:
        origin, category, likelihood = THREAT_META[name]
        threat_objs[name] = Threat.objects.create(
            name=name, type=ttype, description=desc, origin=origin,
            category=category, typical_likelihood=likelihood, status="active",
            **approved(elise),
        )
        threat_objs[name].scopes.set([scope_group])
    Threat.objects.create(
        name="AI-assisted social engineering", type="deliberate",
        description="Voice cloning and tailored lures generated with AI tooling.",
        origin="human_external", category="social_engineering", typical_likelihood=3,
        status="active", workflow_state="pending", created_by=julien,
    ).scopes.set([scope_group])

    vuln_objs = {}
    VULN_META = {
        "Unpatched VPN gateway firmware": ("missing_patch", "confirmed", [sa_vpn]),
        "Legacy Windows hosts in OT network": ("obsolescence", "confirmed", [sa_scada]),
        "Weak password policy on historian database": ("weak_authentication", "confirmed", [sa_historian]),
        "Flat network between IT and OT": ("network_exposure", "confirmed", [sa_wan, sa_scada]),
        "Missing MFA on contractor accounts": ("weak_authentication", "mitigated", [sa_vpn]),
        "Outdated TLS configuration on customer portal": ("configuration_weakness", "confirmed", [sa_portal]),
        "Log4j in vendor monitoring appliance": ("third_party_dependency", "mitigated", [sa_metering]),
        "No offline backup for SCADA configuration": ("insufficient_backup", "identified", [sa_scada, sa_plc]),
    }
    for name, severity, cve, desc in TBL["VULNERABILITIES"]:
        category, status_value, affected = VULN_META[name]
        v = Vulnerability.objects.create(
            name=name, description=desc, category=category, severity=severity,
            cve_references=[cve] if cve else [],
            affected_asset_types=["server", "network_equipment"],
            remediation_guidance="Apply the vendor fix or the documented compensating control.",
            status=status_value, created_by=julien,
            is_approved=True, approved_by=elise, approved_at=NOW,
        )
        v.scopes.set([scope_group])
        v.affected_assets.set(affected)
        vuln_objs[name] = v

    print("Risk assessment and risks...")
    enterprise_assessment_date = months_ago(4)
    assessment = RiskAssessment.objects.create(
        name=f"{enterprise_assessment_date.year} Enterprise risk assessment",
        description="Annual ISO 27005 assessment of the group scope, feeding the treatment plan portfolio.",
        methodology="iso27005", assessment_date=enterprise_assessment_date,
        assessor=julien, risk_criteria=criteria, status="in_progress",
        next_review_date=days_ahead(3), created_by=julien,
    )
    assessment.scopes.set([scope_group])

    def mk_risk(name, desc, il, ii, cl, ci, rl, ri, decision, priority, status_value,
                owner, c=False, i=False, a=False, source="manual"):
        return Risk.objects.create(
            assessment=assessment, name=name, description=desc, risk_source=source,
            impact_confidentiality=c, impact_integrity=i, impact_availability=a,
            initial_likelihood=il, initial_impact=ii,
            current_likelihood=cl, current_impact=ci,
            residual_likelihood=rl, residual_impact=ri,
            treatment_decision=decision, risk_owner=owner, priority=priority,
            status=status_value, created_by=julien,
        )

    r_ransomware = mk_risk(
        "Ransomware encrypting corporate IT and propagating to OT",
        "A ransomware intrusion through phishing or the VPN spreads from office IT towards the supervision network.",
        4, 5, 4, 5, 2, 3, "mitigate", "critical", "treatment_in_progress", elise,
        c=True, i=True, a=True, source="iso27005_analysis",
    )
    r_scada = mk_risk(
        "Manipulation of SCADA setpoints via the flat IT/OT network",
        "An attacker reaching the OT segment alters production setpoints, forcing curtailment or equipment stress.",
        3, 5, 3, 5, 2, 4, "mitigate", "critical", "treatment_planned", thomas,
        i=True, a=True,
    )
    r_breach = mk_risk(
        "Customer personal data breach through the portal",
        "Exploitation of the customer portal exposes identity and consumption data of 240k customers.",
        4, 4, 3, 4, 2, 3, "mitigate", "high", "treatment_in_progress", amelia,
        c=True, source="iso27005_analysis",
    )
    r_phishing = mk_risk(
        "Credential theft through phishing campaigns",
        "Harvested credentials reused against the VPN and collaboration suite.",
        5, 3, 4, 3, 3, 2, "mitigate", "high", "treated", marc, c=True,
    )
    r_vpn = mk_risk(
        "Exploitation of the perimeter VPN gateway",
        "Remote code execution on the unpatched VPN appliance gives a foothold on the internal network.",
        4, 4, 3, 4, 2, 2, "mitigate", "high", "monitoring", marc, c=True, i=True,
    )
    r_mssp = mk_risk(
        "Compromise of the managed SOC provider",
        "A breach at the MSSP exposes detection blind spots and privileged tooling.",
        3, 4, 3, 4, 2, 3, "transfer", "medium", "evaluated", elise, c=True,
    )
    r_ddos = mk_risk(
        "Denial of service against the customer portal",
        "Volumetric attack makes self-service and invoicing unavailable.",
        3, 3, 2, 3, 2, 2, "mitigate", "medium", "treated", ines, a=True,
    )
    r_insider = mk_risk(
        "Insider exfiltration of trading positions",
        "An employee leaks forward positions to a competitor or broker.",
        2, 4, 2, 4, 2, 3, "mitigate", "medium", "analyzed", david, c=True,
    )
    r_power = mk_risk(
        "Extended power failure at the Roubaix datacenter",
        "Outage exceeding generator autonomy interrupts ERP and historian replication.",
        2, 4, 2, 4, 1, 3, "accept", "medium", "accepted", marc, a=True,
    )
    r_historian = mk_risk(
        "Failure of the single-instance plant historian",
        "Hardware or software failure loses telemetry needed for safe restart and forecasting.",
        3, 4, 3, 4, 2, 3, "mitigate", "high", "treatment_planned", thomas, a=True, i=True,
    )
    r_flood = mk_risk(
        "Flooding of the hydro station control room",
        "Seasonal flooding damages local control equipment.",
        1, 4, 1, 4, 1, 3, "accept", "low", "accepted", thomas, a=True,
    )
    r_keyperson = mk_risk(
        "Departure of key OT engineers",
        "Undocumented operational knowledge leaves with senior plant engineers.",
        3, 3, 3, 3, 2, 2, "mitigate", "medium", "evaluated", thomas, a=True,
    )
    Risk.objects.create(
        assessment=assessment, name="Quantum computing threat to current cryptography",
        description="Long-term exposure of archived encrypted data to future decryption.",
        risk_source="manual", initial_likelihood=1, initial_impact=3,
        treatment_decision="not_decided", risk_owner=elise, priority="low",
        status="identified", created_by=julien,
    )

    r_ransomware.affected_essential_assets.set([ea_billing, ea_custdata, ea_control])
    r_ransomware.affected_support_assets.set([sa_erp, sa_laptops, sa_scada])
    r_ransomware.linked_requirements.set([iso_reqs["A.8.13"], iso_reqs["A.8.7"]])
    r_scada.affected_essential_assets.set([ea_control, ea_telemetry])
    r_scada.affected_support_assets.set([sa_scada, sa_plc])
    r_scada.linked_requirements.set([iso_reqs["A.8.22"], vsb_reqs["VSB-2.3"]])
    r_breach.affected_essential_assets.set([ea_custdata])
    r_breach.affected_support_assets.set([sa_portal])
    r_breach.linked_requirements.set([gdpr_reqs["GDPR-32"], gdpr_reqs["GDPR-33"]])
    r_phishing.affected_support_assets.set([sa_collab, sa_vpn])
    r_vpn.affected_support_assets.set([sa_vpn])
    r_mssp.affected_support_assets.set([sa_siem])
    r_ddos.affected_essential_assets.set([ea_billing])
    r_ddos.affected_support_assets.set([sa_portal])
    r_insider.affected_essential_assets.set([ea_trading])
    r_power.affected_support_assets.set([sa_erp, sa_historian])
    r_historian.affected_essential_assets.set([ea_telemetry, ea_forecast])
    r_historian.affected_support_assets.set([sa_historian])
    r_flood.affected_support_assets.set([sa_metering])
    r_ransomware.review_date = days_ahead(2)
    r_ransomware.save()

    for threat_name, vuln_name, tl, ve, ic, ii, ia, controls, risk_link in [
        ("Ransomware attack", "Unpatched VPN gateway firmware", 4, 4, 4, 5, 5,
         "EDR on workstations, daily backups, e-mail filtering.", r_ransomware),
        ("Phishing and credential theft", "Missing MFA on contractor accounts", 4, 3, 4, 3, 3,
         "Awareness programme, phishing simulations, conditional access.", r_phishing),
        ("Sabotage of industrial control systems", "Flat network between IT and OT", 3, 4, 2, 5, 5,
         "Jump host for OT access, vendor VPN profiles.", r_scada),
        ("Compromise of remote access", "Weak password policy on historian database", 3, 3, 3, 4, 4,
         "VPN MFA for employees, network monitoring.", r_historian),
        ("Denial of service on customer portal", "Outdated TLS configuration on customer portal", 2, 3, 1, 2, 4,
         "CDN with rate limiting in front of the portal.", r_ddos),
        ("Flooding of hydro control room", "No offline backup for SCADA configuration", 2, 2, 1, 3, 4,
         "Flood barriers, raised equipment racks.", r_flood),
    ]:
        analysis = ISO27005Risk.objects.create(
            assessment=assessment, threat=threat_objs[threat_name],
            vulnerability=vuln_objs[vuln_name],
            threat_likelihood=tl, vulnerability_exposure=ve,
            impact_confidentiality=ic, impact_integrity=ii, impact_availability=ia,
            existing_controls=controls, risk=risk_link,
            created_by=julien, is_approved=True, approved_by=elise, approved_at=NOW,
        )
        analysis.affected_support_assets.set(list(risk_link.affected_support_assets.all()))

    print("Treatment plans and acceptances...")
    tp_segmentation = RiskTreatmentPlan.objects.create(
        risk=r_scada, name="IT/OT segmentation programme",
        description="Zone and conduit architecture per IEC 62443, with firewalls between office IT and plant networks.",
        treatment_type="mitigate", expected_residual_likelihood=2, expected_residual_impact=4,
        cost_estimate=Decimal("180000.00"), owner=thomas,
        start_date=days_ago(147), target_date=days_ahead(155),
        progress_percentage=45, status="in_progress", created_by=thomas,
    )
    for order, (desc, status_value, target) in enumerate([
        ("Design the zone and conduit model for all plants", "completed", days_ago(89)),
        ("Deploy segmentation firewalls at the wind farm", "in_progress", days_ahead(64)),
        ("Validate conduits and update network documentation", "planned", days_ahead(140)),
    ], 1):
        TreatmentAction.objects.create(
            treatment_plan=tp_segmentation, description=desc, owner=thomas,
            target_date=target, status=status_value, order=order,
            completion_date=days_ago(92) if status_value == "completed" else None,
        )
    tp_segmentation.related_action_plans.set([ap_siem_ot])

    tp_backup = RiskTreatmentPlan.objects.create(
        risk=r_ransomware, name="Backup hardening and immutable vault",
        description="Immutable copies for critical systems with quarterly restoration tests.",
        treatment_type="mitigate", expected_residual_likelihood=2, expected_residual_impact=3,
        cost_estimate=Decimal("60000.00"), owner=marc,
        start_date=days_ago(104), target_date=days_ahead(12),
        progress_percentage=70, status="in_progress", created_by=marc,
    )
    for order, (desc, status_value) in enumerate([
        ("Deploy the immutable vault appliance", "completed"),
        ("Onboard ERP and historian backup jobs", "in_progress"),
    ], 1):
        TreatmentAction.objects.create(
            treatment_plan=tp_backup, description=desc, owner=marc,
            status=status_value, order=order,
            completion_date=days_ago(40) if status_value == "completed" else None,
        )
    tp_backup.related_action_plans.set([ap_historian_enc])

    RiskTreatmentPlan.objects.create(
        risk=r_breach, name="Customer portal hardening",
        description="TLS uplift, dependency patching and a third-party penetration test.",
        treatment_type="mitigate", expected_residual_likelihood=2, expected_residual_impact=3,
        cost_estimate=Decimal("35000.00"), owner=ines,
        start_date=days_ago(118), target_date=days_ago(28),
        progress_percentage=80, status="overdue", created_by=ines,
    )
    RiskTreatmentPlan.objects.create(
        risk=r_phishing, name="Phishing-resistant MFA rollout",
        description="FIDO2 keys for privileged and finance users.",
        treatment_type="mitigate", expected_residual_likelihood=3, expected_residual_impact=2,
        cost_estimate=Decimal("28000.00"), owner=marc,
        start_date=days_ago(174), target_date=days_ago(59),
        completion_date=days_ago(61), progress_percentage=100,
        status="completed", created_by=marc,
    )
    RiskTreatmentPlan.objects.create(
        risk=r_mssp, name="MSSP contract security uplift",
        description="Extend the SOC 2 scope to OT monitoring and add breach notification clauses.",
        treatment_type="transfer", owner=elise,
        start_date=days_ahead(3), target_date=days_ahead(79),
        status="planned", created_by=elise,
    )

    RiskAcceptance.objects.create(
        risk=r_power, accepted_by=elise,
        justification="Generator autonomy covers 48 hours and a second feed is contracted for next year; further mitigation is disproportionate this year.",
        conditions="Quarterly generator tests; review on datacenter contract renewal.",
        valid_until=days_ahead(4), review_date=TODAY,
        status="active", created_by=marc,
    )
    RiskAcceptance.objects.create(
        risk=r_flood, accepted_by=elise,
        justification="Flood barriers installed last year reduce exposure; residual level within appetite.",
        conditions="Re-assess after any flood alert on the Romanche valley.",
        valid_until=days_ahead(276), review_date=days_ahead(170),
        status="active", created_by=thomas,
    )
    RiskAcceptance.objects.create(
        risk=r_historian, accepted_by=elise, accepted_at=NOW - timedelta(days=400),
        risk_level_at_acceptance=4,
        justification="Temporary acceptance pending the historian redundancy budget.",
        valid_until=days_ago(59), status="expired", created_by=thomas,
    )

    # ------------------------------------------------------------------- EBIOS
    print("EBIOS RM study...")
    ebios_assessment_date = days_ago(82)
    ebios = RiskAssessment.objects.create(
        name="EBIOS RM : SCADA & industrial operations",
        description="Strategic cycle covering the production fleet, workshops 0 to 3.",
        methodology="ebios_rm", assessment_date=ebios_assessment_date,
        assessor=julien, risk_criteria=criteria, status="in_progress",
        created_by=julien,
    )
    ebios.scopes.set([scope_ot])

    sf = ebios.ebios_study_framework
    sf.mission_statement = "Assess and treat cyber risks threatening the safe operation of the production fleet."
    sf.business_perimeter = "Electricity generation and plant maintenance activities."
    sf.technical_perimeter = "SCADA supervision, turbine PLCs, plant historian, vendor remote access."
    sf.temporal_perimeter = f"Strategic cycle {ebios_assessment_date.year}-{ebios_assessment_date.year + 1}."
    sf.assumptions = "No major SCADA upgrade during the study."
    sf.constraints = "Workshops must not interfere with plant operations."
    sf.expected_deliverables = f"Risk mapping, strategic scenarios, PACS input for the {ebios_assessment_date.year + 1} budget."
    sf.participants_external = [
        {"name": "C. Renard", "role": "EBIOS RM facilitator", "organization": "Astreinte Conseil"},
    ]
    sf.status = "validated"
    sf.save()
    sf.participants.set([elise, thomas, julien])
    sf.applicable_frameworks.set([fw_iso, fw_nis2])

    for n in range(3):
        w = ebios.ebios_workshops.get(workshop_number=n, iteration_type="strategic", iteration_number=1)
        w.status = "validated"
        w.started_at = NOW - timedelta(days=60 - 15 * n)
        w.validated_by = elise
        w.validated_at = NOW - timedelta(days=50 - 15 * n)
        w.deliverables_summary = f"Workshop {n} deliverables reviewed and approved."
        w.save()
    w3 = ebios.ebios_workshops.get(workshop_number=3, iteration_type="strategic", iteration_number=1)
    w3.status = "in_progress"
    w3.started_at = NOW - timedelta(days=10)
    w3.save()

    sb = ebios.ebios_security_baseline
    sb.dic_summary = "Integrity and availability of production control rated 4/4; telemetry integrity rated 4."
    sb.status = "in_progress"
    sb.save()
    sb.business_values.set([act_generation, act_maintenance])
    sb.essential_assets.set([ea_control, ea_telemetry])
    sb.support_assets.set([sa_scada, sa_plc, sa_historian])
    sb.baseline_references.set([fw_iso, fw_vsb])

    fe_avail = FearedEvent.objects.create(
        baseline=sb, essential_asset=ea_control, dic_criterion="availability",
        name="Loss of production supervision",
        description="Operators lose visibility and control over the production fleet.",
        gravity_level=4, gravity_justification="Forced curtailment and safety exposure within minutes.",
        business_impacts={"operational": "Production halt", "financial": "Imbalance penalties"},
        order=1, **approved(elise),
    )
    fe_integrity = FearedEvent.objects.create(
        baseline=sb, essential_asset=ea_telemetry, dic_criterion="integrity",
        name="Tampering of SCADA telemetry",
        description="Falsified measurements hide unsafe operating conditions.",
        gravity_level=4, gravity_justification="Potential equipment damage and safety impact.",
        business_impacts={"human": "Safety hazard", "operational": "Wrong dispatch decisions"},
        order=2, **approved(elise),
    )
    fe_hist = FearedEvent.objects.create(
        baseline=sb, essential_asset=ea_telemetry, dic_criterion="availability",
        name="Unavailability of the telemetry historian",
        gravity_level=3, order=3, **approved(elise),
    )
    BaselineGap.objects.create(
        baseline=sb, reference_source="ISO 27002:2022 : 8.22 Segregation of networks",
        linked_requirement=iso_reqs["A.8.22"],
        description="No strict segregation between office IT and industrial control segments.",
        severity="critical", recommended_remediation="Implement the IEC 62443 zone and conduit model.",
        status="in_remediation", order=1, created_by=julien,
    ).affected_support_assets.set([sa_scada, sa_plc])
    BaselineGap.objects.create(
        baseline=sb, reference_source="IEC 62443-2-1 : asset inventory",
        description="No maintained inventory of PLC firmware versions across plants.",
        severity="medium", recommended_remediation="Automate firmware inventory collection during maintenance windows.",
        status="identified", order=2, created_by=julien,
    )

    rs_crime = RiskSource.objects.create(
        assessment=ebios, name="Organised cybercrime (ransomware operators)",
        description="Financially motivated groups targeting European utilities.",
        category="organized_crime", motivation_level=4, resources_level=3, activity_level=3,
        motivation_description="High ransom profitability in the energy sector.",
        is_retained=True, retention_justification="Most active threat on the sector per CERT reporting.",
        **approved(elise),
    )
    rs_state = RiskSource.objects.create(
        assessment=ebios, name="State-sponsored actor",
        description="Pre-positioning on energy infrastructure for geopolitical leverage.",
        category="state", motivation_level=3, resources_level=4, activity_level=2,
        is_retained=True, retention_justification="Documented campaigns against grid operators.",
        **approved(elise),
    )
    rs_hacktivist = RiskSource.objects.create(
        assessment=ebios, name="Hacktivist collective",
        category="activist", motivation_level=3, resources_level=2, activity_level=2,
        is_retained=True, **approved(elise),
    )
    RiskSource.objects.create(
        assessment=ebios, name="Isolated amateur",
        category="amateur", motivation_level=2, resources_level=1,
        is_retained=False, retention_justification="Capability too low against the OT perimeter.",
        **approved(elise),
    )

    ov_extortion = TargetedObjective.objects.create(
        risk_source=rs_crime, name="Extortion through production shutdown",
        description="Encrypt or disrupt supervision to force ransom payment.",
        category="lucrative", order=1, **approved(elise),
    )
    ov_extortion.targeted_essential_assets.set([ea_control])
    ov_extortion.targeted_feared_events.set([fe_avail])
    ov_preposition = TargetedObjective.objects.create(
        risk_source=rs_state, name="Pre-positioning for grid disruption",
        description="Silent persistent access to industrial control systems.",
        category="strategic", order=2, **approved(elise),
    )
    ov_preposition.targeted_essential_assets.set([ea_control, ea_telemetry])
    ov_preposition.targeted_feared_events.set([fe_integrity])
    ov_visibility = TargetedObjective.objects.create(
        risk_source=rs_hacktivist, name="Media-visible disruption",
        category="ideological", order=3, **approved(elise),
    )
    ov_visibility.targeted_feared_events.set([fe_hist])

    pair_crime = RiskSourceObjectivePair.objects.create(
        assessment=ebios, risk_source=rs_crime, targeted_objective=ov_extortion,
        relevance="critical", relevance_justification="Matches current ransomware tradecraft on utilities.",
        is_retained=True, retention_justification="Retained for workshop 3.", **approved(elise),
    )
    pair_state = RiskSourceObjectivePair.objects.create(
        assessment=ebios, risk_source=rs_state, targeted_objective=ov_preposition,
        relevance="high", is_retained=True, retention_justification="Retained for workshop 3.",
        **approved(elise),
    )
    RiskSourceObjectivePair.objects.create(
        assessment=ebios, risk_source=rs_hacktivist, targeted_objective=ov_visibility,
        relevance="medium", is_retained=False,
        retention_justification="Monitored; capability judged insufficient this cycle.",
        **approved(elise),
    )

    eco_vendor = EcosystemStakeholder.objects.create(
        assessment=ebios, name="TurbinTech remote maintenance",
        description="Permanent vendor access for turbine diagnostics and firmware updates.",
        category="subcontractor", supplier=sup_turbintech,
        dependency=4, penetration=4, maturity=2, trust=2,
        is_attack_vector=True,
        attack_vector_justification="Privileged standing access to PLCs from outside the perimeter.",
        **approved(elise),
    )
    eco_vendor.accessible_support_assets.set([sa_plc, sa_scada])
    eco_soc = EcosystemStakeholder.objects.create(
        assessment=ebios, name="SentinelWatch managed SOC",
        category="subcontractor", supplier=sup_sentinel,
        dependency=3, penetration=3, maturity=3, trust=3,
        **approved(elise),
    )
    eco_soc.accessible_support_assets.set([sa_siem])
    eco_grid = EcosystemStakeholder.objects.create(
        assessment=ebios, name="National grid operator interconnection",
        category="shared_infrastructure", stakeholder=sh_grid,
        dependency=4, penetration=2, maturity=3, trust=3,
        **approved(elise),
    )
    EcosystemStakeholder.objects.create(
        assessment=ebios, name="Facility services provider",
        category="other", supplier=sup_facil,
        dependency=1, penetration=2, maturity=2, trust=3,
        **approved(elise),
    )

    sts_ransom = StrategicScenario.objects.create(
        assessment=ebios, name="Ransomware on OT via the turbine vendor",
        description="Compromise of TurbinTech, pivot through the maintenance access, encryption of supervision and historian.",
        sr_ov_pair=pair_crime, gravity_level=4,
        gravity_justification="Loss of supervision across the wind fleet.",
        likelihood_level=3, likelihood_justification="Ecosystem stakeholder sits in the danger zone.",
        existing_security_measures="Vendor VPN profile, jump host, daily backups.",
        is_retained=True, **approved(elise),
    )
    sts_ransom.targeted_feared_events.set([fe_avail, fe_hist])
    for order, (desc, action, difficulty) in enumerate([
        ("Spear-phishing of TurbinTech maintenance engineers", "initial_access", "moderate"),
        ("Pivot through the vendor maintenance VPN to the plant network", "lateral_movement", "difficult"),
        ("Deployment of ransomware on supervision servers and historian", "disruption", "moderate"),
    ], 1):
        AttackPathStep.objects.create(
            scenario=sts_ransom, order=order, stakeholder=eco_vendor,
            description=desc, action_type=action, difficulty=difficulty,
            **approved(elise),
        )
    sts_state = StrategicScenario.objects.create(
        assessment=ebios, name="Pre-positioning through the grid interconnection",
        description="Long-term implant on dispatch-facing systems via the TSO data exchange.",
        sr_ov_pair=pair_state, gravity_level=4, likelihood_level=2,
        likelihood_justification="High capability actor, hardened interconnection.",
        is_retained=True, **approved(elise),
    )
    sts_state.targeted_feared_events.set([fe_integrity])
    for order, (desc, action, difficulty) in enumerate([
        ("Compromise of the data exchange gateway with the TSO", "initial_access", "very_difficult"),
        ("Stealth persistence and telemetry manipulation capability", "persistence", "difficult"),
    ], 1):
        AttackPathStep.objects.create(
            scenario=sts_state, order=order, stakeholder=eco_grid,
            description=desc, action_type=action, difficulty=difficulty,
            **approved(elise),
        )

    # ------------------------------------------------------- management review
    print("Management reviews...")
    mr_closed_period_start = days_ago(362)
    mr_closed = ManagementReview.objects.create(
        title=f"{semester_label(mr_closed_period_start)} management review",
        description="Semi-annual ISO 27001 clause 9.3 review of the ISMS.",
        frequency="semiannual", period_start=mr_closed_period_start, period_end=days_ago(179),
        planned_date=days_ago(159), held_date=days_ago(159),
        location="Lyon HQ, board room", facilitator=elise, approver=david,
        next_review_date=days_ahead(12),
        summary="The ISMS is effective overall; OT monitoring and NIS2 readiness require investment.",
        agenda="Audit results; risk register evolution; objectives; resources.",
        minutes="The committee reviewed the audit programme, the risk register and approved two structuring decisions.",
        status="closed", created_by=elise,
    )
    mr_closed.scopes.set([scope_group])
    for user, role, attended in [
        (elise, "facilitator", True), (david, "decision_maker", True),
        (amelia, "contributor", True), (thomas, "contributor", True),
        (sofia, "observer", False),
    ]:
        ManagementReviewParticipant.objects.create(
            review=mr_closed, user=user, role=role, attended=attended,
        )
    ManagementReviewDecision.objects.create(
        review=mr_closed, category="resource_allocation", input_clause="f",
        title="Extend SOC monitoring to the OT perimeter",
        description="Allocate budget to deploy OT probes and onboard plant log sources to the managed SOC.",
        rationale="Detection coverage gap confirmed by the risk assessment and the internal audit.",
        owner=thomas, due_date=days_ahead(124), priority="high",
        status="in_progress", linked_action_plan=ap_siem_ot,
    )
    ManagementReviewDecision.objects.create(
        review=mr_closed, category="improvement", input_clause="g",
        title="Renew cyber insurance with extended OT coverage",
        description="Negotiate the renewed policy to cover production interruption from cyber events.",
        owner=david, due_date=days_ago(89), priority="medium",
        status="implemented", implemented_at=days_ago(105),
        implementation_evidence="Policy CY-2026-114 signed with OT business interruption rider.",
    )
    mr_next_period_start = days_ago(178)
    mr_next = ManagementReview.objects.create(
        title=f"{semester_label(mr_next_period_start)} management review",
        frequency="semiannual", period_start=mr_next_period_start, period_end=days_ago(2),
        planned_date=days_ahead(12), facilitator=elise, approver=david,
        agenda="Internal audit results; certification readiness; NIS2 programme; KPI review.",
        status="planned", created_by=elise,
    )
    mr_next.scopes.set([scope_group])

    # --------------------------------------------------------------- indicators
    print("Indicators and measurements...")
    month_offsets = [330, 300, 270, 240, 210, 180, 150, 120, 90, 60, 30, 0]

    def seed_indicator(name, desc, unit, series_key, operator, threshold, ind_type="technical",
                       owner=None, objectives=None, fmt="number"):
        kwargs = dict(
            name=name, description=desc, indicator_type=ind_type,
            collection_method="manual", format=fmt, unit=unit,
            review_frequency="monthly", first_review_date=TODAY + timedelta(days=19),
            status="active", owner=owner or elise, **approved(elise),
        )
        if operator == "above":
            kwargs.update(critical_threshold_operator="above",
                          critical_threshold_value=str(threshold),
                          critical_threshold_max=float(threshold))
        else:
            kwargs.update(critical_threshold_operator="below",
                          critical_threshold_value=str(threshold),
                          critical_threshold_min=float(threshold))
        ind = Indicator.objects.create(**kwargs)
        ind.scopes.set([scope_group])
        if objectives:
            ind.linked_objectives.set(objectives)
        series = TBL["INDICATOR_SERIES"][series_key]
        for offset, value in zip(month_offsets[:-1], series[:-1]):
            IndicatorMeasurement.objects.create(
                indicator=ind, value=str(value),
                recorded_at=NOW - timedelta(days=offset), recorded_by=elise,
            )
        ind.record_measurement(str(series[-1]), recorded_by=elise)
        return ind

    ind_phishing = seed_indicator(
        "Phishing click rate", "Click rate observed during monthly phishing simulations.",
        "%", "phishing_click_rate", "above", 10, ind_type="organizational",
        objectives=[obj_phishing],
    )
    ind_mfa = seed_indicator(
        "MFA coverage on privileged accounts", "Share of privileged accounts enrolled in MFA.",
        "%", "mfa_coverage", "below", 90, objectives=[obj_mfa],
    )
    ind_patch = seed_indicator(
        "Critical patch latency", "Median days between critical patch release and deployment.",
        "days", "patch_latency_days", "above", 30,
    )
    ind_incidents = seed_indicator(
        "Security incidents per month", "Confirmed incidents handled by the SOC.",
        "incidents", "incidents_per_month", "above", 6, ind_type="organizational",
    )
    ind_backup = seed_indicator(
        "Backup success rate", "Share of backup jobs completed successfully over the month.",
        "%", "backup_success_rate", "below", 95,
    )
    ind_mttr = seed_indicator(
        "SOC mean time to respond", "Average hours from alert to containment.",
        "hours", "soc_mttr_hours", "above", 24,
    )

    predefined = []
    for name, source, parameter in [
        ("Global compliance rate", "global_compliance_rate", ""),
        ("Risk treatment rate", "risk_treatment_rate", ""),
        ("Objective progress", "objective_progress", ""),
        ("Mandatory roles coverage", "mandatory_roles_coverage", ""),
    ]:
        ind = Indicator.objects.create(
            name=name, indicator_type="organizational", collection_method="internal",
            format="number", unit="%", is_internal=True, internal_source=source,
            internal_source_parameter=parameter, review_frequency="monthly",
            first_review_date=TODAY + timedelta(days=19), status="active", owner=elise,
            **approved(elise),
        )
        ind.scopes.set([scope_group])
        value = float(ind.compute_internal_value())
        for offset, delta in [(120, -9), (90, -6), (60, -4), (30, -2)]:
            IndicatorMeasurement.objects.create(
                indicator=ind, value=str(round(max(0.0, value + delta), 1)),
                recorded_at=NOW - timedelta(days=offset), recorded_by=elise,
            )
        ind.record_measurement(str(round(value, 1)), recorded_by=elise)
        predefined.append(ind)

    elise.dashboard_indicators = [str(i.pk) for i in predefined + [
        ind_phishing, ind_mfa, ind_patch, ind_incidents, ind_backup, ind_mttr]]
    elise.dashboard_indicator_charts = [str(i.pk) for i in [
        ind_phishing, ind_mfa, ind_patch, ind_backup, ind_mttr]]

    # Curated default dashboard (captured from the demo dashboard): overall
    # compliance, a row of KPI indicator tiles, the analytics widgets, and the
    # Ask Cairn briefing in the rail. The indicator widgets are bound to the
    # seeded indicators (the exact set / order is just an example) so the layout
    # is valid on a fresh seed.
    _dash_indicators = (predefined + [
        ind_phishing, ind_mfa, ind_patch, ind_incidents, ind_backup, ind_mttr])[:8]
    _indicator_widgets = [
        {"key": f"indicator-{ind.pk}", "id": "indicator", "size": "1x1", "zone": "main",
         "visible": True, "params": {"indicator": str(ind.pk), "show_chart": True}}
        for ind in _dash_indicators
    ]
    elise.dashboard_layout = [
        {"key": "overall_compliance", "id": "overall_compliance", "size": "4x1", "zone": "main", "visible": True, "params": {"show_target": True, "target": 90}},
        *_indicator_widgets,
        {"key": "ongoing_audits", "id": "ongoing_audits", "size": "1x2", "zone": "main", "visible": False, "params": {}},
        {"key": "active_objectives", "id": "active_objectives", "size": "2x3", "zone": "main", "visible": True, "params": {"sort": "default", "order": []}},
        {"key": "compliance_by_framework", "id": "compliance_by_framework", "size": "2x3", "zone": "main", "visible": True, "params": {"sort": "default", "order": []}},
        {"key": "risk_treatment_flow", "id": "risk_treatment_flow", "size": "4x3", "zone": "main", "visible": True, "params": {}},
        {"key": "risk_matrix_current", "id": "risk_matrix_current", "size": "2x3", "zone": "main", "visible": True, "params": {}},
        {"key": "risk_matrix_residual", "id": "risk_matrix_residual", "size": "2x3", "zone": "main", "visible": True, "params": {}},
        {"key": "upcoming_deadlines", "id": "upcoming_deadlines", "size": "1x2", "zone": "rail_top", "visible": False, "params": {}},
        {"key": "priority_risks", "id": "priority_risks", "size": "1x2", "zone": "rail_top", "visible": False, "params": {}},
        {"key": "ask_cairn", "id": "ask_cairn", "size": "2x2", "zone": "rail_top", "visible": True, "params": {}},
    ]
    elise.save()

    # ============================================================ bulk volume
    # Generate 50+ items per category (where it makes sense) on top of the
    # curated narrative, wiring foreign keys to the objects created above so the
    # whole app is populated with realistic, varied data.
    print("Bulk volume (50+ per category)...")
    import unicodedata

    def _email(first, last, i):
        base = f"{first}.{last}".lower().replace(" ", "").replace("'", "")
        base = unicodedata.normalize("NFKD", base).encode("ascii", "ignore").decode()
        base = "".join(ch for ch in base if ch.isalnum() or ch == ".")
        return f"{base or 'user'}.{i}@voltara.example"

    scope_pool = [scope_group, scope_it, scope_ot, scope_cust, scope_rnd]

    # --- users -----------------------------------------------------------
    grp_contrib = Group.objects.get(name="Contributeur")
    grp_aud = Group.objects.get(name="Auditeur")
    grp_read = Group.objects.get(name="Lecteur") if Group.objects.filter(name="Lecteur").exists() else grp_contrib
    bulk_users = []
    for i, u in enumerate(BULK["users"]):
        usr = mk_user(_email(u["first"], u["last"], i), u["first"], u["last"],
                      u["job_title"], u["department"])
        bulk_users.append(usr)
        dept = (u.get("department") or "").lower()
        if "audit" in dept:
            grp_aud.users.add(usr)
        elif any(k in dept for k in ("security", "legal", "it", "ot", "compliance", "privacy")):
            grp_contrib.users.add(usr)
        else:
            grp_read.users.add(usr)
    all_users = [elise, david, marc, amelia, thomas, ines, julien, sofia] + bulk_users

    def pick_user():
        return RNG.choice(all_users)

    # --- roles -----------------------------------------------------------
    seen_roles = set(Role.objects.values_list("name", flat=True))
    for r in BULK["roles"]:
        if r["name"] in seen_roles:
            continue
        seen_roles.add(r["name"])
        role = Role.objects.create(
            name=r["name"],
            type="governance" if r.get("governance") else RNG.choice(["operational", "support", "control"]),
            status="active", **approved(elise),
        )
        role.scopes.set([RNG.choice(scope_pool)])
        role.assigned_users.set(RNG.sample(all_users, k=RNG.randint(1, 3)))

    # --- issues ----------------------------------------------------------
    ISSUE_INT_CATS = ["strategic", "organizational", "human_resources", "technical", "financial", "cultural"]
    ISSUE_EXT_CATS = ["political", "economic", "social", "technological", "legal", "environmental", "competitive", "regulatory"]
    IMPACTS = ["low", "medium", "high", "critical"]
    for it in BULK["issues"]:
        internal = it.get("internal")
        iss = Issue.objects.create(
            name=it["name"], type="internal" if internal else "external",
            category=RNG.choice(ISSUE_INT_CATS if internal else ISSUE_EXT_CATS), description=it.get("description", ""),
            impact_level=RNG.choice(IMPACTS), trend=RNG.choice(["improving", "stable", "degrading"]),
            status=RNG.choice(["identified", "active", "monitored", "closed"]), **approved(elise),
        )
        iss.scopes.set([RNG.choice(scope_pool)])

    # --- stakeholders ----------------------------------------------------
    SH_INT = ["executive_management", "employees", "auditors", "shareholders"]
    SH_EXT = ["customers", "suppliers", "partners", "regulators", "insurers", "public", "competitors", "unions", "other"]
    INF = ["low", "medium", "high"]
    for s in BULK["stakeholders"]:
        internal = s.get("internal")
        sh = Stakeholder.objects.create(
            name=s["name"], type="internal" if internal else "external",
            category=RNG.choice(SH_INT if internal else SH_EXT), description=s.get("description", ""),
            influence_level=RNG.choice(INF), interest_level=RNG.choice(INF),
            status="active", **approved(elise),
        )
        sh.scopes.set([RNG.choice(scope_pool)])

    # --- objectives ------------------------------------------------------
    OBJ_CATS = ["confidentiality", "integrity", "availability", "compliance", "operational", "strategic"]
    OBJ_TYPES = ["security", "compliance", "business", "other"]
    OBJ_FREQ = ["monthly", "quarterly", "semi_annual", "annual"]
    OBJ_STATUS = ["draft", "active", "active", "achieved", "not_achieved"]
    for o in BULK["objectives"]:
        o_status = RNG.choice(OBJ_STATUS)
        prog = 100 if o_status == "achieved" else RNG.randint(5, 95)
        obj = Objective.objects.create(
            name=o["name"], category=RNG.choice(OBJ_CATS), type=RNG.choice(OBJ_TYPES),
            description=o.get("description", ""), owner=pick_user(), status=o_status,
            target_value="100", current_value=str(prog), unit=(o.get("unit") or "%")[:20],
            measurement_frequency=RNG.choice(OBJ_FREQ), progress_percentage=prog,
            target_date=TODAY + timedelta(days=RNG.randint(30, 420)), **approved(elise),
        )
        obj.scopes.set([RNG.choice(scope_pool)])

    # --- activities ------------------------------------------------------
    for a in BULK["activities"]:
        act = Activity.objects.create(
            name=a["name"], type=RNG.choice(["core_business", "support", "management"]),
            criticality=RNG.choice(["low", "medium", "high", "critical"]),
            description=a.get("description", ""), owner=pick_user(), status="active", **approved(elise),
        )
        act.scopes.set([RNG.choice(scope_pool)])

    # --- essential assets ------------------------------------------------
    EA_INFO_CATS = ["strategic_data", "operational_data", "personal_data", "financial_data",
                    "technical_data", "legal_data", "research_data", "commercial_data"]
    EA_PROC_CATS = ["core_process", "support_process", "management_process"]
    bulk_essential = []
    for e in BULK["essential_assets"]:
        info = e.get("information")
        pd = bool(e.get("personal_data"))
        ea = EssentialAsset.objects.create(
            name=e["name"], type="information" if info else "business_process",
            category=RNG.choice(EA_INFO_CATS if info else EA_PROC_CATS),
            description=e.get("description", ""), owner=pick_user(),
            confidentiality_level=RNG.randint(1, 4), integrity_level=RNG.randint(1, 4),
            availability_level=RNG.randint(1, 4),
            data_classification=RNG.choice(["internal", "confidential", "restricted"]),
            personal_data=pd, personal_data_categories=(["identity", "contact"] if pd else []),
            status="active", **approved(elise),
        )
        ea.scopes.set([RNG.choice(scope_pool)])
        if pd:
            ea.tags.add(tag_gdpr)
        bulk_essential.append(ea)

    # --- support assets --------------------------------------------------
    KIND_CATS = {
        "hardware": ["server", "workstation", "laptop", "network_equipment", "storage", "iot_device"],
        "software": ["operating_system", "database", "application", "middleware", "security_tool", "saas_application"],
        "network": ["lan", "wan", "vpn", "firewall_zone", "dmz", "internet_link"],
    }
    bulk_support = []
    for s in BULK["support_assets"]:
        kind = s.get("kind") if s.get("kind") in KIND_CATS else "software"
        sa = SupportAsset.objects.create(
            name=s["name"], type=kind, category=RNG.choice(KIND_CATS[kind]),
            description=s.get("description", ""), owner=pick_user(), environment="production",
            exposure_level="internet_facing" if s.get("internet_facing") else RNG.choice(["internal", "exposed"]),
            status="active", **approved(elise),
        )
        sa.scopes.set([RNG.choice(scope_pool)])
        bulk_support.append(sa)

    all_essential = essential_assets + bulk_essential
    all_support = support_assets + bulk_support

    # A few dependencies so the bulk assets feed the dependency graph / SPOF.
    DEP_TYPES = ["runs_on", "stored_in", "transmitted_by", "managed_by", "protected_by"]
    for ea in bulk_essential:
        for sa in RNG.sample(all_support, k=RNG.randint(1, 3)):
            spof = RNG.random() < 0.18
            AssetDependency.objects.create(
                essential_asset=ea, support_asset=sa, dependency_type=RNG.choice(DEP_TYPES),
                criticality=RNG.choice(["low", "medium", "high", "critical"]),
                redundancy_level="none" if spof else RNG.choice(["partial", "full"]),
                is_single_point_of_failure=spof,
                created_by=julien, is_approved=True, approved_by=elise, approved_at=NOW,
            )

    # --- suppliers -------------------------------------------------------
    TYPE_MAP = {"cloud": st_cloud, "mssp": st_mssp, "industrial": st_industrial,
                "saas": st_saas, "facility": st_facility}
    SR_TITLES = ["ISO/IEC 27001 certificate", "SOC 2 Type II report", "GDPR data processing agreement",
                 "Security questionnaire", "Penetration test report", "EU data residency confirmation"]
    bulk_suppliers = []
    for s in BULK["suppliers"]:
        start = years_ago(4.5) + timedelta(days=RNG.randint(0, 1000))
        s_country = s.get("country", "France")
        s_address, s_lat, s_lon = supplier_location(s_country)
        sup = Supplier.objects.create(
            name=s["name"], type=TYPE_MAP.get(s.get("type_key"), st_saas),
            criticality=s.get("criticality", "medium"), description=s.get("description", ""),
            country=s_country, address=s_address, latitude=s_lat, longitude=s_lon,
            owner=pick_user(),
            contract_start_date=start, contract_end_date=start + timedelta(days=RNG.randint(365, 1460)),
            status="active", **approved(elise),
        )
        sup.scopes.set([scope_group])
        sup.tags.set([tag_thirdparty])
        bulk_suppliers.append(sup)
        for title in RNG.sample(SR_TITLES, k=RNG.randint(1, 3)):
            SupplierRequirement.objects.create(
                supplier=sup, title=title,
                compliance_status=RNG.choice(["not_assessed", "compliant", "compliant",
                                              "partially_compliant", "non_compliant"]),
            )
    # Wire a few supplier dependencies onto bulk support assets.
    for sa in RNG.sample(bulk_support, k=min(20, len(bulk_support))):
        SupplierDependency.objects.create(
            support_asset=sa, supplier=RNG.choice(bulk_suppliers + all_suppliers),
            dependency_type=RNG.choice(["provides", "hosts", "manages", "maintains", "supports", "licenses"]),
            criticality=RNG.choice(["low", "medium", "high", "critical"]),
            redundancy_level=RNG.choice(["none", "partial", "full"]),
            created_by=julien, is_approved=True, approved_by=elise, approved_at=NOW,
        )

    # --- threats ---------------------------------------------------------
    TH_TYPE_BY_ORIGIN = {"human_external": "deliberate", "human_internal": "accidental",
                         "technical": "other", "natural": "environmental"}
    TH_CATS = ["malware", "social_engineering", "unauthorized_access", "denial_of_service", "data_breach",
               "physical_attack", "espionage", "fraud", "sabotage", "human_error", "system_failure",
               "network_failure", "power_failure", "natural_disaster", "fire", "water_damage", "theft",
               "supply_chain", "insider_threat", "ransomware", "apt"]
    bulk_threats = []
    for t in BULK["threats"]:
        origin = t.get("origin") if t.get("origin") in TH_TYPE_BY_ORIGIN else "human_external"
        th = Threat.objects.create(
            name=t["name"], type=TH_TYPE_BY_ORIGIN[origin], description=t.get("description", ""),
            origin=origin, category=RNG.choice(TH_CATS), typical_likelihood=RNG.randint(1, 5),
            status="active", **approved(elise),
        )
        th.scopes.set([scope_group])
        bulk_threats.append(th)

    # --- vulnerabilities -------------------------------------------------
    V_CATS = ["configuration_weakness", "missing_patch", "design_flaw", "coding_error", "weak_authentication",
              "insufficient_logging", "lack_of_encryption", "physical_vulnerability", "organizational_weakness",
              "human_factor", "obsolescence", "insufficient_backup", "network_exposure", "third_party_dependency"]
    bulk_vulns = []
    for v in BULK["vulnerabilities"]:
        vv = Vulnerability.objects.create(
            name=v["name"], description=v.get("description", ""), category=RNG.choice(V_CATS),
            severity=v.get("severity", "medium"),
            status=RNG.choice(["identified", "confirmed", "confirmed", "mitigated", "accepted"]),
            remediation_guidance="Apply the vendor fix or a documented compensating control.",
            affected_asset_types=["server", "network_equipment"],
            created_by=julien, is_approved=True, approved_by=elise, approved_at=NOW,
        )
        vv.scopes.set([scope_group])
        vv.affected_assets.set(RNG.sample(all_support, k=RNG.randint(1, 2)))
        bulk_vulns.append(vv)

    # --- risks (+ treatment plans / acceptances / iso27005 analyses) -----
    DECISIONS = ["mitigate", "mitigate", "mitigate", "accept", "transfer", "avoid"]
    PRIOS = ["low", "medium", "high", "critical"]
    R_STATUS = ["identified", "analyzed", "evaluated", "treatment_planned",
                "treatment_in_progress", "treated", "monitoring"]
    bulk_risks = []
    for r in BULK["risks"]:
        il = RNG.randint(2, 5)
        ii = RNG.randint(2, 5)
        cl = max(1, il - RNG.randint(0, 1))
        ci = max(1, ii - RNG.randint(0, 1))
        rl = max(1, cl - RNG.randint(0, 2))
        ri = max(1, ci - RNG.randint(0, 1))
        decision = RNG.choice(DECISIONS)
        status_value = "accepted" if decision == "accept" else RNG.choice(R_STATUS)
        risk = mk_risk(
            r["name"], r.get("description", ""), il, ii, cl, ci, rl, ri, decision,
            RNG.choice(PRIOS), status_value, pick_user(),
            c=bool(r.get("c")), i=bool(r.get("i")), a=bool(r.get("a")),
            source=RNG.choice(["manual", "iso27005_analysis"]),
        )
        risk.affected_essential_assets.set(RNG.sample(all_essential, k=RNG.randint(1, 2)))
        risk.affected_support_assets.set(RNG.sample(all_support, k=RNG.randint(1, 2)))
        bulk_risks.append((risk, decision, rl, ri))

    for idx, (risk, decision, rl, ri) in enumerate(bulk_risks):
        if decision == "mitigate" and idx % 2 == 0:
            tp_status = RNG.choice(["planned", "in_progress", "in_progress", "completed", "overdue"])
            tp_done = tp_status == "completed"
            tp = RiskTreatmentPlan.objects.create(
                risk=risk, name=f"Treatment plan : {risk.name[:60]}",
                description="Mitigation measures to bring the residual risk within appetite.",
                treatment_type="mitigate", expected_residual_likelihood=rl, expected_residual_impact=ri,
                cost_estimate=Decimal(str(RNG.choice([15000, 25000, 40000, 60000, 90000]))),
                owner=risk.risk_owner, start_date=TODAY - timedelta(days=RNG.randint(30, 120)),
                target_date=(TODAY - timedelta(days=RNG.randint(1, 30)) if tp_status == "overdue"
                             else TODAY + timedelta(days=RNG.randint(30, 300))),
                progress_percentage=100 if tp_done else RNG.randint(0, 95),
                status=tp_status,
                completion_date=TODAY - timedelta(days=RNG.randint(1, 30)) if tp_done else None,
                created_by=risk.risk_owner,
            )
            for order in range(1, RNG.randint(2, 4)):
                st_val = RNG.choice(["planned", "in_progress", "completed"])
                TreatmentAction.objects.create(
                    treatment_plan=tp, description=f"Implementation step {order}", owner=risk.risk_owner,
                    target_date=TODAY + timedelta(days=30 * order), status=st_val, order=order,
                    completion_date=TODAY - timedelta(days=RNG.randint(1, 30)) if st_val == "completed" else None,
                )
        elif decision == "accept":
            ra_expired = RNG.choice([False, False, True])
            RiskAcceptance.objects.create(
                risk=risk, accepted_by=elise,
                justification="Residual risk is within the corporate appetite; further treatment is disproportionate this cycle.",
                conditions="Reviewed at the next risk committee.",
                valid_until=(TODAY - timedelta(days=RNG.randint(1, 60)) if ra_expired
                             else TODAY + timedelta(days=RNG.randint(90, 540))),
                review_date=(TODAY - timedelta(days=RNG.randint(1, 30)) if ra_expired
                             else TODAY + timedelta(days=RNG.randint(60, 300))),
                status="expired" if ra_expired else "active", created_by=risk.risk_owner,
            )

    # ISO 27005 analyses linking bulk threats + vulnerabilities to ~25 risks.
    for risk, _d, _rl, _ri in bulk_risks[:25]:
        an = ISO27005Risk.objects.create(
            assessment=assessment, threat=RNG.choice(bulk_threats),
            vulnerability=RNG.choice(bulk_vulns),
            threat_likelihood=RNG.randint(2, 5), vulnerability_exposure=RNG.randint(2, 5),
            impact_confidentiality=RNG.randint(1, 5), impact_integrity=RNG.randint(1, 5),
            impact_availability=RNG.randint(1, 5),
            existing_controls="Baseline controls in place; monitored by the SOC.",
            risk=risk, created_by=julien, is_approved=True, approved_by=elise, approved_at=NOW,
        )
        an.affected_support_assets.set(list(risk.affected_support_assets.all()))

    # --- action plans ----------------------------------------------------
    AP_PRIO = ["low", "medium", "high", "critical"]
    AP_STATUS = ["new", "to_define", "to_validate", "to_implement", "to_implement", "validated", "closed"]
    all_reqs = list(iso_reqs.values()) + list(nis2_reqs.values()) + list(vsb_reqs.values())
    for a in BULK["action_plans"]:
        ap_status = RNG.choice(AP_STATUS)
        ap_closed = ap_status == "closed"
        ap = ComplianceActionPlan.objects.create(
            name=a["name"], description=a.get("remediation", ""), gap_description=a.get("gap", ""),
            remediation_plan=a.get("remediation", ""), priority=RNG.choice(AP_PRIO),
            owner=pick_user(), created_by=elise,
            start_date=TODAY - timedelta(days=RNG.randint(30, 150)),
            target_date=TODAY + timedelta(days=RNG.randint(30, 320)),
            progress_percentage=100 if ap_closed else RNG.randint(0, 95), status=ap_status,
            completion_date=TODAY - timedelta(days=RNG.randint(1, 30)) if ap_closed else None,
        )
        ap.scopes.set([RNG.choice(scope_pool)])
        if RNG.random() < 0.5:
            ap.requirements.set(RNG.sample(all_reqs, k=RNG.randint(1, 2)))

    # --- indicators ------------------------------------------------------
    for ind_data in BULK["indicators"]:
        technical = ind_data.get("technical")
        above = RNG.random() < 0.5
        threshold = RNG.randint(5, 95)
        ind = Indicator.objects.create(
            name=ind_data["name"], description=ind_data.get("description", ""),
            indicator_type="technical" if technical else "organizational",
            collection_method="manual", format="number", unit=(ind_data.get("unit") or "%")[:20],
            review_frequency="monthly", first_review_date=TODAY + timedelta(days=19),
            critical_threshold_operator="above" if above else "below",
            critical_threshold_value=str(threshold),
            critical_threshold_max=float(threshold) if above else None,
            critical_threshold_min=float(threshold) if not above else None,
            status="active", owner=pick_user(), **approved(elise),
        )
        ind.scopes.set([RNG.choice(scope_pool)])
        val = float(RNG.randint(10, 100))
        for offset in [300, 270, 240, 210, 180, 150, 120, 90, 60, 30]:
            val = max(0.0, min(100.0, val + RNG.uniform(-8, 8)))
            IndicatorMeasurement.objects.create(
                indicator=ind, value=str(round(val, 1)),
                recorded_at=NOW - timedelta(days=offset), recorded_by=elise,
            )
        ind.record_measurement(str(round(max(0.0, min(100.0, val + RNG.uniform(-5, 5))), 1)), recorded_by=elise)

    # --- SWOT analyses (complete) ----------------------------------------
    for sw in BULK["swots"]:
        swa = SwotAnalysis.objects.create(
            name=sw["name"], description="Strategic SWOT analysis for the Voltara ISMS.",
            analysis_date=TODAY - timedelta(days=RNG.randint(10, 220)),
            review_date=TODAY + timedelta(days=RNG.randint(180, 420)),
            validated_by=elise, validated_at=NOW, **approved(elise),
        )
        swa.scopes.set([RNG.choice(scope_pool)])
        for order, item in enumerate(sw.get("items", []), 1):
            SwotItem.objects.create(
                swot_analysis=swa, quadrant=item["quadrant"], description=item["description"],
                impact_level=item.get("impact", "medium"), order=order,
            )
        for order, stg in enumerate(sw.get("strategies", []), 1):
            SwotStrategy.objects.create(
                swot_analysis=swa, quadrant=stg["quadrant"], description=stg["description"], order=order,
            )

    # --- findings on every completed/in-progress audit -------------------
    STATUS_TO_FINDING = {
        "major_non_conformity": "major_nc", "minor_non_conformity": "minor_nc",
        "observation": "observation", "improvement_opportunity": "improvement", "strength": "strength",
    }
    for asm in [asm_gdpr, asm_nis2, asm_vsb]:
        for res in asm.results.select_related("requirement"):
            ft = STATUS_TO_FINDING.get(res.compliance_status)
            if not ft:
                continue
            num = res.requirement.requirement_number
            f = Finding.objects.create(
                assessment=asm, finding_type=ft, assessor=asm.assessor or elise, created_by=elise,
                description=res.finding or f"{num} - {res.get_compliance_status_display()} identified during the assessment.",
                recommendation="Define and track a corrective action to close the gap.",
                evidence="Audit interviews and document sampling.",
                workflow_state="validated", is_approved=True, approved_by=elise, approved_at=NOW,
            )
            f.requirements.set([res.requirement])

    # ------------------------------------------------------------ housekeeping
    print("SPOF detection and notifications...")
    SpofDetector().apply()

    from django.contrib.contenttypes.models import ContentType
    Notification.objects.create(
        recipient=elise, actor=marc, notification_type="lifecycle_submitted",
        title='Scope "R&D Innovation Lab" is pending validation',
        message="Marc Lefevre submitted the scope R&D Innovation Lab for validation.",
        target_content_type=ContentType.objects.get(app_label="context", model="scope"),
        target_object_id=str(scope_rnd.pk),
        target_url=f"/context/scopes/{scope_rnd.pk}/",
    )
    Notification.objects.create(
        recipient=elise, actor=julien, notification_type="lifecycle_submitted",
        title='Threat "AI-assisted social engineering" is pending validation',
        message="Julien Petit submitted a new threat for validation.",
        target_content_type=ContentType.objects.get(app_label="risks", model="threat"),
        target_object_id="",
        target_url="/risks/threats/",
    )

    # ----------------------------------------------------------- trust center
    print("Trust Center...")
    # A simple Voltara mark (lightning bolt) as an SVG data URI, used as the
    # public hero logo and the favicon.
    voltara_logo = "data:image/svg+xml," + quote(
        "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'>"
        "<rect width='64' height='64' rx='14' fill='#0E9F6E'/>"
        "<path d='M35 7 L17 36 H29 L26 57 L47 27 H34 Z' fill='#ffffff'/>"
        "</svg>"
    )
    cs.logo = voltara_logo
    cs.logo_64 = voltara_logo
    cs.logo_128 = voltara_logo
    cs.save()

    tc = TrustCenterSettings.get()
    tc.is_published = True
    tc.headline = "Security and compliance at Voltara Energy"
    tc.intro = (
        "<p>At <strong>Voltara Energy</strong> we operate critical renewable "
        "energy infrastructure, and we hold our security and privacy practices "
        "to a high standard.</p>"
        "<p>This Trust Center summarizes our certifications, the subprocessors we "
        "rely on, and the controls that protect customer and operational data. "
        "For anything not published here, <em>reach out to our security team</em>.</p>"
    )
    tc.contact_email = "security@voltara.example"
    tc.show_compliance_percentages = True
    tc.theme_accent = "#0E9F6E"
    tc.custom_css = (
        "/* Voltara Energy - Trust Center theme */\n"
        ":root {\n"
        "  --accent: #0E9F6E;\n"
        "  --accent-soft: #E6FBF3;\n"
        "  --accent-glow: rgba(14, 159, 110, .18);\n"
        "  --bg: #F4FBF8;\n"
        "}\n"
        '[data-bs-theme="dark"] {\n'
        "  --accent: #2BD4A0;\n"
        "  --accent-soft: rgba(43, 212, 160, .14);\n"
        "  --accent-glow: rgba(43, 212, 160, .22);\n"
        "  --bg: #0A0F0D;\n"
        "  --surface: #0F1714;\n"
        "}\n"
        ".tc-hero {\n"
        "  background:\n"
        "    radial-gradient(120% 120% at 85% -10%, rgba(163, 230, 53, .30) 0%, transparent 55%),\n"
        "    linear-gradient(135deg, #065F46 0%, #0E9F6E 60%, #0BA5A4 100%);\n"
        "}\n"
        ".tc-section h2 { display: inline-block; padding-bottom: .35rem; border-bottom: 3px solid var(--accent); }\n"
        ".tc-card:hover { border-color: var(--accent); box-shadow: 0 12px 30px var(--accent-glow); }\n"
        ".tc-footer { border-top: 2px solid var(--accent); }\n"
    )
    tc.save()

    def tc_pub(**kwargs):
        return dict(created_by=elise, workflow_state=PublicationState.PUBLISHED, **kwargs)

    TrustCenterCertification.objects.create(
        framework=fw_iso, public_label="ISO/IEC 27001:2022",
        public_description="<p>Our ISMS is certified against ISO/IEC 27001, covering the full Annex A control set.</p>",
        show_percentage=True, display_order=1, **tc_pub(),
    )
    TrustCenterCertification.objects.create(
        framework=fw_nis2, public_label="NIS2 Directive",
        public_description="<p>As an operator of essential services, we align with the EU NIS2 cybersecurity measures.</p>",
        show_percentage=True, display_order=2, **tc_pub(),
    )
    TrustCenterCertification.objects.create(
        framework=fw_gdpr, public_label="GDPR",
        public_description="<p>Personal data is processed in line with the EU General Data Protection Regulation.</p>",
        show_percentage=True, display_order=3, **tc_pub(),
    )

    TrustCenterSubprocessor.objects.create(
        supplier=sup_cloudnord, public_name="CloudNord",
        purpose="Cloud hosting and colocation for production workloads",
        public_country="France", public_website="https://cloudnord.example",
        display_order=1, **tc_pub(),
    )
    TrustCenterSubprocessor.objects.create(
        supplier=sup_sentinel, public_name="SentinelWatch",
        purpose="24/7 managed security operations (SOC / SIEM)",
        public_country="France", public_website="https://sentinelwatch.example",
        display_order=2, **tc_pub(),
    )
    TrustCenterSubprocessor.objects.create(
        supplier=sup_paycore, public_name="PayCore",
        purpose="Payment processing for customer invoicing",
        public_country="Netherlands", public_website="https://paycore.example",
        display_order=3, **tc_pub(),
    )
    TrustCenterSubprocessor.objects.create(
        supplier=sup_hrline, public_name="HRline",
        purpose="Human resources information system",
        public_country="France", display_order=4, **tc_pub(),
    )

    TrustCenterMeasure.objects.create(
        title="Security governance and ISMS", category="organizational",
        icon="bi-diagram-3",
        description="<p>An ISO 27001-aligned ISMS led by an appointed CISO and DPO, with annual internal audits and management reviews.</p>",
        display_order=1, **tc_pub(),
    )
    TrustCenterMeasure.objects.create(
        title="Vendor risk management", category="organizational",
        icon="bi-shield-check",
        description="<p>Every critical supplier is assessed against security requirements before and during the engagement.</p>",
        display_order=2, **tc_pub(),
    )
    TrustCenterMeasure.objects.create(
        title="Encryption in transit and at rest", category="technical",
        icon="bi-lock",
        description="<p>Customer and operational data is encrypted with industry-standard algorithms, in transit and at rest.</p>",
        display_order=3, **tc_pub(),
    )
    TrustCenterMeasure.objects.create(
        title="24/7 monitoring and detection", category="technical",
        icon="bi-activity",
        description="<p>A managed SOC operates our SIEM around the clock to detect and respond to threats.</p>",
        display_order=4, **tc_pub(),
    )
    TrustCenterMeasure.objects.create(
        title="Secure data centers", category="physical",
        icon="bi-hdd-rack",
        description="<p>Production runs in ISO 27001-certified EU data centers with strict physical access controls.</p>",
        display_order=5, **tc_pub(),
    )

    demo_pdf = b"%PDF-1.4\n% Voltara Energy - Trust Center demo document.\n"
    TrustCenterDocument.objects.create(
        title="Information security overview", access=DocumentAccess.PUBLIC,
        description="<p>A high-level summary of our security program.</p>",
        file_content=demo_pdf, file_name="voltara-security-overview.pdf",
        content_type="application/pdf", display_order=1, **tc_pub(),
    )
    TrustCenterDocument.objects.create(
        title="Data processing addendum (template)", access=DocumentAccess.PUBLIC,
        description="<p>Our standard DPA template for customers and partners.</p>",
        file_content=b"PK\x03\x04 Voltara DPA template (demo).",
        file_name="voltara-dpa-template.docx",
        content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        display_order=2, **tc_pub(),
    )
    doc_soc2 = TrustCenterDocument.objects.create(
        title="SOC 2 Type II report", access=DocumentAccess.GATED, requires_nda=True,
        description="<p>Available on request after acceptance of our NDA.</p>",
        file_content=demo_pdf, file_name="voltara-soc2-type-ii.pdf",
        content_type="application/pdf", display_order=3, **tc_pub(),
    )
    TrustCenterDocument.objects.create(
        title="Penetration test executive summary", access=DocumentAccess.GATED,
        requires_nda=True,
        description="<p>Latest third-party penetration test summary, available on request.</p>",
        file_content=demo_pdf, file_name="voltara-pentest-summary.pdf",
        content_type="application/pdf", display_order=4, **tc_pub(),
    )

    # One pending access request so the curation inbox is not empty.
    DocumentRequest.objects.create(
        document=doc_soc2, email="jordan.blake@acme-corp.example",
        requester_name="Jordan Blake", company="ACME Corp",
        reason="Vendor due diligence for an upcoming contract.",
        nda_accepted=True, nda_accepted_at=NOW,
    )

print("Seed completed.")
print(f"  Users: {User.objects.count()}  Scopes: {Scope.objects.count()}  Sites: {Site.objects.count()}")
print(f"  Essential assets: {EssentialAsset.objects.count()}  Support assets: {SupportAsset.objects.count()}")
print(f"  Frameworks: {Framework.objects.count()}  Requirements: {Requirement.objects.count()}")
print(f"  Risks: {Risk.objects.count()}  Treatment plans: {RiskTreatmentPlan.objects.count()}")
print(f"  Action plans: {ComplianceActionPlan.objects.count()}  Indicators: {Indicator.objects.count()}")
print(
    f"  Trust Center: {TrustCenterCertification.objects.count()} certifications, "
    f"{TrustCenterSubprocessor.objects.count()} subprocessors, "
    f"{TrustCenterMeasure.objects.count()} measures, "
    f"{TrustCenterDocument.objects.count()} documents, "
    f"{DocumentRequest.objects.count()} request"
)
print("Login: elise.moreau@voltara.example / " + PASSWORD)
