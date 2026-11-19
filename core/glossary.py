# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""The glossary : one thing, one name, everywhere.

A newcomer is not stopped by one unfamiliar word that is explained. They are
stopped by five words for one thing, and by an acronym nobody spells out. The
product therefore names each notion once (``docs/brand/glossary.md`` is the
reference, with the reasons), and this module is that vocabulary as the
application shows it :

- the page ``/glossary/``, reached from the help of every page and from the
  user menu;
- the search palette, which answers a word a reader types (*actif*, *audit*,
  *DIC*) with the name the product uses, including the names it does not use
  (``also``);
- the REST endpoint ``/api/v1/glossary/`` and the MCP tool ``get_glossary``,
  so an assistant speaks the words the interface shows.

A term is a notion of the product : its name, a definition a newcomer can
read, with an example, the other names people know it by, and the register
where it lives. An acronym is spelled out, then explained.

Every string is translated : the French catalogue holds the French names
(*bien essentiel*, *partie intéressée*, *SMSI*). A term takes the very
message the interface uses for it (``_("Stakeholder")``), so the glossary
cannot name a thing otherwise than the screens do. ``also`` is one string,
the names separated by commas, under its own context : the other names of a
thing are not the same in each language, and are not translations of each
other.

``core/tests/test_glossary.py`` holds the vocabulary : every term is defined
in both languages, every acronym a screen shows is listed here or is an
everyday word (``core.usability.EVERYDAY_ACRONYMS``), and the French
catalogue does not use a spelling the glossary retires.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass

from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy


@dataclass(frozen=True)
class Term:
    """A notion of the product, under the one name the interface gives it."""

    key: str
    name: str
    definition: str
    #: The other names people know it by, separated by commas (one string).
    also: str = ""
    #: The register where it lives, as a URL name.
    url_name: str = ""


@dataclass(frozen=True)
class Acronym:
    """An acronym a screen may show, spelled out and explained."""

    key: str
    letters: str
    words: str
    definition: str = ""
    #: The name of a standard, a law, an agency or a method : it is used as it
    #: is (*ISO 27001*, *NIS2*), where another acronym is spelled out first.
    proper: bool = False


