"""Dashboard widget registry - single source of truth for the configurable home dashboard.

The home dashboard is an Apple-style grid of widgets. Each widget is declared
once here (id, title, icon, template partial, allowed sizes and a default
placement). A user's personal arrangement is stored as a small JSON list on
``User.dashboard_layout`` (order + per-widget size + visibility); it is merged
with this registry at render time by :func:`resolve_layout`, so newly shipped
widgets appear automatically and removed ones drop out without data migrations.

Sizes map to a 12-column grid:

====  =========  ===========
Size  Columns    Meaning
====  =========  ===========
S     3          1/4 width (right-rail widgets)
M     6          1/2 width
L     9          3/4 width
XL    12         Full width
====  =========  ===========
"""

from __future__ import annotations

from dataclasses import dataclass

from django.utils.translation import gettext_lazy as _

# Column span (out of 12) for each widget size on the dashboard grid.
WIDGET_SIZE_SPANS = {"S": 3, "M": 6, "L": 9, "XL": 12}

# Human labels for the size picker shown on each widget in edit mode.
WIDGET_SIZE_LABELS = {
    "S": _("Small - 1/4"),
    "M": _("Medium - 1/2"),
    "L": _("Large - 3/4"),
    "XL": _("Full width"),
}

# The two dashboard zones: the main area (normal width, below the title) and a
# dedicated side rail shown in the right-hand gutter on large screens, which
# drops below the main area on smaller screens. Rail widgets render at the rail
# width (their size is ignored while in the rail).
ZONE_MAIN = "main"
ZONE_RAIL = "rail"
ZONES = (ZONE_MAIN, ZONE_RAIL)

# Widget categories, used to group the "Add a widget" gallery.
CATEGORY_COMPLIANCE = _("Compliance")
CATEGORY_RISKS = _("Risks")
CATEGORY_GOVERNANCE = _("Governance")
CATEGORY_ACTIVITY = _("Activity")


@dataclass(frozen=True)
class DashboardWidget:
    """A single dashboard widget definition."""

    id: str
    title: object  # lazy translatable
    icon: str  # Bootstrap Icons name, without the "bi-" prefix
    template: str  # partial under templates/dashboard/widgets/
    category: object
    sizes: tuple[str, ...]  # allowed sizes, in ascending order
    default_size: str
    default_order: int
    default_visible: bool = True
    default_zone: str = ZONE_MAIN  # "main" or "rail"
    description: object = ""

    def span(self, size: str) -> int:
        return WIDGET_SIZE_SPANS.get(size, WIDGET_SIZE_SPANS[self.default_size])


