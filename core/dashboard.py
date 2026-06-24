"""Dashboard widget registry - single source of truth for the configurable home dashboard.

The home dashboard is an Apple-style grid of widgets. Each widget is declared
once here (id, title, icon, template partial, allowed sizes and a default
placement). A user's personal arrangement is stored as a small JSON list on
``User.dashboard_layout`` (order + per-widget size + visibility); it is merged
with this registry at render time by :func:`resolve_layout`, so newly shipped
widgets appear automatically and removed ones drop out without data migrations.

Widget sizes are **two-dimensional** ``"WxH"`` tokens (width x height), not a
single width step. The main area is a fixed-cell grid:

- **Width** ``W`` is a number of quarter-columns (1..4) on the 12-column grid.
  ``W`` columns of the layout span ``W * 3`` of the 12 grid columns:

  ====  =======  ===========
  W     Columns  Meaning
  ====  =======  ===========
  1     3        1/4 width
  2     6        1/2 width
  3     9        3/4 width
  4     12       Full width
  ====  =======  ===========

- **Height** ``H`` is a number of fixed row units (1..4). Each unit is a fixed
  pixel height (``--dash-row`` in the template), so a widget occupies an exact
  ``W x H`` tile and its content scrolls inside if it overflows.

So ``"2x1"`` is a half-width, one-row tile and ``"4x2"`` is a full-width,
two-row tile. The rail ignores width and height (rail widgets stack at the rail
width with content height); the token only drives the main-area grid.
"""

from __future__ import annotations

from dataclasses import dataclass

from django.utils.translation import gettext_lazy as _, pgettext_lazy

# Geometry of the main-area grid.
GRID_COLUMNS = 12  # total CSS grid columns
WIDTH_UNIT_COLUMNS = 3  # grid columns per width unit, so W in 1..4 maps to 3..12
MAX_WIDTH = GRID_COLUMNS // WIDTH_UNIT_COLUMNS  # 4
MAX_HEIGHT = 4  # tallest tile, in fixed row units

# Legacy single-letter sizes (pre-x*y) mapped to their width unit, so a layout
# saved with the old S/M/L/XL tokens keeps its width on the next resolve.
_LEGACY_WIDTHS = {"S": 1, "M": 2, "L": 3, "XL": 4}


def parse_size(token) -> tuple[int, int] | None:
    """Parse a ``"WxH"`` size token into ``(width, height)`` unit counts.

    Returns ``None`` for anything that is not a well-formed token within the
    supported ``1..MAX_WIDTH`` x ``1..MAX_HEIGHT`` range.
    """
    if not isinstance(token, str):
        return None
    parts = token.lower().split("x")
    if len(parts) != 2:
        return None
    try:
        w, h = int(parts[0]), int(parts[1])
    except (TypeError, ValueError):
        return None
    if 1 <= w <= MAX_WIDTH and 1 <= h <= MAX_HEIGHT:
        return (w, h)
    return None


def size_label(token: str) -> str:
    """Human label for the size picker, e.g. ``"2 x 1"`` (width x height)."""
    dims = parse_size(token)
    if dims is None:
        return token
    return f"{dims[0]} × {dims[1]}"


# ── Per-widget parameters ───────────────────────────────────
# Most widgets are singletons with no parameters. Parameterized widgets (e.g.
# the indicator widget) carry a small ``params`` dict per instance, sanitised on
# resolve so a malformed client payload can never corrupt the stored layout.


def _sanitize_indicator_params(raw) -> dict:
    """Normalise the indicator widget's params: ``{indicator, show_chart}``.

    ``indicator`` is the chosen indicator's id (a string, empty when the widget
    is not configured yet); ``show_chart`` toggles the sparkline.
    """
    raw = raw if isinstance(raw, dict) else {}
    indicator = raw.get("indicator")
    return {
        "indicator": str(indicator) if indicator else "",
        "show_chart": bool(raw.get("show_chart", False)),
    }


# Sort modes for the progress-bar list widgets (compliance by framework, active
# objectives). "manual" uses the per-widget ``order`` (an ordered list of item
# ids); the others sort by the row value or name. Applied client-side.
SORT_MODES = ("default", "value_desc", "value_asc", "name", "manual")


