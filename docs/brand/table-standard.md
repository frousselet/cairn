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