# Ordered registry. ``default_order`` defines the out-of-the-box arrangement;
# the right-rail widgets (S) are interleaved so a fresh dashboard already shows
# the 3/4 + 1/4 split.
DASHBOARD_WIDGETS: list[DashboardWidget] = [
    DashboardWidget(
        id="overall_compliance",
        title=_("Overall compliance"),
        icon="speedometer2",
        template="dashboard/widgets/overall_compliance.html",
        category=CATEGORY_COMPLIANCE,
        sizes=("L", "XL"),
        default_size="XL",
        default_order=10,
        description=_("Average compliance across all active frameworks, with the target."),
    ),
    DashboardWidget(
        id="indicators",
        title=_("Key indicators"),
        icon="graph-up",
        template="dashboard/widgets/indicators.html",
        category=CATEGORY_GOVERNANCE,
        sizes=("XL",),
        default_size="XL",
        default_order=20,
        description=_("Your pinned KPI cards with trend sparklines."),
    ),
    DashboardWidget(
        id="compliance_by_framework",
        title=_("Compliance by framework"),
        icon="journal-bookmark",
        template="dashboard/widgets/compliance_by_framework.html",
        category=CATEGORY_COMPLIANCE,
        sizes=("S", "M", "L"),
        default_size="L",
        default_order=30,
        description=_("Per-framework compliance breakdown."),
    ),
    DashboardWidget(
        id="upcoming_deadlines",
        title=_("Upcoming deadlines"),
        icon="calendar-event",
        template="dashboard/widgets/upcoming_deadlines.html",
        category=CATEGORY_ACTIVITY,
        sizes=("S", "M"),
        default_size="S",
        default_order=40,
        default_zone=ZONE_RAIL,
        description=_("Reviews, audits and target dates in the next 30 days. Designed for the right rail."),
    ),
    DashboardWidget(
        id="active_objectives",
        title=_("Active objectives"),
        icon="trophy",
        template="dashboard/widgets/active_objectives.html",
        category=CATEGORY_GOVERNANCE,
        sizes=("S", "M", "L"),
        default_size="M",
        default_order=50,
        description=_("Progress of objectives in play."),
    ),
    DashboardWidget(
        id="priority_risks",
        title=_("Priority risks"),
        icon="fire",
        template="dashboard/widgets/priority_risks.html",
        category=CATEGORY_RISKS,
        sizes=("S", "M"),
        default_size="S",
        default_order=60,
        default_zone=ZONE_RAIL,
        description=_("Top untreated risks by residual level. Designed for the right rail."),
    ),
    DashboardWidget(
        id="risk_treatment_flow",
        title=_("Risk treatment flow"),
        icon="diagram-3",
        template="dashboard/widgets/risk_treatment_flow.html",
        category=CATEGORY_RISKS,
        sizes=("M", "L", "XL"),
        default_size="XL",
        default_order=70,
        description=_("How treatment moves risks from their current to their residual level."),
    ),
    DashboardWidget(
        id="risk_matrices",
        title=_("Risk matrices"),
        icon="grid-3x3",
        template="dashboard/widgets/risk_matrices.html",
        category=CATEGORY_RISKS,
        sizes=("L", "XL"),
        default_size="XL",
        default_order=80,
        description=_("Probability x impact heatmaps, current and residual."),
    ),
    DashboardWidget(
        id="today_actions",
        title=_("Today's actions"),
        icon="list-check",
        template="dashboard/widgets/today_actions.html",
        category=CATEGORY_ACTIVITY,
        sizes=("M", "L", "XL"),
        default_size="L",
        default_order=90,
        default_visible=False,
        description=_("A prioritized to-do list built from the current state of your ISMS."),
    ),
]

WIDGETS_BY_ID: dict[str, DashboardWidget] = {w.id: w for w in DASHBOARD_WIDGETS}

# Registry order, used whenever we need a stable canonical ordering.
_ORDERED = sorted(DASHBOARD_WIDGETS, key=lambda w: w.default_order)


def default_layout() -> list[dict]:
    """The out-of-the-box layout for a user who never customised their dashboard."""
    return [
        {"id": w.id, "size": w.default_size, "visible": w.default_visible, "zone": w.default_zone}
        for w in _ORDERED
    ]


def _clamp_size(widget: DashboardWidget, size) -> str:
    return size if size in widget.sizes else widget.default_size


def _clamp_zone(widget: DashboardWidget, zone) -> str:
    return zone if zone in ZONES else widget.default_zone


def resolve_layout(stored) -> list[dict]:
    """Merge a stored per-user layout with the registry.

    Keeps known entries in their saved order with sizes clamped to the widget's
    allowed set, drops unknown / duplicate ids, then appends any registry widget
    the user has never seen (using its defaults). The result always covers every
    registered widget exactly once.
    """
    resolved: list[dict] = []
    seen: set[str] = set()
    for entry in stored or []:
        if not isinstance(entry, dict):
            continue
        wid = entry.get("id")
        widget = WIDGETS_BY_ID.get(wid)
        if widget is None or wid in seen:
            continue
        seen.add(wid)
        resolved.append({
            "id": wid,
            "size": _clamp_size(widget, entry.get("size")),
            "visible": bool(entry.get("visible", True)),
            "zone": _clamp_zone(widget, entry.get("zone")),
        })
    for widget in _ORDERED:
        if widget.id not in seen:
            resolved.append({
                "id": widget.id,
                "size": widget.default_size,
                "visible": widget.default_visible,
                "zone": widget.default_zone,
            })
    return resolved


def sanitize_layout(payload) -> list[dict]:
    """Validate a layout posted by the client into a storable structure.

    Reuses :func:`resolve_layout` so the saved value is always complete and
    well-formed regardless of what the client sent.
    """
    return resolve_layout(payload)