def _sanitize_target_params(raw) -> dict:
    """Normalise the overall-compliance widget's params: ``{show_target, target}``.

    ``show_target`` toggles the target marker; ``target`` is its value (0..100).
    """
    raw = raw if isinstance(raw, dict) else {}
    try:
        target = int(raw.get("target", 80))
    except (TypeError, ValueError):
        target = 80
    return {
        "show_target": bool(raw.get("show_target", True)),
        "target": max(0, min(100, target)),
    }


def _sanitize_sort_params(raw) -> dict:
    """Normalise a sortable list widget's params: ``{sort, order}``."""
    raw = raw if isinstance(raw, dict) else {}
    sort = raw.get("sort")
    order = raw.get("order")
    return {
        "sort": sort if sort in SORT_MODES else "default",
        "order": [str(x) for x in order] if isinstance(order, list) else [],
    }


# Number of list rows a progress-bar widget shows for a given tile height (1..4).
# The shown rows divide the tile height evenly, so a taller tile shows more rows
# without scroll or empty space; the client reads this to slice the sorted list.
PROGRESS_ROW_COUNTS = {1: 2, 2: 5, 3: 8, 4: 11}


# Dashboard zones: the main area (normal width, below the title) and a dedicated
# side rail shown in the right-hand gutter on large screens. The rail is split
# into two sub-zones, top and bottom: on wide screens they stack together in the
# right gutter, and when the layout collapses the top sub-zone moves *above* the
# main area and the bottom sub-zone *below* it. Rail widgets render at the rail
# width with content height (their WxH size is ignored while in the rail).
ZONE_MAIN = "main"
ZONE_RAIL_TOP = "rail_top"
ZONE_RAIL_BOTTOM = "rail_bottom"
ZONES = (ZONE_MAIN, ZONE_RAIL_TOP, ZONE_RAIL_BOTTOM)
# Legacy single rail zone, now split into top/bottom: migrate old layouts to the
# top sub-zone (their previous "stacks above the main area" behaviour).
_LEGACY_ZONES = {"rail": ZONE_RAIL_TOP}

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
    sizes: tuple[str, ...]  # allowed "WxH" tokens, ascending by (width, height)
    default_size: str
    default_order: int
    default_visible: bool = True
    default_zone: str = ZONE_MAIN  # "main", "rail_top" or "rail_bottom"
    description: object = ""
    # A "multiple" widget can be placed several times, each instance carrying its
    # own params; it is added on demand from the gallery and never auto-appended.
    # A singleton (default) appears at most once and is auto-appended if missing.
    multiple: bool = False
    # Optional sanitiser for this widget's per-instance params dict.
    param_sanitizer: object = None
    # Which config dialog the edit-mode gear opens ("indicator", "sort" or "" for
    # none). A widget is configurable iff this is set.
    config: str = ""

    @property
    def configurable(self) -> bool:
        return bool(self.config)

    def sanitize_params(self, raw) -> dict:
        return self.param_sanitizer(raw) if self.param_sanitizer else {}

    def default_params(self) -> dict:
        return self.sanitize_params(None)

    def _dims(self, size: str) -> tuple[int, int]:
        return parse_size(size) or parse_size(self.default_size) or (MAX_WIDTH, 1)

    def cols(self, size: str) -> int:
        """Grid-column span (out of 12) for the given size."""
        return self._dims(size)[0] * WIDTH_UNIT_COLUMNS

    def rows(self, size: str) -> int:
        """Grid-row span (fixed row units) for the given size."""
        return self._dims(size)[1]

    def width(self, size: str) -> int:
        """Width unit (1..MAX_WIDTH) for the given size."""
        return self._dims(size)[0]

    def height(self, size: str) -> int:
        """Height unit (1..MAX_HEIGHT) for the given size."""
        return self._dims(size)[1]


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
        sizes=("2x1", "3x1", "4x1"),
        default_size="4x1",
        default_order=10,
        param_sanitizer=_sanitize_target_params,
        config="target",
        description=_("Average compliance across all active frameworks, with the target."),
    ),
    DashboardWidget(
        id="ask_cairn",
        title=pgettext_lazy("dashboard widget title", "Summary"),
        icon="stars",
        template="dashboard/widgets/ask_cairn.html",
        category=CATEGORY_GOVERNANCE,
        sizes=("2x2", "2x3", "3x2", "3x3"),
        default_size="2x2",
        default_order=15,
        default_zone=ZONE_RAIL_TOP,
        description=_("Cairn's briefing of the day's key governance, risk and compliance points."),
    ),
    DashboardWidget(
        id="ongoing_audits",
        title=_("Ongoing audits"),
        icon="clipboard-check",
        template="dashboard/widgets/ongoing_audits.html",
        category=CATEGORY_COMPLIANCE,
        sizes=("1x2", "1x3", "2x2"),
        default_size="1x2",
        default_order=18,
        default_zone=ZONE_RAIL_TOP,
        description=_("Audits running right now (shown only while one is under way)."),
    ),
    DashboardWidget(
        id="indicator",
        title=_("Indicator"),
        icon="graph-up",
        template="dashboard/widgets/indicator.html",
        category=CATEGORY_GOVERNANCE,
        sizes=("1x1",),
        default_size="1x1",
        default_order=20,
        multiple=True,
        param_sanitizer=_sanitize_indicator_params,
        config="indicator",
        description=_("A single KPI indicator with its value, trend and an optional mini-chart."),
    ),
    DashboardWidget(
        id="compliance_by_framework",
        title=_("Frameworks"),
        icon="journal-bookmark",
        template="dashboard/widgets/compliance_by_framework.html",
        category=CATEGORY_COMPLIANCE,
        sizes=("2x2", "2x3", "3x2", "3x3"),
        default_size="3x2",
        default_order=30,
        param_sanitizer=_sanitize_sort_params,
        config="sort",
        description=_("Per-framework compliance breakdown."),
    ),
    DashboardWidget(
        id="upcoming_deadlines",
        title=_("Upcoming deadlines"),
        icon="calendar-event",
        template="dashboard/widgets/upcoming_deadlines.html",
        category=CATEGORY_ACTIVITY,
        sizes=("1x2", "1x3", "2x2"),
        default_size="1x2",
        default_order=40,
        default_zone=ZONE_RAIL_TOP,
        description=_("Reviews, audits and target dates in the next 30 days. Designed for the right rail."),
    ),
    DashboardWidget(
        id="active_objectives",
        title=_("Objectives"),
        icon="trophy",
        template="dashboard/widgets/active_objectives.html",
        category=CATEGORY_GOVERNANCE,
        sizes=("1x2", "2x2", "2x3", "3x2"),
        default_size="2x2",
        default_order=50,
        param_sanitizer=_sanitize_sort_params,
        config="sort",
        description=_("Progress of objectives in play."),
    ),
    DashboardWidget(
        id="priority_risks",
        title=_("Priority risks"),
        icon="fire",
        template="dashboard/widgets/priority_risks.html",
        category=CATEGORY_RISKS,
        sizes=("1x2", "1x3", "2x2"),
        default_size="1x2",
        default_order=60,
        default_zone=ZONE_RAIL_TOP,
        description=_("Top untreated risks by residual level. Designed for the right rail."),
    ),
    DashboardWidget(
        id="risk_treatment_flow",
        title=_("Risk treatment flow"),
        icon="diagram-3",
        template="dashboard/widgets/risk_treatment_flow.html",
        category=CATEGORY_RISKS,
        sizes=("2x2", "3x2", "4x2", "4x3"),
        default_size="4x2",
        default_order=70,
        description=_("How treatment moves risks from their current to their residual level."),
    ),
    DashboardWidget(
        id="risk_matrix_current",
        title=pgettext_lazy("risk matrix widget", "Current risks"),
        icon="grid-3x3",
        template="dashboard/widgets/risk_matrix_current.html",
        category=CATEGORY_RISKS,
        sizes=("2x2", "2x3"),
        default_size="2x2",
        default_order=80,
        description=_("Probability x impact heatmap, before treatment."),
    ),
    DashboardWidget(
        id="risk_matrix_residual",
        title=pgettext_lazy("risk matrix widget", "Residual risks"),
        icon="grid-3x3",
        template="dashboard/widgets/risk_matrix_residual.html",
        category=CATEGORY_RISKS,
        sizes=("2x2", "2x3"),
        default_size="2x2",
        default_order=81,
        description=_("Probability x impact heatmap, after treatment."),
    ),
]

