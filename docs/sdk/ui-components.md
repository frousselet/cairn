# UI components

The component framework every Cairn screen is built from. A screen composes
these parts. It does not re-type card, `<dl>`, badge or form markup. If a screen
needs something the framework lacks, extend the framework (a tag in
`core/templatetags/ui.py`, its template in `templates/components/`, its CSS in
`static/css/cairn/10-framework.css`, a test in `core/tests/test_ui_framework.py`)
and then use it. Do not fork it into the page.

The [brand guidelines](../brand/brand-guidelines.md) are the visual source of
truth (palette, type scale, spacing, motion, accessibility). The
[interface conventions](ui-conventions.md) cover the rules a screen follows.
This page is the catalogue : what exists, how to call it, and which page anatomy
it belongs to. `/styleguide/` renders every component live in a running instance.

Everything here loads with `{% load ui %}`.

## Page anatomies

There are four kinds of screen. Each has one canonical anatomy.

### List page

```django
{% page_header _("Action plans") nav="compliance:action-plan-list" accent="compliance" %}
  <button class="btn btn-primary" hx-get="{% url '...-create' %}" hx-target="#drawer-form-content" hx-swap="innerHTML">
    <i class="bi bi-plus-lg me-1" aria-hidden="true"></i>{% trans "New action plan" %}
  </button>
{% endpage_header %}
<div class="list-layout">
  <div class="list-main">
    <div class="card">
      {% include "includes/list_toolbar.html" %}
      <div class="table-responsive"><table class="table table-hover mb-0">...</table></div>
    </div>
    {% include "includes/pagination.html" %}
  </div>
  <aside class="list-rail list-rail--kpi">{% include "includes/list_rail_kpis.html" %}</aside>
</div>
{% include "includes/list_filter_offcanvas.html" with filter_list_url=request.path %}
```

Reference : `compliance/templates/compliance/action_plan_list.html`. The table
itself follows the [table standard](../brand/table-standard.md). An empty
`<tbody>` renders `{% empty_state colspan=N ... %}`.

### Detail page

```django
{% page_header obj.name reference=obj.reference nav="<list url name>" accent="<module>" %}
  {% include "includes/history_trigger.html" %}
  <a href="{% url '...-update' obj.pk %}" class="btn btn-primary" hx-get="{% url '...-update' obj.pk %}"
     hx-target="#drawer-form-content" hx-swap="innerHTML"><i class="bi bi-pencil me-1" aria-hidden="true"></i>{% trans "Edit" %}</a>
{% endpage_header %}
{% include "includes/history_panel.html" %}
{% include "includes/lifecycle_stepper.html" %}

{% detail_layout %}
  {% slot rail %}
    {% kpi_tile _("Lifecycle stage") obj.lifecycle_label icon="signpost-split" %}
    ... up to three more key figures ...
  {% endslot %}
  {% section_card _("Description") icon="text-left" %}...{% endsection_card %}
  ... one section_card per concern ...
  {% record_card obj %}
{% enddetail_layout %}
```

Reference : `compliance/templates/compliance/action_plan_detail.html`.

- **Header actions**, left to right : the history trigger, secondary actions
  (`btn-secondary`), **Delete** when the page offers it (`btn-danger` with the
  `trash` icon, opening its confirmation modal), then **Edit** as the single
  `btn-primary`, always last, always with the `pencil` icon and always opening
  the edit modal (`hx-get` into the drawer, with the page URL as `href` so a
  middle click still works).
- **The stepper** is the only place a state changes, and the only status
  display needed. Do not repeat the state as a badge in a card.
- **The rail** holds at most four `kpi_tile`. The first one is the lifecycle
  stage, then the figures a reader looks for first (priority, a due date, a
  count, a score).
- **The body** is a stack of `section_card`. Open with the description, or with
  an `overview` of the identifying facts, then the domain sections, then the
  relations, then comments. Always close with `record_card`.
- **No tabs**, unless the page really has separate modes (see the
  [conventions](ui-conventions.md)).

### Form

Every form opens in the modal shell. Its template is one line :

