# List-table standard

Single source of truth for how every **list table** (full-page `*_list.html`, the
HTMX `*_table_body.html` partials, and detail-page sub-tables) must look and behave.
Derived from the canonical examples (`assets/essential_asset_list.html`,
`assets/dependency_list.html`). Follow it exactly so every table in the app shares
the same appearance, columns and ergonomics, in both light and dark themes.

## Page skeleton (full-page list)

```django
{% extends "base.html" %}
{% load i18n ui help_tags table_tags workflow_tags %}   {# + entity-specific libs #}

{% block title %}{% trans "<Plural entity>" %} — Cairn{% endblock %}

{% block content %}
{% page_header _("<Plural entity>") eyebrow=_("<Module>") accent="<module-accent>" %}
  {# primary action button(s), permission-gated, in the page header #}
{% endpage_header %}
{% help_modal "<app>.<entity>_list" %}

{# OPTIONAL filter chips — keep when the list already had them #}

{% include "includes/table_search.html" %}

<div class="card">
  <div class="table-responsive">
    <table class="table table-hover mb-0">
      <thead> <tr> …columns… </tr> </thead>
      <tbody>
        {% for obj in objects %}
        <tr> …cells… </tr>
        {% empty %}
        {% empty_state title=_("…") message=_("…") colspan=N %}
        {% endfor %}
      </tbody>
    </table>
  </div>
</div>

{% include "includes/pagination.html" %}
{% endblock %}
```

## Hard rules

1. **Card wrapper, always.** `<div class="card"><div class="table-responsive"><table class="table table-hover mb-0">`.
   Never a raw `<table>` without the card, never add `align-middle` (the base
   stylesheet already vertical-centers cells).
2. **Search toolbar, always.** `{% include "includes/table_search.html" %}` directly
   above the card on every list page.
3. **Pagination, always.** `{% include "includes/pagination.html" %}` as the last line
   before `{% endblock %}`.