WIDGETS_BY_ID: dict[str, DashboardWidget] = {w.id: w for w in DASHBOARD_WIDGETS}

# Registry order, used whenever we need a stable canonical ordering.
_ORDERED = sorted(DASHBOARD_WIDGETS, key=lambda w: w.default_order)


def _default_entry(widget: DashboardWidget) -> dict:
    """A layout entry for a widget placed with its defaults."""
    return {
        "key": widget.id,
        "id": widget.id,
        "size": widget.default_size,
        "visible": widget.default_visible,
        "zone": widget.default_zone,
        "params": widget.default_params(),
    }


def default_layout() -> list[dict]:
    """The out-of-the-box layout for a user who never customised their dashboard.

    Only singleton widgets are placed; ``multiple`` widgets (e.g. indicators)
    start at zero instances and are added on demand from the gallery.
    """
    return [_default_entry(w) for w in _ORDERED if not w.multiple]


def _clamp_size(widget: DashboardWidget, size) -> str:
    """Coerce a stored size into one of the widget's allowed ``"WxH"`` tokens.

    A valid allowed token is kept as-is. A legacy single-letter token (S/M/L/XL)
    is migrated to the allowed token with the same width (preferring the widget
    default's height), so older layouts keep their relative width. Anything else
    falls back to the widget default.
    """
    if size in widget.sizes:
        return size
    legacy_width = _LEGACY_WIDTHS.get(size)
    if legacy_width is not None:
        default_height = widget.height(widget.default_size)
        same_width = [s for s in widget.sizes if widget.width(s) == legacy_width]
        if same_width:
            # Prefer the token whose height matches the widget default, else the
            # first (shortest) allowed token at that width.
            return next(
                (s for s in same_width if widget.height(s) == default_height),
                same_width[0],
            )
    return widget.default_size