```django
{% extends "includes/modal_form.html" %}
{% block modal_title_icon %}<span class="drawer-title-icon"><i class="bi bi-list-check"></i></span>{% endblock %}
```

The fields, steps, helpers and progress come from the form
(`core.modal_forms.SteppedFormMixin`). The full-page version, used when the
`/edit/` URL is visited directly, is one line as well :

```django
{% extends "includes/page_form.html" %}
```

It renders the same fields in the same anatomy, every step shown as a titled
group, with the standard footer (Cancel on the left, Save on the right).
`core.mixins.HtmxFormMixin` provides its title (`modal_title_create` /
`modal_title_update`), its breadcrumb and its Cancel target. Override
`page_form_fields` only for a form with no `steps`, and only to iterate the
fields through `includes/form_field.html`.

### Delete confirmation

```django
{% extends "includes/confirm_delete_modal.html" %}   {# drawer-served #}
{% extends "includes/confirm_delete_page.html" %}    {# direct visit #}
{% load i18n %}
{% block delete_title %}{% trans "Delete decision" %}{% endblock %}
{% block delete_message %}{% blocktrans with ref=object.reference %}Delete decision <strong>{{ ref }}</strong>?{% endblocktrans %}{% endblock %}
{% block delete_details %}<p class="text-muted small">{% trans "The 4 linked actions will become orphaned." %}</p>{% endblock %}
```

Both shells name the object, state that the action cannot be undone, put Cancel
on the left and the red **Delete** on the right. Fill `delete_details` with the
consequences (linked records, protection rules). An inline delete button with
its own modal, in a table row for example, is `{% confirm_delete url=... name=... %}`.

## Catalogue

