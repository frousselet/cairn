# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""The navigation of the application, declared once.

``MENU`` is the sidebar : a short list of sections, each holding the pages of
one area of work. Everything that shows where a page sits is derived from it :

- the sidebar itself (``{% sidebar_menu %}``, ``includes/sidebar_menu.html``);
- the breadcrumb of every list and detail page (``NAV_TREE``, read by
  ``{% page_header nav="<url name>" %}``);
- the view switcher of an entry that has several views (``nav_views``).

Two levels, on purpose. A section opens on its pages; there is no group inside
a section. What used to be a third level is either a page of the section, or
several *views* of one entry : the indicators are one entry whose page switches
between organizational and technical, not a folder of two.

Reference data (the catalogs and types the registers draw on, set up once and
then rarely opened) has a section of its own, so that the sections people work
in every day only list what they work on.

Labels are plain English strings, translated at render time with ``gettext``.
Add the French translation of a new label to ``locale/fr/LC_MESSAGES/django.po``.
"""

from dataclasses import dataclass
from functools import lru_cache


@dataclass(frozen=True)
class NavView:
    """One view of a menu entry that has several (a list among sibling lists)."""

    label: str
    url_name: str
    # Shown only to a user holding this permission. ``None`` : the permission
    # the page itself requires (see ``required_permissions``).
    perm: str | None = None
    # Shown only when this Django setting is true.
    setting: str | None = None


@dataclass(frozen=True)
class NavItem:
    """One entry of a section : a page, or several views of one subject."""

    label: str
    url_name: str = ""
    perm: str | None = None
    setting: str | None = None
    # Sibling views. The entry links to the first one the user may open, and
    # each of their pages shows a switcher between them.
    views: tuple[NavView, ...] = ()
    # Other URL names whose breadcrumb is this entry's (a detail page that
    # declares itself, a second entry point to the same register).
    aliases: tuple[str, ...] = ()
    # URL prefixes of pages that belong to the entry without a URL of their
    # own under it : the rows of an EBIOS RM study are edited under
    # /risks/ebios/, not under /risks/assessments/. The sidebar marks the
    # entry current on them.
    prefixes: tuple[str, ...] = ()
    # False : the entry gives pages their breadcrumb but has no line in the
    # sidebar (it is reached from elsewhere, e.g. the user menu).
    in_menu: bool = True
    # The entry is labelled with this template context variable instead of
    # ``label`` (the assistant's name is configurable).
    label_context: str = ""


@dataclass(frozen=True)
class NavSection:
    key: str
    label: str
    icon: str
    items: tuple[NavItem, ...]
    # Shown only to a user holding a permission of this module.
    module: str | None = None


MENU: tuple[NavSection, ...] = (
    NavSection("governance", "Governance", "diagram-3", (
        NavItem("Scopes", "context:scope-list"),
        NavItem("Issues", "context:issue-list"),
        # Their feedback is a view of the same entry : a register of its own,
        # one menu line (a longer section pushed its last entries under the
        # pinned user card of a laptop screen).
        NavItem("Stakeholders", prefixes=("/context/expectations/",), views=(
            NavView("Stakeholders", "context:stakeholder-list"),
            NavView("Stakeholder feedback", "context:feedback-list"),
        )),
        NavItem("Objectives", "context:objective-list"),
        NavItem("SWOT analyses", "context:swot-list"),
        NavItem("Roles", "context:role-list"),
        NavItem("Activities", "context:activity-list"),
        NavItem("Indicators", prefixes=("/context/indicators/",), views=(
            NavView("Organizational", "context:indicator-organizational-list"),
            NavView("Technical", "context:indicator-technical-list"),
        )),
        NavItem("Management reviews", "reports:management-review-list"),
        NavItem("Reports", "reports:report-list"),
    )),
    NavSection("assets", "Assets and suppliers", "box-seam", (
        NavItem("Essential assets", "assets:essential-asset-list"),
        NavItem("Support assets", "assets:support-asset-list"),
        NavItem("Sites", "assets:site-list"),
        NavItem("Suppliers", "assets:supplier-list", prefixes=(
            "/assets/supplier-contacts/", "/assets/supplier-subprocessors/", "/assets/supplier-requirements/",
        )),
        NavItem("Contracts", "assets:contract-list"),
        NavItem("Certificates", "assets:certificate-list"),
        NavItem("Dependencies", views=(
            NavView("Asset dependencies", "assets:dependency-list"),
            NavView("Supplier dependencies", "assets:supplier-dependency-list"),
            NavView("Site–asset dependencies", "assets:site-asset-dependency-list"),
            NavView("Site–supplier dependencies", "assets:site-supplier-dependency-list"),
            NavView("Dependency graph", "assets:dependency-graph"),
        )),
    )),
    NavSection("risks", "Risk management", "shield-exclamation", (
        NavItem("Assessments", "risks:assessment-list", prefixes=("/risks/ebios/", "/risks/iso27005/")),
        NavItem("Risks", "risks:risk-list"),
        NavItem("Treatment plans", "risks:treatment-plan-list", prefixes=("/risks/treatment-actions/",)),
        NavItem("Acceptances", "risks:acceptance-list"),
        NavItem("ISO 27005 analyses", "risks:iso27005-list", in_menu=False),
    )),
    NavSection("compliance", "Compliance", "patch-check", (
        NavItem("Frameworks", "compliance:framework-list"),
        NavItem("Requirements", "compliance:requirement-list"),
        NavItem("Audits & compliance", "compliance:assessment-list"),
        NavItem("Nonconformities", "compliance:finding-list", aliases=("compliance:finding-detail",)),
        NavItem("Action plans", "compliance:action-plan-list"),
        NavItem("Controls", "controls:control-list"),
        NavItem("Control tests", "controls:controltest-list"),
        NavItem("Documents", "documents:policy-list", prefixes=("/documents/versions/",)),
        NavItem("Acknowledgement campaigns", "documents:campaign-list", prefixes=("/documents/acknowledgements/",)),
        NavItem("To acknowledge", "documents:acknowledge-list", in_menu=False),
    )),
    NavSection("incidents", "Incidents", "fire", (
        NavItem("Incidents", "incidents:incident-list", aliases=("incidents:incident-detail",)),
        NavItem("Security events", "incidents:event-list", aliases=("incidents:event-detail",)),
        NavItem("Notification obligations", "incidents:notification-list",
                aliases=("incidents:notification-detail",)),
        NavItem("Response plans", "incidents:response-plan-list",
                aliases=("incidents:response-plan-detail",)),
    )),
    NavSection("reference", "Reference data", "collection", (
        NavItem("Asset groups", "assets:group-list"),
        NavItem("Supplier types", "assets:supplier-type-list", prefixes=("/assets/supplier-type-requirements/",)),
        NavItem("Risk criteria", "risks:criteria-list"),
        NavItem("Threats", "risks:threat-list"),
        NavItem("Vulnerabilities", "risks:vulnerability-list"),
        NavItem("Requirement mappings", "compliance:mapping-list"),
        NavItem("Reporting authorities", "incidents:reporting-authority-list",
                aliases=("incidents:reporting-authority-detail",)),
        NavItem("Obligation templates", "incidents:obligation-template-list",
                aliases=("incidents:obligation-template-detail",)),
    )),
    NavSection("administration", "Administration", "gear", (
        NavItem("Company", "accounts:company-settings", perm="system.config.read"),
        NavItem("Users", "accounts:user-list", perm="system.users.read"),
        NavItem("Groups", "accounts:group-list", perm="system.groups.read"),
        NavItem("Permissions", "accounts:permission-list", perm="system.groups.read"),
        NavItem("Tags", "context:tag-list"),
        NavItem("Lifecycles", "core:lifecycle-list", perm="system.config.read",
                aliases=("core:lifecycle-edit",)),
        NavItem("Agent skills", "mcp_skills:skill-list", perm="system.mcp_skill.read",
                aliases=("mcp_skills:skill-detail",)),
        NavItem("Calendar subscriptions", "accounts:calendar-subscription-list", perm="system.users.read"),
        NavItem("Trust Center", "trust_center_manage:settings", perm="trust_center.settings.read",
                aliases=("trust_center_manage:hub",), prefixes=("/trust-center/manage/",)),
        NavItem("Document requests", "trust_center_manage:request-list", in_menu=False),
        NavItem("Ask Cairn", label_context="ASSISTANT_NAME", views=(
            NavView("Semantic index", "assistant:semantic-index", perm="system.config.read",
                    setting="AI_ASSISTANT_ENABLED"),
            NavView("Feedback", "assistant:feedback-list", perm="system.assistant_feedback.read"),
        )),
        NavItem("Access log", "accounts:access-log-list", perm="system.audit_trail.read"),
        NavItem("Action log", "accounts:action-log-list", perm="system.audit_trail.read"),
    ), module="system"),
)


def _build_tree():
    """``url name -> (section, group | None, leaf label)`` for the breadcrumbs.

    ``group`` is the entry's label when the page is one of its views, ``None``
    otherwise : the breadcrumb reads *Governance > Indicators > Technical* and
    *Governance > Scopes*.
    """
    tree = {}
    for section in MENU:
        for item in section.items:
            if item.views:
                for view in item.views:
                    tree[view.url_name] = (section.label, item.label, view.label)
            else:
                tree[item.url_name] = (section.label, None, item.label)
            for alias in item.aliases:
                tree[alias] = (section.label, None, item.label)
    return tree


# leaf URL name -> (section, group | None, leaf menu label)
NAV_TREE = _build_tree()


@lru_cache(maxsize=None)
def required_permissions(url_name):
    """The permissions the page behind ``url_name`` asks for, as a tuple.

    Read from the view itself (``permission_required``), so a menu entry is
    shown exactly to the users the page lets in : an entry that only leads to
    a refusal is not offered. A page with no declared permission is open.
    """
    from django.urls import NoReverseMatch, Resolver404, resolve, reverse

    try:
        match = resolve(reverse(url_name))
    except (NoReverseMatch, Resolver404):
        return ()
    view_class = getattr(match.func, "view_class", None)
    required = getattr(view_class, "permission_required", None)
    if not required:
        return ()
    return (required,) if isinstance(required, str) else tuple(required)


def _allowed(user, url_name, perm, setting):
    from django.conf import settings as django_settings

    if setting and not getattr(django_settings, setting, False):
        return False
    codenames = (perm,) if perm else required_permissions(url_name)
    return all(user.has_perm(codename) for codename in codenames)


def nav_views(url_name, user):
    """The views the switcher of ``url_name``'s page offers to ``user``.

    ``[(label, url name), ...]``, empty when the page is not one view among
    several or when the user may open only one of them.
    """
    for section in MENU:
        for item in section.items:
            if any(view.url_name == url_name for view in item.views):
                visible = [
                    (view.label, view.url_name)
                    for view in item.views
                    if _allowed(user, view.url_name, view.perm, view.setting)
                ]
                return visible if len(visible) > 1 else []
    return []


def visible_menu(user, context=None):
    """The sidebar for ``user`` : sections and entries they may open.

    Returns ``[{"key", "label", "icon", "items": [{"label", "url", "paths"}]}]``
    with URLs resolved. ``paths`` lists every URL an entry stands for (its
    views), so the sidebar can mark it current on any of them. A section with
    no visible entry is left out.
    """
    from django.urls import NoReverseMatch, reverse
    from django.utils.translation import gettext

    def url_of(name):
        try:
            return reverse(name)
        except NoReverseMatch:
            return None

    sections = []
    for section in MENU:
        if section.module and not user.has_module_perms(section.module):
            continue
        items = []
        for item in section.items:
            if not item.in_menu:
                continue
            if item.views:
                targets = [
                    url_of(view.url_name)
                    for view in item.views
                    if _allowed(user, view.url_name, view.perm, view.setting)
                ]
                targets = [url for url in targets if url]
            else:
                if not _allowed(user, item.url_name, item.perm, item.setting):
                    continue
                targets = [url for url in [url_of(item.url_name)] if url]
            if not targets:
                continue
            label = (context or {}).get(item.label_context) if item.label_context else None
            items.append({
                "label": label or gettext(item.label),
                "url": targets[0],
                "paths": " ".join([*targets, *item.prefixes]),
            })
        if items:
            sections.append({
                "key": section.key,
                "label": gettext(section.label),
                "icon": section.icon,
                "items": items,
            })
    return sections
