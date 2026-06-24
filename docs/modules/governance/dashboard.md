# Dashboard (configurable widgets)

The home dashboard (`/`) is a personalizable grid of widgets. Each user arranges
their own dashboard - which widgets show, in what order, and at what size - and
the arrangement is persisted per user. The editing experience mirrors the Apple
widget editor: an **Edit** button, a wiggle animation, a dotted placement grid,
drag-to-reorder, per-widget resizing, and an **Add a widget** gallery.

## Layout model

The dashboard has **two zones**: a **main area** (normal width, directly below
the page title) and a dedicated **side rail**. Each widget carries a `zone`
(`main` or `rail`).

- The **main area** is a 12-column CSS grid. Each main widget declares a set of
  allowed sizes; a size maps to a column span:

  | Size | Span | Meaning     |
  | ---- | ---- | ----------- |
  | S    | 3    | 1/4 width   |
  | M    | 6    | 1/2 width   |
  | L    | 9    | 3/4 width   |
  | XL   | 12   | Full width  |

- The **rail** is a vertical stack of widgets. On large screens
  (`min-width: 1600px`) the whole dashboard (page header + both zones) uses more
  of the screen up to a max width, kept centred (the standard container cap is
  lifted - only for the dashboard, via `:has` - and replaced by a wider one so it
  never sprawls on very large screens). The title row and the board share this
  container, so they are always the same width. The rail sits *beside* the main area as
  a comfortably wide column (24rem, 28rem on very wide screens) and the main area
  takes the rest. Below that breakpoint the container keeps its normal width and
  the rail **stacks below** the main area at full width, so the layout never
  breaks on tablets or phones. A widget's size is ignored while it is in the rail
  (rail widgets fill the rail width).

## Widget registry

Widgets are declared once in `core/dashboard.py` (`DASHBOARD_WIDGETS`), the
single source of truth. A `DashboardWidget` carries an `id`, `title`, `icon`
(Bootstrap Icons), the `template` partial (`templates/dashboard/widgets/`), a
`category` (used to group the gallery), the allowed `sizes`, a `default_size`,
a `default_order` and `default_visible`. Adding a widget is a matter of adding
one entry plus its partial; everything else (gallery tile, resize menu, API,
MCP) is derived.

Shipped widgets:

| id | Default | Sizes | Notes |
| -- | ------- | ----- | ----- |
| `overall_compliance` | XL, visible | L, XL | Average compliance + target |
| `indicators` | XL, visible | XL | Pinned KPI cards (own configure modal) |
| `compliance_by_framework` | L, visible | S, M, L | |
| `upcoming_deadlines` | S, visible | S, M | Right-rail; next 30 days |
| `active_objectives` | M, main, visible | S, M, L | |
| `priority_risks` | S, **rail**, visible | S, M | Critical/high, untreated |
| `risk_treatment_flow` | XL, main, visible | M, L, XL | Sankey |
| `risk_matrices` | XL, main, visible | L, XL | Current + residual heatmaps |
| `today_actions` | L, main, hidden | M, L, XL | Prioritized to-do list |

`upcoming_deadlines` and `priority_risks` default to the **rail**; everything
else to the **main** area.

## Persistence and resolution

A user's arrangement is stored on `User.dashboard_layout` (JSON): an ordered
list of `{id, size, visible, zone}` entries. At render time `resolve_layout()`
merges it with the registry: known entries are kept in order (sizes clamped to
the widget's allowed set, zone clamped to `main`/`rail`), unknown/duplicate ids
are dropped, and any widget the user has never seen is appended with its
defaults. This means newly shipped widgets appear automatically and removed ones
disappear with no data migration. Layouts saved before the rail existed simply
gain each widget's default zone on the next resolve.

A visible widget with no data to show (e.g. no frameworks yet) is hidden in view
mode and shown only as a removable placeholder while editing.

## Edit mode

Toggled client-side (no reload). Entering edit mode sets `body.dash-editing`,
which reveals the dotted placement grid (on both zones), the per-widget chrome
(remove button, drag grip, resize menu) and the wiggle animation. Reordering
uses [SortableJS](https://sortablejs.github.io/Sortable/) (lazy-loaded from a
CDN, like ECharts): each zone is its own sortable, sharing a group, so a widget
can be **dragged between the main area and the rail** - its `zone` is updated on
drop. The resize menu is hidden in the rail (rail widgets fill the rail width).
Removing a widget flips it to hidden and surfaces its gallery tile; adding from
the gallery reveals it in its zone. Leaving edit mode persists the layout if
anything changed. The wiggle and zone transitions honour `prefers-reduced-motion`.

## API

- `GET /api/v1/dashboard-layout/` - the resolved layout plus the widget catalogue.
- `PUT /api/v1/dashboard-layout/` - replace the layout (`{"layout": [...]}`); the
  payload is sanitised against the registry.
- `POST /dashboard/layout/` - the web UI save endpoint used by the editor.

## MCP tools

- `get_dashboard_layout` - the current user's layout and the widget catalogue.
- `update_dashboard_layout` - replace the layout (sanitised against the registry).

Both operate on own-data (no extra permission beyond authentication).