| Component | Kind | Use it for |
| --- | --- | --- |
| [`page_header`](#page_header) | block tag | The title bar of every page |
| [`detail_layout`](#detail_layout) | block tag + `rail` slot | The body of a detail page |
| [`kpi_tile`](#kpi_tile) | tag | One key figure in a list or detail rail |
| [`section_card`](#section_card) | block tag + `actions` / `footer` slots | A titled content card |
| [`subhead`](#subhead) | tag | A divider title inside a card |
| [`overview` / `ov_row`](#overview--ov_row) | block tags | Icon-led summary rows |
| [`meta_list` / `meta_item`](#meta_list--meta_item) | block tags | Label and value pairs |
| [`record_card`](#record_card) | tag | The traceability card that closes a detail page |
| [`ref_link`](#ref_link) | tag | A linked element : reference pill and name |
| [`tag_list`](#tag_list) | tag | Tags as coloured pills |
| [`badge` / `choice_badge`](#badge--choice_badge) | tags | Status, level and result badges |
| `{% workflow_badge obj %}` | tag (`workflow_tags`) | The lifecycle state of an element |
| [`dash` / `or_dash`](#dash--or_dash) | tag / filter | The "no value" marker |
| `empty_state` | tag | An empty list or section |
| `progress_bar` | tag | A percentage |
| `confirm_delete` | tag | An inline delete button with its confirmation modal |
| `bulk_actions_bar`, `filter_chip`, `stepper`, `kpi_card`, `sidebar_card`, `illustration` | tags | See their docstrings in `core/templatetags/ui.py` |
| [`back_url`](#back_url) | tag | A safe "back to where I came from" link |

### Slots

The block components take named **slots**. A slot is a region of the
component's markup that the caller fills, wherever it sits in the body :

```django
{% section_card _("Contacts") icon="person-lines-fill" %}
  {% slot actions %}<button class="btn btn-sm btn-secondary">...</button>{% endslot %}
  ...body...
{% endsection_card %}
```

A slot belongs to the component that directly contains it. Slots of a nested
component stay with that component.

### page_header

```django
{% page_header title reference=obj.reference nav="<list url name>" accent="<module>" subtitle=... icon=... compact=True %}
  ...action buttons...
{% endpage_header %}
```

`nav` builds the breadcrumb from the sidebar tree (`core/navigation.py`). On a
detail page, the last crumb is the reference. On detail pages the header also
shows who last changed the element, and when. `accent` takes a module key (see
the brand guidelines).

### detail_layout

```django
{% detail_layout rail_label=_("Key figures") %}
  {% slot rail %}...kpi_tile...{% endslot %}
  ...main column...
{% enddetail_layout %}
```

Below 1800 px the rail sits above the content, as a row of tiles that wraps.
From 1800 px it becomes a sticky right-hand column and the page widens. Without
a `rail` slot the main column takes the full width. The rail is an `<aside>`
named by `rail_label`.

### kpi_tile

```django
{% kpi_tile label value icon="calendar-check" tone="success" href=url suffix="%" size="lg" %}
```

`tone` is one of `accent` (default), `success`, `warning`, `danger`, `info` or
`neutral`. Semantic tones are reserved for figures that carry a status : use
`{{ value|badge_variant:"level" }}` to take the tone from the badge registry.
`size` is `lg` for a number and `sm` for a word or a date, and is inferred when
omitted. An empty value renders the dash. With `href`, the whole tile is a link.

### section_card

```django
{% section_card title icon="link-45deg" count=n id="relations" collapsible=True open=False flush=True hide_empty=True %}
  {% slot actions %}...{% endslot %}
  ...body...
  {% slot footer %}...{% endslot %}
{% endsection_card %}
```

The title is an uppercase eyebrow (`h2.section-card__title`), followed by an
optional `count` pill (zero is shown) and the `actions` slot on the right.

- `collapsible` turns the card into a native `<details>`, and `open=False`
  starts it folded.
- `flush` drops the body padding, so a table runs edge to edge (its first and
  last cells keep the card's inset).
- `hide_empty` renders nothing when the body is empty, so an optional section
  needs no surrounding `{% if %}`.

### subhead

```django
{% subhead _("Certified scope") icon="diagram-3" %}
```

A small uppercase divider for a second level inside a card.

### overview / ov_row

```django
{% overview %}
  {% ov_row "journal-bookmark" _("Framework") %}<a href="..." class="ov-link">{{ obj.framework }}</a>{% endov_row %}
  {% ov_row "award" _("Certification body") %}{{ obj.issuer }}{% endov_row %}
  {% ov_row "text-left" _("Description") lead=True rich=True %}{{ obj.description|safe }}{% endov_row %}
{% endoverview %}
```

Each row shows only an icon and a value. The label is not displayed : it names
the row for assistive technology (`role="group"` + `aria-label`). A row whose
body renders empty is dropped, and an overview with no row renders nothing.
`lead` enlarges the row (use it for the description). `rich` styles rich-text
HTML.

### meta_list / meta_item

```django
{% meta_list cols=2 %}
  {% meta_item _("Start date") plan.start_date %}
  {% meta_item _("Supervisor") %}{% user_badge plan.owner size=28 link=True block=True %}{% endmeta_item %}
  {% meta_item _("Notes") wide=True %}...{% endmeta_item %}
{% endmeta_list %}
```

A `<dl>` grid with one, two or three columns (`cols`). It falls back to one
column on a phone. `meta_item` has two forms : the value inline (escaped), or a
block body. Either way an empty value renders the dash. `wide` spans every
column, and `hide_empty` drops an empty block item.

### record_card

```django
{% record_card obj %}
```

The reference, version, author, creation date and last change of a `BaseModel`.
It always comes last on a detail page, in the same order, with dates in the
active locale's format inside `<time datetime>`.

### ref_link

```django
<div class="ref-links">
  {% for risk in plan.risks.all %}{% url 'risks:risk-detail' risk.pk as u %}{% ref_link risk url=u %}{% endfor %}
</div>
```

The element's reference pill, then its name as a link. `preview_url` opens the
element in the drawer instead of navigating. `label` overrides the name (it
defaults to `obj.name`, then `str(obj)`) and `reference` overrides the pill.
Stack several links in a `.ref-links` container.

### tag_list

```django
{% tag_list obj.tags.all %}            {# nothing when there is no tag #}
{% tag_list obj.tags.all dash=True %}  {# the dash when there is none #}
```

Each tag renders as a pill in its own colour. The label colour is chosen by
relative luminance, so a pale tag keeps a legible label. Only a `#rgb` or
`#rrggbb` value is ever written into the style attribute, and anything else
falls back to the neutral tone.

### badge / choice_badge

```django
{% choice_badge plan "priority" %}                  {# tone from the registry, label from get_priority_display #}
{% choice_badge req "compliance_status" %}
{% choice_badge obj "state" type="status" %}
{% badge "critical" type="severity" %}              {# a raw value #}
{% badge variant="success" icon="check" label=_("Signed") %}
```

Every badge is a `.badge-dot` pill, in a table, a card or a header alike. Tones
come from `BADGE_REGISTRY` in `core/templatetags/ui.py` :

- `level` : priority, criticality, severity and impact share one ordinal scale.
- `compliance` : requirement and assessment results.
- `treatment_decision`, `threat_zone` and `ebios_scale` (the EBIOS RM 1 to 4 scales).
- `methodology` and `dic` : categories, so they keep the identity colour.
- `status`, `approval` and `risk`.

`choice_badge` infers the type from the field name (see
`CHOICE_BADGE_TYPES`). Never write an `{% if value == '...' %}` chain to pick a
badge colour : add the value to the registry. A lifecycle state is
`{% workflow_badge obj %}`, which reads its tone from the lifecycle.

### dash / or_dash

```django
{{ obj.start_date|or_dash }}
{% dash %}
```

The single marker for an empty value. It is announced as "Not set" to screen
readers. Components that display values (`meta_item`, `kpi_tile`, `tag_list
dash=True`, `choice_badge`) apply it themselves.

### back_url

```django
<a href="{% back_url list_url %}" class="btn btn-secondary">{% trans "Back" %}</a>
```

Returns the referrer only when it comes from this host, otherwise the default.
Never write `request.META.HTTP_REFERER` into a template : it is set by the
client.

## Utilities

A short list of utility classes replaces the inline styles that recurred most :

| Class | Instead of |
| --- | --- |
| `.text-accent` | `style="color:var(--accent)"` |
| `.text-meta` | `style="color:var(--text-muted);font-size:.82rem"` (secondary information) |
| `.text-sm` | `style="font-size:.8rem / .85rem / .875rem"` (the 13 px step of the type scale) |
| `.link-inherit` | `style="color:inherit;text-decoration:none"` |
| `.cursor-pointer` | `style="cursor:pointer"` |
| `.sticky-rail` | `style="position:sticky;top:1rem;align-self:flex-start"` |
| `.tabular-nums` | numbers that must align |

An inline `style` is acceptable only for a value computed per element (a width
percentage, a custom property such as `--tag-bg`). A fixed visual choice belongs
in a class.

## Stylesheets

The design system ships as ordered static files in `static/css/cairn/`. They are
linked by `templates/base.html` through `{% static_v %}` (cache-busted on change),
and the file order is the cascade :

| File | Holds |
| --- | --- |
| `00-tokens.css` | Design tokens : palette, semantic colours, dark theme, button fills, module accents |
| `01-base.css` | Element defaults and the typography ladder |
| `02-shell.css` | Sidebar, main content area, vertical rhythm |
| `03-elements.css` | Bootstrap elements restyled : cards, tables, buttons, badges, tabs, alerts, forms, progress, pagination |
| `04-overlays.css` | Command palette and the assistant panel |
| `05-content.css` | Hero, references, table links, avatars, filters, TomSelect, rich text, modals |
| `06-responsive.css` | Mobile adjustments |
| `07-forms.css` | The modal form engine |
| `08-motion.css` | Page transitions, skeleton loader |
| `09-components.css` | Page header, empty state, KPI, list and detail layouts, stepper, lifecycle graph |
| `10-framework.css` | The primitives on this page and the utilities |

Only rules that need the template engine stay inline in `base.html` : the
`@font-face` declarations (`{% static %}`) and the per-company accent override
(company settings).
