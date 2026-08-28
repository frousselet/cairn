# Adding a dashboard widget

The home dashboard is a grid of tiles a user arranges themselves. A widget is
declared once in a registry, given a template, and it appears : in the "Add a
widget" gallery, in the size picker, in every user's dashboard if it is a
singleton, and in the
[generated reference](../reference/generated/dashboard-widgets.md). There is no
per-widget plumbing to write and no data migration to run.

This page adds a widget end to end. The running example is **Overdue action
plans** : a list of compliance action plans whose target date has passed.

## How the dashboard is put together

Understanding the four moving parts first makes the rest obvious.

```
core/dashboard.py                       core/views.py                templates/
┌───────────────────────┐               ┌──────────────────┐         ┌──────────────────┐
│ DASHBOARD_WIDGETS     │──registry────▶│ GeneralDashboard │──ctx───▶│ home.html        │
│  DashboardWidget(...) │               │  View            │         │  └ _shell.html   │
│                       │               │   widget_has_data│         │      └ your      │
│ resolve_layout()      │◀──stored──────│   _place()       │         │        template  │
└───────────────────────┘   layout      └──────────────────┘         └──────────────────┘
          ▲                                                                    │
          │                                                                    ▼
   User.dashboard_layout  ◀──── POST /dashboard/layout/ ────  edit mode in the browser
```

1. **The registry** (`DASHBOARD_WIDGETS` in `core/dashboard.py`) declares what a
   widget is : its id, title, icon, template, category, allowed sizes and
   default placement.
2. **The user's layout** (`User.dashboard_layout`, a JSON list) records their
   personal arrangement : order, size, zone, visibility and per-instance
   parameters.
3. **`resolve_layout()`** merges the two at render time. This is the part that
   matters : a widget you ship today appears on every existing dashboard
   tomorrow, and a widget you remove drops out, without a migration. Unknown
   ids are dropped, sizes are clamped to what the widget allows, and parameters
   are re-sanitised, so a stale or malicious client payload can never corrupt a
   stored layout.
4. **`GeneralDashboardView`** puts the data in the context and decides, per
   widget, whether it has anything to show.

### Sizes, zones and what they mean

A size is a `WxH` token. **W** is a width in quarter-columns, 1 to 4, so `4` is
full width on the 12-column grid. **H** is a height in fixed row units, 1 to 4,
plus the half-step `0.5` used by the bare Section heading. `2x1` is a
half-width, one-row tile; `4x2` is full width and two rows tall.

There are three zones. `main` is the grid below the title. `rail_top` and
`rail_bottom` are the right-hand rail on wide screens; when the layout
collapses, the top rail moves *above* the main area and the bottom rail below
it. Rail widgets render at the rail width with content height, so their `WxH`
is ignored while they sit there. A narrow list belongs in the rail; a chart does
not.

Tiles do not scroll. A widget's content is fitted to the tile it was given, so
list widgets read `PROGRESS_ROW_COUNTS` to decide how many rows fit at that
height. Design for that, rather than assuming you can overflow.

## 1. Declare the widget

In `core/dashboard.py`, add an entry to `DASHBOARD_WIDGETS`. Keep the list
ordered by `default_order`; leave gaps of ten so a later widget can slot in
between two without renumbering.

```python
DashboardWidget(
    id="overdue_action_plans",
    title=_("Overdue action plans"),
    icon="calendar-x",                       # a Bootstrap Icons name, no "bi-" prefix
    template="dashboard/widgets/overdue_action_plans.html",
    category=CATEGORY_COMPLIANCE,
    sizes=("1x2", "1x3", "2x2"),             # ascending by (width, height)
    default_size="1x2",
    default_order=45,
    default_zone=ZONE_RAIL_TOP,
    description=_("Action plans whose target date has passed."),
),
```

Every field of `DashboardWidget`:

| Field | Meaning |
| --- | --- |
| `id` | Stable identifier. It ends up in stored layouts, so renaming it silently drops the widget from every dashboard that had it |
| `title` | Shown in the header and the gallery. Lazy-translated |
| `icon` | A [Bootstrap Icons](https://icons.getbootstrap.com/) name, without `bi-` |
| `template` | Partial under `templates/dashboard/widgets/` |
| `category` | Groups the gallery : compliance, risks, governance, activity, incidents, layout |
| `sizes` | The allowed `WxH` tokens. One entry means no resize control is offered |
| `default_size` | Must be one of `sizes` |
| `default_order` | Position on a fresh dashboard |
| `default_visible` | Whether a fresh dashboard shows it. Defaults to true |
| `default_zone` | `main`, `rail_top` or `rail_bottom` |
| `description` | The gallery tile's subtitle. Lazy-translated |
| `multiple` | Placeable several times, each instance with its own parameters. Added on demand from the gallery, never auto-appended |
| `param_sanitizer` | Normalises this widget's per-instance parameters (see below) |
| `config` | Which configuration dialog the edit-mode gear opens. A widget is configurable if and only if this is set |
| `bare` | Renders with no card chrome : no background, border, shadow or padding. Used by the Section heading |

A **singleton** (the default) appears at most once and is auto-appended to any
layout missing it, which is how a new widget reaches existing users. A
`multiple` widget starts at zero instances and is added deliberately.

## 2. Write the template

`templates/dashboard/widgets/overdue_action_plans.html`. The generic shell
(`_shell.html`) already draws the card, the drag handle, the resize menu and
the remove button, so the partial is only the content.

```django
{% load i18n %}
{# Widget: compliance action plans past their target date. Expects `overdue_action_plans`. #}
<div class="card h-100">
  <div class="card-header d-flex align-items-center gap-2">
    <i class="bi bi-calendar-x" aria-hidden="true"></i>
    <span>{% trans "Overdue action plans" %}</span>
  </div>
  <div class="card-body" data-progress-rows>
    {% for plan in overdue_action_plans %}
      <a href="{{ plan.get_absolute_url }}" class="d-flex justify-content-between text-decoration-none">
        <span class="text-truncate">{{ plan.name }}</span>
        <span class="badge text-bg-danger">{{ plan.target_date|date:"SHORT_DATE_FORMAT" }}</span>
      </a>
    {% endfor %}
  </div>
</div>
```

Four things the template must respect:

- **`h-100` on the card.** The tile has a fixed height and the card fills it.
- **Both themes.** Use Bootstrap semantic classes and the brand tokens, never a
  hardcoded colour. Check light and dark before calling it done.
- **No overflow.** The tile does not scroll. Slice the list rather than letting
  it spill.
- **Every string translated**, with its French entry added in the same change.

`placed` is available in the template : `placed.params`, `placed.size`,
`placed.w`, `placed.h`, `placed.key`. A widget that renders differently by
height reads `placed.h`.

## 3. Provide the data

In `GeneralDashboardView.get_context_data` (`core/views.py`), add the queryset,
scope-filtered like everything else on that page:

```python
ctx["overdue_action_plans"] = self._filter_scoped(
    ActionPlan.objects.filter(
        target_date__lt=today,
        status__in=ACTION_PLAN_OPEN_STATUSES,
    )
).select_related("owner")[:10]
```

Then declare whether the widget has anything to show, in the `widget_has_data`
mapping a few lines below:

```python
widget_has_data = {
    ...
    "overdue_action_plans": bool(ctx["overdue_action_plans"]),
}
```

This is not cosmetic. A visible widget with no data is **hidden in normal mode
and shown as a removable placeholder in edit mode**, so a user is never
presented with an empty box they cannot explain, but can still see and remove it
while rearranging. Omit the entry and the widget defaults to "always has data",
which shows an empty card for ever.

The dashboard view is one query-heavy method serving every widget. Use
`select_related` / `prefetch_related`, slice, and if your widget needs several
rows per item, pre-fetch them in one query the way the indicator widget does
rather than looping in the template.

## 4. If the widget takes parameters

Skip this unless a user needs to configure the tile. A parameterised widget
carries a small `params` dict per instance, and **it must be sanitised** :
`params` arrives from the browser, and `resolve_layout` runs the sanitiser on
every load, so a malformed or hostile payload is normalised rather than stored.

```python
def _sanitize_overdue_params(raw) -> dict:
    """Normalise the widget's params: ``{days}`` - how far past due to look."""
    raw = raw if isinstance(raw, dict) else {}
    try:
        days = int(raw.get("days", 0))
    except (TypeError, ValueError):
        days = 0
    return {"days": max(0, min(365, days))}
```

Wire it with `param_sanitizer=_sanitize_overdue_params`. The sanitiser must
return a complete dict for `None`, because that is what produces the widget's
defaults.

Setting `config="overdue"` makes the gear appear in edit mode. The dialog itself
is a partial under `templates/dashboard/`, included from `home.html` next to the
four that already exist (`indicator_config_modal.html`,
`section_config_modal.html`, `sort_config_modal.html`,
`target_config_modal.html`), with the small piece of JavaScript in `home.html`
that opens it and writes the result back onto the tile's `data-params`.

## 5. Regenerate the reference

```bash
python manage.py generate_docs
```

The widget now appears in
[reference/generated/dashboard-widgets.md](../reference/generated/dashboard-widgets.md).
CI fails until this is committed.

## 6. Test it

`core/tests/test_dashboard.py` is the place. At minimum:

```python
def test_widget_is_registered():
    assert "overdue_action_plans" in WIDGETS_BY_ID


def test_default_size_is_allowed():
    widget = WIDGETS_BY_ID["overdue_action_plans"]
    assert widget.default_size in widget.sizes


def test_layout_survives_an_unknown_widget():
    resolved = resolve_layout([{"id": "nope"}, {"id": "overdue_action_plans"}])
    assert [e["id"] for e in resolved if e["id"] == "nope"] == []


def test_widget_is_scope_filtered(client, user_in_one_scope, plan_in_another_scope):
    ...
```

The scope test is the one that matters. The dashboard is the surface where a
tenancy leak is least visible and most damaging, because a count does not look
like a record.

## Checklist

- [ ] Registry entry added, `default_size` is one of `sizes`
- [ ] Template renders correctly in light **and** dark mode
- [ ] Content fits every allowed size without scrolling
- [ ] Data is scope-filtered
- [ ] `widget_has_data` entry added
- [ ] Parameters sanitised, if the widget takes any
- [ ] Strings wrapped and translated into French
- [ ] `generate_docs` re-run and committed
- [ ] Tests cover registration, sizing and scope filtering
- [ ] Checked on a narrow viewport