def _clamp_zone(widget: DashboardWidget, zone) -> str:
    zone = _LEGACY_ZONES.get(zone, zone)
    return zone if zone in ZONES else widget.default_zone


def resolve_layout(stored) -> list[dict]:
    """Merge a stored per-user layout with the registry.

    Each entry is an instance: ``{key, id, size, visible, zone, params}`` where
    ``id`` is the widget type and ``key`` is a stable per-instance id. Known
    entries are kept in their saved order with sizes/zones clamped and params
    sanitised; unknown ids are dropped. A **singleton** widget appears at most
    once (duplicates dropped) and is auto-appended with its defaults if missing;
    a **multiple** widget keeps every instance (each with a unique key) and is
    never auto-appended.
    """
    resolved: list[dict] = []
    seen_singletons: set[str] = set()
    seen_keys: set[str] = set()
    auto = 0
    for entry in stored or []:
        if not isinstance(entry, dict):
            continue
        wid = entry.get("id")
        widget = WIDGETS_BY_ID.get(wid)
        if widget is None:
            continue
        if widget.multiple:
            key = entry.get("key")
            if not isinstance(key, str) or not key or key in seen_keys:
                key = f"{wid}-{auto}"
                auto += 1
                while key in seen_keys:
                    key = f"{wid}-{auto}"
                    auto += 1
        else:
            if wid in seen_singletons:
                continue
            seen_singletons.add(wid)
            key = wid
        seen_keys.add(key)
        resolved.append({
            "key": key,
            "id": wid,
            "size": _clamp_size(widget, entry.get("size")),
            "visible": bool(entry.get("visible", True)),
            "zone": _clamp_zone(widget, entry.get("zone")),
            "params": widget.sanitize_params(entry.get("params")),
        })
    for widget in _ORDERED:
        if not widget.multiple and widget.id not in seen_singletons:
            resolved.append(_default_entry(widget))
    return resolved


def sanitize_layout(payload) -> list[dict]:
    """Validate a layout posted by the client into a storable structure.

    Reuses :func:`resolve_layout` so the saved value is always complete and
    well-formed regardless of what the client sent.
    """
    return resolve_layout(payload)
