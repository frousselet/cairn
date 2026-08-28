<!-- GENERATED FILE - DO NOT EDIT BY HAND.
     Rendered from `core/dashboard.py` (`DASHBOARD_WIDGETS`) by `python manage.py generate_docs`.
     Change the code, then re-run the command. CI fails on a stale page. -->

# Dashboard widgets

The home dashboard is a grid of widgets, each declared once in `core/dashboard.py`. A user's personal arrangement lives in `User.dashboard_layout` and is merged with this registry at render time, so a newly shipped widget appears without a data migration.

Sizes are `WxH` tokens : width in quarter-columns (1..4) and height in row units (1..4, plus the half-step `0.5`). Zones are `main`, `rail_top`, `rail_bottom`.

To add one, follow [sdk/dashboard-widget.md](../../sdk/dashboard-widget.md).

**13 widgets** ship with the platform.

## Catalogue

| Id | Title | Category | Sizes | Default | Zone | Reusable | Config | Description |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `overall_compliance` | Overall compliance | Compliance | `2x1` `3x1` `4x1` | `4x1` | `main` | - | `target` | Average compliance across all active frameworks, with the target. |
| `ask_cairn` | Summary | Governance | `2x2` `2x3` `3x2` `3x3` | `2x2` | `rail_top` | - | - | Cairn's briefing of the day's key governance, risk and compliance points. |
| `ongoing_audits` | Ongoing audits | Compliance | `1x2` `1x3` `2x2` | `1x2` | `rail_top` | - | - | Audits running right now (shown only while one is under way). |
| `indicator` | Indicator | Governance | `1x1` | `1x1` | `main` | yes | `indicator` | A single KPI indicator with its value, trend and an optional mini-chart. |
| `compliance_by_framework` | Frameworks | Compliance | `2x2` `2x3` `3x2` `3x3` | `3x2` | `main` | - | `sort` | Per-framework compliance breakdown. |
| `upcoming_deadlines` | Upcoming deadlines | Activity | `1x2` `1x3` `2x2` | `1x2` | `rail_top` | - | - | Reviews, audits and target dates in the next 30 days. Designed for the right rail. |
| `active_objectives` | Objectives | Governance | `1x2` `2x2` `2x3` `3x2` | `2x2` | `main` | - | `sort` | Progress of objectives in play. |
| `priority_risks` | Priority risks | Risks | `1x2` `1x3` `2x2` | `1x2` | `rail_top` | - | - | Top untreated risks by residual level. Designed for the right rail. |
| `notification_deadlines` | Notification deadlines | Incidents | `2x2` `2x3` `3x2` `4x2` | `2x2` | `main` | - | - | Statutory notification obligations that are late or still running, with the incidents left open behind them. |
| `risk_treatment_flow` | Risk treatment flow | Risks | `2x2` `3x2` `4x2` `4x3` | `4x2` | `main` | - | - | How treatment moves risks from their current to their residual level. |
| `risk_matrix_current` | Current risks | Risks | `2x2` `2x3` | `2x2` | `main` | - | - | Probability x impact heatmap, before treatment. |
| `risk_matrix_residual` | Residual risks | Risks | `2x2` `2x3` | `2x2` | `main` | - | - | Probability x impact heatmap, after treatment. |
| `section` | Section | Layout | `4x0.5` | `4x0.5` | `main` | yes | `section` | A full-width heading placed on the page background to group widgets into sections. |

## Templates

| Id | Template | Icon | Default order | On by default | Bare |
| --- | --- | --- | --- | --- | --- |
| `overall_compliance` | `dashboard/widgets/overall_compliance.html` | `bi-speedometer2` | 10 | yes | - |
| `ask_cairn` | `dashboard/widgets/ask_cairn.html` | `bi-stars` | 15 | yes | - |
| `ongoing_audits` | `dashboard/widgets/ongoing_audits.html` | `bi-clipboard-check` | 18 | yes | - |
| `indicator` | `dashboard/widgets/indicator.html` | `bi-graph-up` | 20 | yes | - |
| `compliance_by_framework` | `dashboard/widgets/compliance_by_framework.html` | `bi-journal-bookmark` | 30 | yes | - |
| `upcoming_deadlines` | `dashboard/widgets/upcoming_deadlines.html` | `bi-calendar-event` | 40 | yes | - |
| `active_objectives` | `dashboard/widgets/active_objectives.html` | `bi-trophy` | 50 | yes | - |
| `priority_risks` | `dashboard/widgets/priority_risks.html` | `bi-fire` | 60 | yes | - |
| `notification_deadlines` | `dashboard/widgets/notification_deadlines.html` | `bi-hourglass-split` | 65 | yes | - |
| `risk_treatment_flow` | `dashboard/widgets/risk_treatment_flow.html` | `bi-diagram-3` | 70 | yes | - |
| `risk_matrix_current` | `dashboard/widgets/risk_matrix_current.html` | `bi-grid-3x3` | 80 | yes | - |
| `risk_matrix_residual` | `dashboard/widgets/risk_matrix_residual.html` | `bi-grid-3x3` | 81 | yes | - |
| `section` | `dashboard/widgets/section.html` | `bi-type-h2` | 90 | yes | yes |

## Rows shown by a progress-bar widget

A list widget fits its row count to the tile height, so a taller tile shows more rows rather than scrolling.

| Tile height | Rows |
| --- | --- |
| `1` | 2 |
| `2` | 5 |
| `3` | 8 |
| `4` | 11 |
