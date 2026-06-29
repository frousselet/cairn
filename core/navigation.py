"""Central navigation hierarchy, mirroring the main sidebar menu.

Single source of truth used by the ``{% page_header %}`` tag to build the
breadcrumb (eyebrow) of list and detail pages so it always reflects the
sidebar tree, e.g. ``Governance > Organization > Stakeholders > STKH-1``.

Each entry is keyed by the leaf's *list* URL name and maps to its menu
ancestry::

    "<namespace>:<entity>-list": (section, group, leaf_label)

``section`` and ``group`` are menu headings with no page of their own, so
they render as plain (non-clickable) crumbs. ``group`` is ``None`` for leaves
that sit directly under a section. ``leaf_label`` is the menu label of the
leaf itself (which may differ from the list page title, e.g. menu "Risks" vs
title "Risk register"); it links to the list on detail pages and is the
current crumb on the list page itself.

Labels are stored as plain English strings and translated at render time with
``gettext`` (they already exist in the catalogs since the sidebar uses them).
"""

# leaf list URL name -> (section, group | None, leaf menu label)
NAV_TREE = {
    # ── Governance ───────────────────────────────────────────────
    "context:scope-list": ("Governance", "Organization", "Scopes"),
    "context:issue-list": ("Governance", "Organization", "Issues"),
    "context:stakeholder-list": ("Governance", "Organization", "Stakeholders"),
    "context:objective-list": ("Governance", "Organization", "Objectives"),
    "context:swot-list": ("Governance", "Organization", "SWOT analyses"),
    "context:role-list": ("Governance", None, "Roles"),
    "context:activity-list": ("Governance", None, "Activities"),
    "context:indicator-organizational-list": ("Governance", "Indicators", "Organizational"),
    "context:indicator-technical-list": ("Governance", "Indicators", "Technical"),
    "reports:report-list": ("Governance", "Strategy", "Reports"),
    "reports:management-review-list": ("Governance", "Strategy", "Management reviews"),
    # ── Assets ───────────────────────────────────────────────────
    "assets:essential-asset-list": ("Assets", "Goods", "Essential assets"),
    "assets:support-asset-list": ("Assets", "Goods", "Support assets"),
    "assets:group-list": ("Assets", "Goods", "Asset groups"),
    "assets:site-list": ("Assets", None, "Sites"),
    "assets:supplier-list": ("Assets", "Suppliers", "Suppliers"),
    "assets:supplier-type-list": ("Assets", "Suppliers", "Supplier types"),
    "assets:contract-list": ("Assets", "Documents", "Contracts"),
    "assets:certificate-list": ("Assets", "Documents", "Certificates"),
    "assets:dependency-list": ("Assets", "Dependencies", "Asset dependencies"),
    "assets:supplier-dependency-list": ("Assets", "Dependencies", "Supplier dependencies"),
    "assets:site-asset-dependency-list": ("Assets", "Dependencies", "Site–asset dependencies"),
    "assets:site-supplier-dependency-list": ("Assets", "Dependencies", "Site–supplier dependencies"),
    "assets:dependency-graph": ("Assets", "Dependencies", "Dependency graph"),
    # ── Risk management ──────────────────────────────────────────
    "risks:assessment-list": ("Risk management", "Assessments", "Assessments"),
    "risks:criteria-list": ("Risk management", "Assessments", "Criteria"),
    "risks:risk-list": ("Risk management", "Register", "Risks"),
    "risks:treatment-plan-list": ("Risk management", "Register", "Treatment plans"),
    "risks:acceptance-list": ("Risk management", "Register", "Acceptances"),
    "risks:iso27005-list": ("Risk management", "Register", "ISO 27005 analyses"),
    "risks:threat-list": ("Risk management", "Catalogs", "Threats"),
    "risks:vulnerability-list": ("Risk management", "Catalogs", "Vulnerabilities"),
    # ── Compliance ───────────────────────────────────────────────
    "compliance:framework-list": ("Compliance", None, "Frameworks"),
    "compliance:requirement-list": ("Compliance", None, "Requirements"),
    "compliance:assessment-list": ("Compliance", None, "Audits & compliance"),
    "compliance:mapping-list": ("Compliance", None, "Mappings"),
    "compliance:action-plan-list": ("Compliance", None, "Action plans"),
    # ── Administration ───────────────────────────────────────────
    "accounts:company-settings": ("Administration", "General", "Company"),
    "context:tag-list": ("Administration", "General", "Tags"),
    "core:versioning-config-list": ("Administration", "General", "Versioning"),
    "accounts:calendar-subscription-list": ("Administration", "General", "Calendar subscriptions"),
    "trust_center_manage:settings": ("Administration", "General", "Trust Center"),
    "trust_center_manage:request-list": ("Administration", "Trust Center", "Document requests"),
    "accounts:user-list": ("Administration", "Access", "Users"),
    "accounts:group-list": ("Administration", "Access", "Groups"),
    "accounts:permission-list": ("Administration", "Access", "Permissions"),
    "assistant:feedback-list": ("Administration", "Ask Cairn", "Feedback"),
    "accounts:access-log-list": ("Administration", "Logs", "Access log"),
    "accounts:action-log-list": ("Administration", "Logs", "Action log"),
}
