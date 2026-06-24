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

- The **main area** is a fixed-cell CSS grid: 12 columns wide with fixed-height
  rows (`grid-auto-rows: var(--dash-row)`, 170px). A widget's size is a
  two-dimensional **`"WxH"` tile token** (width x height), so each main widget
  occupies an exact `W x H` tile and overflowing content scrolls inside it
  (keeping the grid aligned).

  - **Width** `W` (1..4) is a number of quarter-columns; it maps to a
    `grid-column` span of `W * 3` of the 12 columns:

    | W | Span | Meaning     |
    | - | ---- | ----------- |
    | 1 | 3    | 1/4 width   |
    | 2 | 6    | 1/2 width   |
    | 3 | 9    | 3/4 width   |
    | 4 | 12   | Full width  |

  - **Height** `H` (1..4) is a number of fixed row units; it maps directly to a
    `grid-row` span. One row is `--dash-row` tall (170px), so a 2-row tile is
    `2 * 170px + 1.5rem` gap.

  So `2x1` is a half-width, one-row tile and `4x2` is a full-width, two-row
  tile. Below 1200px the main grid collapses to a single content-height column
  (fixed tiles only apply once the 2D grid is active), so nothing is clipped
  when widgets stack on tablets and phones.

- The **rail** is split into two sub-zones - `rail_top` and `rail_bottom`. On
  wide screens (`min-width: 1800px`) the whole dashboard (page header + zones)
  uses more of the screen up to a max width, kept centred (the standard container
  cap is lifted - only for the dashboard, via `:has` - and replaced by a wider one
  so it never sprawls on very large screens). The title row and the board share
  this container, so they are always the same width. The two sub-zones stack
  together in a single column *beside* the main area (the wrap re-forms as a flex
  column; 24rem, 28rem on very wide screens) and the main area takes the rest. The
  threshold accounts for the sidebar plus the rail width, so the main column is
  never cramped. Below that breakpoint the container keeps its normal width and
  the rail wrap becomes `display: contents` so its sub-zones become direct grid
  items: **`rail_top` moves above the main area and `rail_bottom` below it** (each
  ordered around the main column), so the layout never breaks on tablets or
  phones. A widget's `WxH` size is ignored while it is in the rail (rail widgets
  fill the rail width at content height). An empty sub-zone collapses in view mode
  (`:empty`) and reappears as a drop target while editing.
- When they sit *beside* the main area, the two sub-zones share one **sticky**
  wrap: it scrolls up with the page until it clears the sticky page header, then
  stays put while the taller main column keeps scrolling.
- The rail list widgets (`priority_risks`, `upcoming_deadlines`, `ongoing_audits`)
  share one card treatment: airy cards that show the **responsible** (photo +
  name) when the source has one - the risk owner, and per-event the lead assessor
  / action-plan or objective owner for deadlines (resolved JSON-safely via
  `attach_deadline_responsibles`, so the calendar feed stays serialisable) - and
  flow into a **responsive grid** (one column when narrow, several when wide).
- In the **stacked, full-width** rail the `ask_cairn` ("Summary") widget reflows
  into a **banner**: a title header, then the summary in the first column and the
  references filling two columns beside it, kept close to one row tall. It falls
  back to the vertical card on narrow screens and in the beside rail.

## Widget registry

Widgets are declared once in `core/dashboard.py` (`DASHBOARD_WIDGETS`), the
single source of truth. A `DashboardWidget` carries an `id`, `title`, `icon`
(Bootstrap Icons), the `template` partial (`templates/dashboard/widgets/`), a
`category` (used to group the gallery), the allowed `sizes`, a `default_size`,
a `default_order`, `default_visible`, a `multiple` flag and an optional
`param_sanitizer`. Adding a widget is a matter of adding one entry plus its
partial; everything else (gallery tile, resize menu, API, MCP) is derived.

### Instances and parameters