TERMS = (
    # ── Organisation ────────────────────────────────────────────────────────
    Term(
        "scope", _("Scope"),
        _("What your security work applies to : the whole company, one site or one activity. Every other record is filed under a scope."),
        pgettext_lazy("glossary : other names", "perimeter, boundary"), "context:scope-list",
    ),
    Term(
        "site", _("Site"),
        _("A place where the organisation works or keeps its equipment : an office, a data centre, a factory."),
        pgettext_lazy("glossary : other names", "location, premises"), "assets:site-list",
    ),
    Term(
        "issue", _("Issue"),
        _("A fact, inside or outside the organisation, that weighs on your security : a new regulation, fast growth, a move to the cloud."),
        pgettext_lazy("glossary : other names", "context factor"), "context:issue-list",
    ),
    Term(
        "stakeholder", _("Stakeholder"),
        _("A person or an organisation that expects something of your security : a client, a regulator, your staff."),
        pgettext_lazy("glossary : other names", "interested party"), "context:stakeholder-list",
    ),
    Term(
        "objective", _("Objective"),
        _("A measurable aim of your security work, for example training every newcomer within a month."),
        pgettext_lazy("glossary : other names", "goal, target"), "context:objective-list",
    ),
    Term(
        "indicator", _("Indicator"),
        _("A figure followed over time to know whether things go as intended : the share of laptops encrypted, the time taken to close an incident."),
        pgettext_lazy("glossary : other names", "metric, KPI"), "context:indicator-organizational-list",
    ),
    Term(
        "role", _("Role"),
        _("A function in the security organisation, with its responsibilities, given to one or several people."),
        pgettext_lazy("glossary : other names", "function"), "context:role-list",
    ),
    Term(
        "activity", _("Activity"),
        _("Something the organisation does as part of its business : invoicing, recruiting, manufacturing."),
        pgettext_lazy("glossary : other names", "business process"), "context:activity-list",
    ),
    Term(
        "management_review", _("Management review"),
        _("The regular meeting where the management looks at how security is doing and decides what changes."),
        pgettext_lazy("glossary : other names", "steering committee"), "reports:management-review-list",
    ),
    # ── What is protected ───────────────────────────────────────────────────
    Term(
        "essential_asset", _("Essential asset"),
        _("What the business cannot do without : a piece of information you hold or an activity you run, such as the customer file, payroll or production."),
        pgettext_lazy("glossary : other names", "business value, primary asset"), "assets:essential-asset-list",
    ),
    Term(
        "support_asset", _("Support asset"),
        _("What an essential asset relies on to work : a server, an application, premises, a team or the service of a supplier."),
        pgettext_lazy("glossary : other names", "supporting asset"), "assets:support-asset-list",
    ),
    Term(
        "security_needs", _("Security needs"),
        _("How much an essential asset must stay available, exact and secret : its availability, its integrity and its confidentiality, each rated on a scale."),
        pgettext_lazy("glossary : other names", "CIA, valuation, classification"), "assets:essential-asset-list",
    ),
    Term(
        "dependency", _("Dependency"),
        _("The link saying that one thing needs another to work : payroll needs the HR application, which needs its hosting supplier."),
        "", "assets:dependency-list",
    ),
    Term(
        "supplier", _("Supplier"),
        _("An outside organisation you depend on : a hosting company, a software publisher, a subcontractor."),
        pgettext_lazy("glossary : other names", "third party, vendor, provider"), "assets:supplier-list",
    ),
    # ── Risks ───────────────────────────────────────────────────────────────
    Term(
        "risk", _("Risk"),
        _("Something that could go wrong, and what it would cost you : a threat, the weakness it uses and the damage it would do."),
        "", "risks:risk-list",
    ),
    Term(
        "risk_assessment", _("Risk assessment"),
        _("The exercise of listing your risks, rating how likely and how serious each one is, and deciding what to do about them."),
        pgettext_lazy("glossary : other names", "risk analysis, risk study"), "risks:assessment-list",
    ),
    Term(
        "threat", _("Threat"),
        _("What could cause harm : a fire, a ransomware attack, a mistake."),
        "", "risks:threat-list",
    ),
    Term(
        "vulnerability", _("Vulnerability"),
        _("A weakness a threat can use : a server that is not updated, a newcomer who was not trained."),
        pgettext_lazy("glossary : other names", "weakness, flaw"), "risks:vulnerability-list",
    ),
    Term(
        "likelihood", _("Likelihood"),
        _("How plausible it is that a risk happens, on the scale of your risk criteria."),
        pgettext_lazy("glossary : other names", "probability"), "risks:criteria-list",
    ),
    Term(
        "impact", _("Impact"),
        _("How serious the damage would be if the risk happened, on the scale of your risk criteria. EBIOS RM calls it gravity."),
        pgettext_lazy("glossary : other names", "severity, gravity"), "risks:criteria-list",
    ),
    Term(
        "treatment_plan", _("Treatment plan"),
        _("What you decide to do about a risk : reduce it, avoid it, share it or accept it, with the actions that follow."),
        pgettext_lazy("glossary : other names", "risk treatment, remediation plan"), "risks:treatment-plan-list",
    ),
    Term(
        "risk_acceptance", _("Risk acceptance"),
        _("The formal decision, by someone entitled to take it, to live with a risk as it is, for a given time."),
        "", "risks:acceptance-list",
    ),
    # ── EBIOS RM : the words of the method, kept as the ANSSI guide writes them ──
    Term(
        "feared_event", _("Feared event"),
        _("In EBIOS RM, what the organisation fears for one of its essential assets : that it leaks, is altered or stops. Each one is rated for its gravity."),
        "", "",
    ),
    Term(
        "security_baseline", _("Security baseline"),
        _("In EBIOS RM, what the organisation already applies to protect itself : the frameworks it follows, with the rules they hold."),
        "", "",
    ),
    Term(
        "risk_source", pgettext_lazy("EBIOS RM", "Risk source"),
        _("In EBIOS RM, an attacker who could aim at the organisation : a criminal group, a competitor, a disgruntled employee."),
        pgettext_lazy("glossary : other names", "attacker, threat actor"), "",
    ),
    Term(
        "targeted_objective", _("Targeted objective"),
        _("In EBIOS RM, the goal a risk source pursues : money, espionage, sabotage."),
        "", "",
    ),
    Term(
        "ecosystem_stakeholder", _("Ecosystem stakeholder"),
        _("In EBIOS RM, an organisation an attack can come through to reach you : a supplier, a partner, a client."),
        "", "",
    ),
    Term(
        "strategic_scenario", _("Strategic scenario"),
        _("In EBIOS RM, the path of an attack seen from above : from a risk source to a feared event, through the ecosystem."),
        "", "",
    ),
    Term(
        "operational_scenario", _("Operational scenario"),
        _("In EBIOS RM, a strategic scenario detailed step by step : the techniques an attacker would use on your support assets."),
        "", "",
    ),
    Term(
        "baseline_gap", _("Baseline gap"),
        _("In EBIOS RM, a rule of the security baseline that the organisation does not meet yet, for example a network that is not segregated."),
        "", "",
    ),
    # ── Compliance ──────────────────────────────────────────────────────────
    Term(
        "framework", _("Framework"),
        _("A standard, a law or a set of internal rules you choose to comply with, ISO 27001 for instance. It is made of requirements."),
        pgettext_lazy("glossary : other names", "standard, regulation"), "compliance:framework-list",
    ),
    Term(
        "requirement", _("Requirement"),
        _("One thing a framework asks of you, such as keeping an inventory of what you protect."),
        pgettext_lazy("glossary : other names", "clause, obligation"), "compliance:requirement-list",
    ),
    Term(
        "compliance_assessment", _("Compliance assessment"),
        _("A check, at a given date, of how far you meet the requirements of a framework : a self-assessment, an internal audit or a certification audit."),
        pgettext_lazy("glossary : other names", "audit, evaluation"), "compliance:assessment-list",
    ),
    Term(
        "finding", _("Finding"),
        _("What an assessment or a test noticed : a nonconformity to correct, a remark, or a point that works well."),
        pgettext_lazy("glossary : other names", "observation, gap"), "compliance:finding-list",
    ),
    Term(
        "nonconformity", _("Nonconformity"),
        _("A finding that says a requirement is not met. It is corrected through an action plan."),
        pgettext_lazy("glossary : other names", "deviation, gap"), "compliance:finding-list",
    ),
    Term(
        "action_plan", _("Action plan"),
        _("The work decided to correct a finding or to reach compliance, with an owner and a deadline."),
        pgettext_lazy("glossary : other names", "corrective action, remediation"), "compliance:action-plan-list",
    ),
    Term(
        "control", pgettext_lazy("control", "Control"),
        _("Something you do or put in place to reduce a risk or meet a requirement : a backup, a rule, a training session."),
        pgettext_lazy("glossary : other names", "security measure, safeguard"), "controls:control-list",
    ),
    Term(
        "control_test", _("Control test"),
        _("A check that a control really works : restoring a backup to see that it can be read, for example."),
        "", "controls:controltest-list",
    ),
    Term(
        "document", _("Document"),
        _("A written rule of the organisation, a policy, a procedure or a charter, with its versions, its approval and the people who must read it."),
        pgettext_lazy("glossary : other names", "policy, procedure, documented information"), "documents:policy-list",
    ),
    Term(
        "evidence", pgettext_lazy("incident", "Evidence"),
        _("What proves that something was done : a report, a screenshot, an export, a signed document."),
        pgettext_lazy("glossary : other names", "proof, record"), "",
    ),
    # ── Incidents ───────────────────────────────────────────────────────────
    Term(
        "incident", pgettext_lazy("incident", "Security incident"),
        _("Something that happened and harmed your information, or could have : a stolen laptop, an intrusion, a message sent to the wrong person."),
        "", "incidents:incident-list",
    ),
    Term(
        "security_event", pgettext_lazy("incident", "Security event"),
        _("Something unusual that someone reports and that may or may not turn out to be an incident : a suspicious message, a door left open."),
        pgettext_lazy("glossary : other names", "alert, report"), "incidents:event-list",
    ),
    # ── How records live ────────────────────────────────────────────────────
    Term(
        "owner", _("Owner"),
        _("The person who answers for a record and decides about it."),
        pgettext_lazy("glossary : other names", "accountable person"), "",
    ),
    Term(
        "manager", _("Manager"),
        _("The person who runs something day to day : a scope, an action."),
        pgettext_lazy("glossary : other names", "person in charge"), "",
    ),
    Term(
        "custodian", _("Custodian"),
        _("The person who looks after an asset in practice, on behalf of its owner : the administrator of a server."),
        pgettext_lazy("glossary : other names", "keeper, administrator"), "",
    ),
    Term(
        "lifecycle", _("Lifecycle"),
        _("The steps a record goes through, from draft to archived. A record counts in reports once it has reached a validated step."),
        pgettext_lazy("glossary : other names", "workflow, approval circuit"), "",
    ),
    Term(
        "lifecycle_step", _("Step"),
        _("Where a record stands in its lifecycle : draft, validated, archived. A list shows it in its Status column."),
        pgettext_lazy("glossary : other names", "state, status, stage"), "",
    ),
    Term(
        "review", _("Review"),
        _("Looking at a record again on a planned date, to confirm that it is still right."),
        pgettext_lazy("glossary : other names", "periodic check"), "",
    ),
    Term(
        "tag", _("Tag"),
        _("A free word you put on records to find them again."),
        pgettext_lazy("glossary : other names", "label, keyword"), "context:tag-list",
    ),
)