4. **Reference column = clickable pill.**
   `<td><a href="{detail url}" class="ref">{{ obj.reference }}</a></td>`.
   Header: `{% sortable_th "reference" "Ref." %}` (label is always `Ref.`, never
   `Reference`). Do **not** add `style="text-decoration:none"` — `a.ref` already
   handles it. If a row has no reference, omit the column entirely (don't fake one).
5. **Name column = clickable accent link.**
   `<td><a href="{detail url}" class="cell-link">{{ obj.name }}</a></td>`.
   Header: `{% sortable_th "name" "Name" %}`.
6. **Cross-references** to another record use `class="cell-link"` too (e.g. an
   essential asset linked from a dependency row). Never reuse the old inline
   `style="color:var(--accent);text-decoration:none;font-weight:500"` — replace every
   occurrence with `class="cell-link"`.
7. **Empty-cell placeholder = ASCII hyphen.** `{{ value|default:"-" }}`. Never the
   em-dash `—` (U+2014). Replace any `default:"—"` with `default:"-"` and any bare
   `—` used as an empty marker inside a `<td>` with `-`. (Em-dashes elsewhere, e.g.
   prose, are out of scope for this pass.)
8. **Status column** (workflow entities): `<td>{% workflow_badge obj %}</td>`,
   header `{% sortable_th "workflow_state" "Status" %}`.
9. **Tags column** (entities with tags): second-to-last column.
   Header `<th>{% trans "Tags" %}</th>`, cell
   `<td>{% include "includes/tags_badge.html" with tags=obj.tags.all %}</td>`.
   Replace any inline `{% for tag in … %}<span class="badge" …>…</span>{% endfor %}`
   loop with that include.
10. **Actions column = always last, right-aligned.**
    Header `<th class="text-end">{% trans "Actions" %}</th>`, cell `<td class="text-end">`.
    - Edit: `class="btn btn-sm btn-outline-primary" title="{% trans 'Edit' %}"`,
      icon `<i class="bi bi-pencil"></i>`.
    - Delete (only when the entity is deletable): `class="btn btn-sm btn-outline-danger"
      title="{% trans 'Delete' %}"`, icon `<i class="bi bi-trash"></i>`.
    - **Keep the existing edit mechanism**: HTMX drawer (`hx-get` →
      `#drawer-form-content`) where the list already uses it, full-page `href`
      otherwise. Keep existing permission gates (`{% has_perm %}`).
    - Lists currently missing an Actions column must gain one.
11. **colspan** in `{% empty_state %}` must equal the exact number of `<th>` columns.
12. **i18n**: every visible string wrapped in `{% trans %}`/`_()`. Do not edit any
    `locale/*.po` file in this pass — instead report any *new* English string you
    introduce so it can be translated centrally.

## Two-line cells and people identity (optional)

By default a cell is a single value (rules 4-10). When a row carries several
**closely related** fields, group them into one cell on two lines instead of
spending a column on each : a **primary line** over a **muted secondary line**.
This keeps wide entities (people, contacts) scannable and the table narrow.

Use the shared helpers (defined in `base.html`, theme-aware in light/dark) :

- `.cell-stack` : the two-line wrapper (a flex column, tight `line-height`).
- `.cell-sub` : the muted, smaller secondary line (`var(--text-muted)`, `.8125rem`).
  A `.cell-link` placed directly in a `.cell-stack` is automatically bold (600).

```django
<td>
  <span class="cell-stack">
    <span>{{ obj.job_title }}</span>
    {% if obj.department %}<span class="cell-sub">{{ obj.department }}</span>{% endif %}
  </span>
</td>
```

**People identity** (avatar + name + secondary line) uses `.cell-people` :

```django
<td>
  <a href="{detail url}" class="cell-people">
    {% if u.avatar %}
    <img src="{{ u.avatar_64|default:u.avatar }}" alt="" class="cell-avatar">
    {% else %}
    <span class="cell-avatar-fallback">{{ u.display_name|initials }}</span>
    {% endif %}
    <span class="cell-stack">
      <span class="cell-link">{{ u.display_name }}</span>
      <span class="cell-sub">{{ u.email }}</span>
    </span>
  </a>
</td>
```

Rules for two-line / people cells :

- The **avatar is 40px** (`.cell-avatar` / `.cell-avatar-fallback`), sized to align
  with the two-line text block. Do **not** hand-roll avatar markup or inline sizes ;
  use the helpers (or `{% user_badge %}` for a single-line avatar+name elsewhere).
- The whole people cell is a single link to the detail page (`<a class="cell-people">`),
  not just the name.
- Keep the secondary line **secondary** : one muted field only, never a second link
  or a badge. Status, tags and actions stay in their own columns (rules 8-10).
- Fold the secondary field's standalone column **and its sort header** away when you
  merge it (e.g. merging Email into Name drops the Email `sortable_th`). The primary
  field stays sortable. Note the dropped sort in the PR description.
- Graceful fallback when the primary field is empty : promote the secondary field to
  the single line, or render `<span class="cell-empty">-</span>` if both are empty.
- Still **no `align-middle`** (rule 1) : the base stylesheet centres cells, and the
  helpers keep the two lines tight on their own.
- Canonical example : `accounts/user_list.html`.

## HTMX list + table_body split

Some lists render the `<tbody>` from a `*_table_body.html` partial loaded via HTMX.
In that case rules 4-11 about the **cells** apply to the partial; rules 1-3 and the
`<thead>` live in the `*_list.html`. Both files must stay column-aligned.

## Out of scope (do not touch)

- View/Python logic, URLs, sortable-field definitions.
- Per-list density tweaks already present (e.g. `style="font-size:.85rem"` on dense
  numeric cells) — leave them.
- `base.html` and `locale/*.po` (edited centrally).
- The `permission_list.html` card/badge layout (intentionally not a table).