Most widgets are **singletons**: they appear at most once and are auto-placed
with their defaults. A widget with `multiple = True` (currently `indicator`) is
an **instance** widget: it is added on demand from the gallery, can be placed
several times, and each instance carries its own `params` dict (sanitised by the
widget's `param_sanitizer`). The `indicator` widget takes
`params = {indicator: <id>, show_chart: bool}` and is fixed at `1x1`; it renders
one KPI card (value, trend, optional sparkline) via
`build_indicator_slot()` (shared with the legacy pinned strip). Each instance is
configured in edit mode through a **gear** on the widget that opens a shared
dialog (pick the indicator + toggle the chart); the card refreshes in place from
`GET /dashboard/indicator-widget/` without a reload, and the same endpoint backs
the WebSocket live-value refresh.

A widget is **configurable** when it declares a `config` kind (the gear's dialog:
`"indicator"`, `"sort"` or `"target"`); this is independent of `multiple`, so a
singleton can be configurable too. The `overall_compliance` widget uses
`config = "target"` with `params = {show_target, target}`: a dialog toggles the
target marker and sets its value (0..100), applied client-side (the marker and
its label are pure presentation). The progress-bar list widgets (`compliance_by_framework`,
`active_objectives`) use `config = "sort"` with
`params = {sort, order}`: `sort` is one of `default` / `value_desc` /
`value_asc` / `name` / `manual`, and `order` is the per-widget id order used in
`manual` mode (set by dragging the rows in the dialog). Sorting and the row
count are applied **client-side** (`layoutProgressWidget`): rows carry
`data-id` / `data-name` / `data-value`, are sorted per the params, and only the
first **N** are shown - **N depends on the tile height** (`PROGRESS_ROW_COUNTS`,
roughly height x rows), and the shown rows divide the tile height evenly so the
bars stay aligned with no scroll and no empty band. When there are fewer real
rows than N, the remaining slots are filled with **skeleton placeholders** (grey
text rects + a light grey bar) so the layout stays uniformly full. The two
widgets share one row layout (`.fw-bar`), so they look identical.

Shipped widgets:

Sizes are `"WxH"` tile tokens (see *Layout model*).

| id | Default | Sizes | Notes |
| -- | ------- | ----- | ----- |
| `overall_compliance` | 4x1, visible | 2x1, 3x1, 4x1 | Average compliance + target |
| `ask_cairn` | 2x2, **rail**, visible | 2x2, 2x3, 3x2, 3x3 | "Summary": LLM briefing + references (async, cached) |
| `ongoing_audits` | 1x2, **rail**, visible | 1x2, 1x3, 2x2 | Audits running now (**conditional**: hidden when none; multi-column when wide) |
| `indicator` | (added on demand) | 1x1 | **Multiple**; one KPI per instance, params `{indicator, show_chart}` |
| `compliance_by_framework` | 3x2, visible | 2x2, 2x3, 3x2, 3x3 | Sortable progress bars (gear) |
| `upcoming_deadlines` | 1x2, **rail**, visible | 1x2, 1x3, 2x2 | Right-rail; next 30 days |
| `active_objectives` | 2x2, main, visible | 1x2, 2x2, 2x3, 3x2 | Sortable progress bars (gear) |
| `priority_risks` | 1x2, **rail**, visible | 1x2, 1x3, 2x2 | Critical/high, untreated |
| `risk_treatment_flow` | 4x2, main, visible | 2x2, 3x2, 4x2, 4x3 | Sankey (fills tile) |
| `risk_matrix_current` | 2x2, main, visible | 2x2, 2x3 | Current-risk heatmap (before treatment) |
| `risk_matrix_residual` | 2x2, main, visible | 2x2, 2x3 | Residual-risk heatmap (after treatment) |

`upcoming_deadlines`, `priority_risks`, `ask_cairn` and `ongoing_audits` default
to the **rail**; everything else to the **main** area.

The `ongoing_audits` widget is **conditional**: the view lists compliance
assessments whose window covers today, excluding cancelled audits and draft
"audit projects" (status `DRAFT`); when there is none, `has_data` is false and the
widget hides in view mode (it still shows as a drop target while editing). Each
item shows the audit name, status badge, frameworks, the concerned scope(s)
(via the shared `grouped_scope_badges` component), the lead assessor (photo +
name) and a time-progress bar with the days left; items flow into a responsive
grid (one column when narrow, several when wide). When at least one audit is
running, the **Ask Cairn** briefing also covers it. The endpoint builds the audit
details **server-side** (`ongoing_audits_brief` - name, audited scopes, standards,
lead auditor and a `covers_entire_scope` flag, never trusting client strings). The
model returns the briefing as **two `<p>` paragraphs** (it may open a paragraph
with at most one professional, inoffensive emoji, at the very start - enforced
server-side by `_move_emojis_to_paragraph_start`, which moves any stray emoji to
the front and drops extras): the
**first** is the audit paragraph, opened by a short bold `<b>` lead-in (the
standards involved + "en cours"), then plain prose naming what is audited (the word *scope* /
*perimetre*; when `covers_entire_scope` is true - every root perimeter selected -
it says the audit covers the **entire scope**, otherwise it **always names the
specific scopes** - never a vague "partially"), the standards and the lead auditor,
factoring out anything repeated across audits (a shared lead auditor or standard).
The **second** paragraph (plain, no bold lead-in) is a single flowing **sentence**
(not a terse list) covering the critical items, each named by its exact entity
(critical *risks*, non-compliant *requirements*, overdue *action plans* - never a
vague "point"). These metrics are **counts only**, so the model is told to state
the figure + entity and never invent individual item names (e.g. it must not
enumerate "Risque critique 1 et Risque critique 2", which it does not have). The
model's output is escaped server-side except for `<p>` / `<b>` / `<strong>`
(`_safe_briefing_html`), so the widget renders it as HTML without an injection
risk. Any **person** the briefing names (a lead auditor) is then swapped for a
trusted **photo + name chip** (`_inject_people_chips`: a single longest-first
regex pass over the sanitised HTML replaces each known name with a server-built
avatar + name pill - the chip markup bypasses the escape but is built from the
user, with the name and avatar URL escaped). The briefing never claims there is
no audit.

The `ask_cairn` widget (titled **"Summary"** / "Résumé"; the Ask Cairn brand
lives in the attribution line) shows an **LLM-synthesised briefing** of the day
and defaults to the **rail**. The dashboard view builds a small metrics snapshot
(`ask_cairn_data`: overall compliance plus the non-zero **urgent** counts). Only
the urgent items feed it - the "Priority" action group (tone `high`: critical
risks, non-compliant requirements, overdue plans); the lower-priority "to plan" /
"to watch" items are deliberately excluded so the briefing stays focused and the
user is not buried under a long to-do list (those stay visible in the full Today's
actions / tasks). After the page renders, the widget **asynchronously POSTs that
snapshot** to `POST /dashboard/ask-cairn-briefing/`, which asks the configured
model (Mistral by default, via `assistant/briefing.py`) to synthesise it into a
one-to-two-sentence briefing (complete, concise prose that **names the specific
items and figures** - a vague count restatement like "N points need your
attention" is explicitly forbidden), **caches it per user per day**, and returns
the text plus an honest attribution ("AI-generated summary on &lt;date&gt; at
&lt;time&gt;, powered by &lt;provider&gt;"). The briefing is written in the
**reader's language** (`request.LANGUAGE_CODE`, i.e. the user's profile language):
the prompt carries French example phrasing to pin down structure, so the target
language is passed **spelled out** ("English" / "French" via `_language_name`,
not the bare code) and the model is told the examples are structural only and
must never dictate the output language - otherwise an English reader was getting
a French briefing. The model is also told to phrase the briefing **idiomatically**
in the target language and not translate the French examples word for word (which
yielded stilted English such as "Audit ISO 27001 in progress"); the most visible
example, the audit lead-in, is given in **both English and French** so each has a
natural template. Below the summary the widget lists
the **references** it draws on (`ask_cairn_references`: the key items, each
linking to where to act).
The fetch is off the request path, so a slow or unreachable model only delays the
briefing, never the page. While it loads, a **skeleton placeholder** reserves the
text's space (so the rail widgets below it don't jump) and the real briefing
**fades in** when it arrives; the deterministic, properly-pluralised **count
fallback** ("N points need your attention today") is shown only if the assistant
is disabled or the call fails (kept hidden otherwise so it never flashes). When
there is nothing urgent it shows an all-clear. The endpoint allow-lists the metric
keys and coerces values, so the client cannot inflate or inject the model payload.

When there are ongoing audits, the **audit cards** (the same cards as the Ongoing
audits widget, via the shared `ongoing_audit_card` / `ongoing_audit_styles`
includes) are also surfaced inside the Summary widget, in the **right column**
(the `ask-cairn__aside`, which holds the references then the cards beneath them);
the standalone Ongoing audits widget is kept. The cards **stretch to equal
height** (each fills its grid cell; the progress bars are pushed to the bottom so
they line up) and the grid uses `auto-fit` (not `auto-fill`) so a couple of cards
stretch to fill the width instead of bunching to the left.

## Persistence and resolution

A user's arrangement is stored on `User.dashboard_layout` (JSON): an ordered
list of `{key, id, size, visible, zone, params}` instances, where `id` is the
widget type and `key` is a stable per-instance id (it equals `id` for
singletons). At render time `resolve_layout()` merges it with the registry:
known entries are kept in order (sizes clamped to the widget's allowed set, zone
clamped to `main`/`rail`, params sanitised); unknown ids are dropped; a
**singleton** appears at most once (duplicates dropped) and is auto-appended with
its defaults if missing; a **multiple** widget keeps every instance (each with a
unique key, generated when absent) and is never auto-appended. This means newly
shipped singleton widgets appear automatically and removed ones disappear with no
data migration. Layouts saved before the rail existed simply gain each widget's
default zone on the next resolve. Legacy single-letter sizes (`S`/`M`/`L`/`XL`,
from before the `WxH` standard) are migrated on resolve to the allowed token with
the same width, so an old layout keeps its relative widths.

## Autofit (fit content to tile)

A main-area widget always fills its tile exactly - **never a scrollbar, never an
empty band**. Two mechanisms cooperate:

- The tile is a flex column that clips overflow (`overflow: hidden`), so nothing
  ever scrolls.
- List-style widgets render a generous pool of rows inside a `[data-fit-list]`
  container. A small client-side autofit (in `home.html`) **hides trailing rows
  until the list no longer overflows** its tile, then the kept rows
  **distribute (`space-between`) to fill the height**. So a taller or wider tile
  shows *more* rows and a shorter one shows *fewer* - the content adapts to the
  size rather than scrolling or leaving a gap.
- The progress-bar widgets (`[data-progress-rows]`) use a deterministic variant
  instead of measure-and-trim: they sort the rows and show a fixed count for the
  tile height (see *Instances and parameters*), the shown rows dividing the
  height evenly.
- Fixed-aspect widgets that can't be trimmed (the risk-matrix heatmaps,
  `[data-fit-scale]`) are **measured and scaled**: a `--fit-scale` is computed
  (`min(slotW/contentW, slotH/contentH)`, capped for modest upscaling) and applied
  as a `transform: scale`, so the whole matrix always fits its tile, centred, with
  no overflow. Outside the fixed grid it shows natural size (scrolls if cramped).