ACRONYMS = (
    Acronym(
        "isms", pgettext_lazy("glossary : acronym", "ISMS"), _("information security management system"),
        _("Everything your organisation does to keep its information safe, organised so that it can be checked and improved : rules, roles, risks, controls and reviews."),
    ),
    Acronym(
        "cia", pgettext_lazy("glossary : acronym", "CIA"), _("confidentiality, integrity, availability"),
        _("The three security needs of an asset : that it stays secret, exact and usable."),
    ),
    Acronym(
        "mtd", pgettext_lazy("glossary : acronym", "MTD"), _("maximum tolerable downtime"),
        _("How long an activity may stay stopped before the damage becomes unacceptable."),
    ),
    Acronym(
        "rto", pgettext_lazy("glossary : acronym", "RTO"), _("recovery time objective"),
        _("The time within which you aim to restart an activity after it stops."),
    ),
    Acronym(
        "rpo", pgettext_lazy("glossary : acronym", "RPO"), _("recovery point objective"),
        _("How much recent data you accept to lose : an RPO of four hours means a backup at least every four hours."),
    ),
    Acronym(
        "spof", pgettext_lazy("glossary : acronym", "SPOF"), _("single point of failure"),
        _("Something that stops an essential asset when it fails, because nothing replaces it."),
    ),
    Acronym(
        "kpi", pgettext_lazy("glossary : acronym", "KPI"), _("key performance indicator"),
        _("The figure that tells whether an objective is being reached."),
    ),
    Acronym(
        "raci", pgettext_lazy("glossary : acronym", "RACI"), _("responsible, accountable, consulted, informed"),
        _("Four ways to be involved in a task : doing it, answering for it, being asked before, being told after."),
    ),
    Acronym(
        "swot", pgettext_lazy("glossary : acronym", "SWOT"), _("strengths, weaknesses, opportunities, threats"),
        _("A four-box picture of where the organisation stands, used to choose its priorities."),
    ),
    Acronym(
        "soa", pgettext_lazy("glossary : acronym", "SoA"), _("statement of applicability"),
        _("The list of the controls of ISO 27001 with, for each one, whether it applies to you and why."),
    ),
    Acronym(
        "tlp", pgettext_lazy("glossary : acronym", "TLP"), _("Traffic Light Protocol"),
        _("A colour code saying how far a piece of information may be shared, from RED (the people named only) to CLEAR (anyone)."),
    ),
    Acronym(
        "ebios_rm", pgettext_lazy("glossary : acronym", "EBIOS RM"), _("EBIOS Risk Manager"),
        _("The risk assessment method of ANSSI, the French cybersecurity agency. It runs in five workshops, from what you protect to the measures you decide."),
        proper=True,
    ),
    Acronym(
        "sr_ov", pgettext_lazy("glossary : acronym", "SR/OV"), _("risk source, targeted objective"),
        _("In EBIOS RM, who could attack you and what they would be after."),
    ),
    Acronym(
        "pacs", pgettext_lazy("glossary : acronym", "PACS"), _("continuous security improvement plan"),
        _("In EBIOS RM, the measures decided at the end of the study, with their owner and their deadline."),
    ),
    Acronym(
        "gdpr", pgettext_lazy("glossary : acronym", "GDPR"), _("General Data Protection Regulation"),
        _("The European law on personal data : what may be done with it, and what must be reported when it leaks."),
        proper=True,
    ),
    Acronym(
        "dpo", pgettext_lazy("glossary : acronym", "DPO"), _("data protection officer"),
        _("The person who watches over the use of personal data in the organisation."),
    ),
    Acronym(
        "nis2", pgettext_lazy("glossary : acronym", "NIS2"), _("directive on the security of network and information systems"),
        _("The European directive that asks the organisations it names to manage their risks and to report serious incidents."),
        proper=True,
    ),
    Acronym(
        "csirt", pgettext_lazy("glossary : acronym", "CERT / CSIRT"), _("computer security incident response team"),
        _("A team that helps handle incidents; each country has a national one, which some incidents must be reported to."),
    ),
    Acronym(
        "soc", pgettext_lazy("glossary : acronym", "SOC"), _("security operations centre"),
        _("The team that watches the systems to spot attacks."),
    ),
    Acronym(
        "siem", pgettext_lazy("glossary : acronym", "SIEM"), _("security information and event management"),
        _("The tool that gathers the logs of the systems and raises an alert on what looks wrong."),
    ),
    Acronym(
        "nda", pgettext_lazy("glossary : acronym", "NDA"), _("non-disclosure agreement"),
        _("A contract by which the reader of your documents promises to keep them to themselves."),
    ),
    Acronym(
        "grc", pgettext_lazy("glossary : acronym", "GRC"), _("governance, risk and compliance"),
        _("The work this application supports : deciding who answers for what, managing risks and meeting requirements."),
    ),
    Acronym(
        "mcp", pgettext_lazy("glossary : acronym", "MCP"), _("Model Context Protocol"),
        _("How an AI assistant connects to this application to read and update records, with your permissions and nothing more."),
    ),
    Acronym(
        "iso_27001", pgettext_lazy("glossary : acronym", "ISO 27001"), _("international standard for information security management"),
        _("The standard that says how to run an ISMS. An organisation can be certified against it."),
        proper=True,
    ),
    Acronym(
        "iso_27005", pgettext_lazy("glossary : acronym", "ISO 27005"), _("international standard for information security risk management"),
        _("The standard that says how to assess and treat security risks."),
        proper=True,
    ),
    Acronym(
        "anssi", pgettext_lazy("glossary : acronym", "ANSSI"), _("French national cybersecurity agency"),
        _("The French authority for the security of information systems, which publishes the EBIOS RM method."),
        proper=True,
    ),
    Acronym(
        "mitre_attack", pgettext_lazy("glossary : acronym", "MITRE ATT&CK"), _("catalogue of attack techniques"),
        _("A public catalogue of the techniques attackers use, kept by the MITRE organisation."),
        proper=True,
    ),
)


def fold(text):
    """``text`` without case nor accents, to compare what a reader types."""
    text = unicodedata.normalize("NFKD", str(text).casefold())
    return "".join(char for char in text if not unicodedata.combining(char))


def other_names(term):
    """The other names of ``term``, as a list (empty when it has none)."""
    return [name.strip() for name in str(term.also).split(",") if name.strip()] if term.also else []


def _term_row(term):
    return {
        "key": term.key,
        "name": str(term.name),
        "definition": str(term.definition),
        "also": other_names(term),
        "url_name": term.url_name,
    }


def _acronym_row(acronym):
    return {
        "key": acronym.key,
        "letters": str(acronym.letters),
        "words": str(acronym.words),
        "definition": str(acronym.definition),
        "proper": acronym.proper,
    }


def _matches(needle, *texts):
    return any(needle in fold(text) for text in texts)


def terms(query="", *, deep=True):
    """The terms in the language in use, sorted by name.

    ``query`` keeps the terms whose name or other names hold it and, when
    ``deep``, those whose definition does : the page searches everything, the
    palette answers a word with the things that bear it.
    """
    rows = [_term_row(term) for term in TERMS]
    needle = fold(query.strip()) if query else ""
    if needle:
        rows = [
            row for row in rows
            if _matches(needle, row["name"], *row["also"]) or (deep and _matches(needle, row["definition"]))
        ]
    return sorted(rows, key=lambda row: fold(row["name"]))