Autofit runs on first paint and on every tile-size change via a `ResizeObserver`
on each widget (so resizing in edit mode, moving a widget between zones, or a
window/container reflow all re-fit), with a `resize`-event fallback. Chart
widgets fill their tile the same way: the risk-treatment-flow Sankey now grows to
the tile height and re-renders (`chart.resize()`) on every tile change. The rail
keeps natural content height, so its lists are never trimmed.

A visible widget with no data to show (e.g. no frameworks yet) is hidden in view
mode and shown only as a removable placeholder while editing.

## Edit mode

Toggled client-side (no reload). Entering edit mode sets `body.dash-editing`,
which reveals the dotted placement grid (on both zones), the per-widget chrome
(remove button, drag grip, a **config gear** on configurable widgets, resize
menu) and the wiggle animation. Reordering uses
[SortableJS](https://sortablejs.github.io/Sortable/) (lazy-loaded from a CDN,
like ECharts): each zone is its own sortable, sharing a group, so a widget can be
**dragged between the main area and the rail** - its `zone` is updated on drop.
The resize menu is hidden in the rail (rail widgets fill the rail width).

Adding and removing depends on the widget kind. A **singleton** is removed by
flipping it to hidden (its gallery tile reappears) and re-added from the gallery
in its zone. A **multiple** widget's gallery tile is always available; clicking
it clones a fresh instance (a hidden `<template>`), assigns a new key and opens
its config dialog, while removing an instance deletes it outright. Gallery tiles
can also be **dragged straight onto a zone** (the gallery is a SortableJS
clone-source; the zones' `onAdd` materialises the dropped tile into the real
widget at the exact drop position). Either way, a newly placed widget **scrolls
into view and flashes** an accent ring so it is obvious where it landed. The config
gear opens a shared dialog (for the indicator widget: pick the indicator + toggle
the chart) that writes the instance's `params` and refreshes its card from the
partial endpoint. Leaving edit mode persists the layout if anything changed. The
wiggle and zone transitions honour `prefers-reduced-motion`.

## API

- `GET /api/v1/dashboard-layout/` - the resolved layout plus the widget catalogue.
- `PUT /api/v1/dashboard-layout/` - replace the layout (`{"layout": [...]}`); the
  payload is sanitised against the registry.
- `POST /dashboard/layout/` - the web UI save endpoint used by the editor.
- `GET /dashboard/indicator-widget/?indicator=<id>&chart=0|1` - render a single
  indicator widget's card (used to refresh an instance after it is configured and
  for the WebSocket live-value refresh); returns the placeholder when no valid
  indicator is supplied.
- `POST /dashboard/ask-cairn-briefing/` - generate (and cache per user per day)
  the Ask Cairn LLM briefing for the posted metrics snapshot `{"data": {...}}`;
  returns `{ok, text, disclaimer}`, or `{ok: false}` when the assistant is off or
  the model is unavailable.

## MCP tools

- `get_dashboard_layout` - the current user's layout and the widget catalogue.
- `update_dashboard_layout` - replace the layout (sanitised against the registry).

Both operate on own-data (no extra permission beyond authentication).