def acronyms(query="", *, deep=True):
    """The acronyms in the language in use, sorted by their letters."""
    rows = [_acronym_row(acronym) for acronym in ACRONYMS]
    needle = fold(query.strip()) if query else ""
    if needle:
        rows = [
            row for row in rows
            if _matches(needle, row["letters"], row["words"]) or (deep and _matches(needle, row["definition"]))
        ]
    return sorted(rows, key=lambda row: fold(row["letters"]))


def known_acronyms():
    """Every acronym the glossary explains, in the language in use, upper case.

    "EBIOS RM" also answers for "EBIOS" and "RM", "SR/OV" for "SR" and "OV".
    """
    known = set()
    for acronym in ACRONYMS:
        letters = str(acronym.letters).upper()
        known.add(letters)
        known.update(part for part in letters.replace("/", " ").replace("&", " ").split() if part)
    return known


def unexplained_acronyms(text):
    """The acronyms ``text`` uses without saying what they mean, sorted.

    For a text a newcomer reads on its own (the help of a page) : an acronym
    of the glossary must come with its words, every one of them, unless it is
    a proper name; any other acronym must be an everyday word
    (``core.usability.EVERYDAY_ACRONYMS``). Checked in the language in use.
    """
    import re

    from core.usability import EVERYDAY_ACRONYMS

    folded = fold(text)
    explained, proper = {}, set()
    for acronym in ACRONYMS:
        letters = str(acronym.letters).upper()
        parts = {letters, *(part for part in re.split(r"[\s/&]+", letters) if part)}
        if acronym.proper:
            proper |= parts
            continue
        words = [word for word in re.findall(r"\w+", fold(str(acronym.words))) if len(word) > 3]
        for part in parts:
            explained[part] = words
    missing = set()
    for token in set(re.findall(r"\b[A-Z][A-Z0-9]{1,7}\b", str(text))):
        if token in proper or token in EVERYDAY_ACRONYMS or token.isdigit():
            continue
        words = explained.get(token)
        if words is None or not all(word in folded for word in words):
            missing.add(token)
    return sorted(missing)


def as_payload(query=""):
    """The glossary as plain data, for the REST endpoint and the MCP tool."""
    from django.urls import NoReverseMatch, reverse

    def link(url_name):
        try:
            return reverse(url_name) if url_name else None
        except NoReverseMatch:
            return None

    return {
        "terms": [
            {"key": row["key"], "name": row["name"], "definition": row["definition"],
             "also_called": row["also"], "url": link(row["url_name"])}
            for row in terms(query)
        ],
        "acronyms": [
            {"key": row["key"], "acronym": row["letters"], "meaning": row["words"], "definition": row["definition"]}
            for row in acronyms(query)
        ],
    }
