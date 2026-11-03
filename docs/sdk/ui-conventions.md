# Interface conventions

The patterns a new screen is expected to follow. They exist so that a user who
has learned one Cairn screen has learned them all, and so that a reviewer can
tell "different" from "wrong".

The visual system itself, the palette, typography, spacing, motion and
accessibility commitments, is
[the brand guidelines](../brand/brand-guidelines.md). That document is the
source of truth; this page is how it lands in a template.

## No build step

Server-rendered Django templates, Bootstrap 5.3, HTMX for partial updates,
Apache ECharts for graphs. There is no bundler and no npm. A change that needs
one is a change that needs a conversation first.

`/styleguide/` renders the whole component set in a running instance. Look there
before inventing a component.

## Never load a library from a CDN

Every front-end library is served from the instance itself. Referencing
`cdn.jsdelivr.net`, `unpkg.com` or Google Fonts from a template fails the build
(`core/tests/test_dependencies.py`), because an isolated deployment would then
render an unstyled page and every visitor would be announced to a third party.

To add one :

1. Declare it in `core/dependencies.py` as a `Dependency` in the `FRONTEND`
   group, with its `pinned_version` and one `VendorAsset` per file it needs.
   Keep the sub-directory layout the library expects of itself : a stylesheet
   that asks for `fonts/…` or `images/…` needs those files at that relative
   path.
2. Get the digests with `python manage.py vendor_assets --print-hashes` and
   paste them into the declaration. The download is refused if they do not
   match.
3. Mirror the files locally with `python manage.py vendor_assets`.
4. Load it in the template with `{% static "vendor/<library>/<file>" %}` - no
   version in the path, no `integrity` attribute (the file is same-origin and
   was verified when it was fetched).

Upgrading is the same list : change the version, re-run `--print-hashes`, paste,
then `vendor_assets --force`. The tests check that the pinned version is the one
the declared URLs actually fetch, and that every `vendor/…` path a template asks
for is a file something mirrors.

## Compose, never re-type

A screen is assembled from [the component framework](ui-components.md) :
`page_header`, `detail_layout`, `section_card`, `meta_list`, `kpi_tile`,
`record_card`, `choice_badge`, `tag_list`, the shared form and delete shells.
Hand-written card, `<dl>`, badge-colour or form-field markup is a review finding
: the same information then looks different from one page to the next, and a
fix made in the component never reaches the copy.

## Detail pages : cards, not tabs

Use `{% detail_layout %}` : a stack of `section_card` in the main column, and a
rail of at most four `kpi_tile` (the lifecycle stage first). The rail sits above
the content on narrower screens and becomes a sticky right-hand column on wide
ones. Group the content into stacked cards, collapsible where it is secondary,
and close the page with `{% record_card obj %}`.

Tabs hide content and cost the reader a click to discover what they do not know
is there. Use them only where the views are genuinely distinct modes, as the
compliance assessment does with Planning, Findings and History.
`compliance/templates/compliance/action_plan_detail.html` is the reference
implementation, and [the detail anatomy](ui-components.md#detail-page) gives
the rules for header actions, the rail and the order of the sections.

## Forms and deletion

Every form is the modal shell (`includes/modal_form.html`), and its full-page
fallback is one line : `{% extends "includes/page_form.html" %}`. A delete
confirmation extends `includes/confirm_delete_modal.html` or
`includes/confirm_delete_page.html`. Cancel is always neutral and on the left,
and the primary or destructive action is on the right. The doctrine is in the
[brand guidelines](../brand/brand-guidelines.md#forms).

## Lifecycle transitions

Add `LifecycleStepperMixin` to the DetailView, include the shared template:

```django
{% include "includes/lifecycle_stepper.html" %}
```

It renders done, current, next and future steps, the permission-aware next step,
refusal and rework through clickable earlier pills, the archived off-ramp, and
the comment modal for transitions that require one. State badges use
`{% workflow_badge obj %}`.

Never a plain button, never a status dropdown, never per-page stepper markup.
Each of those reintroduces on one page the divergence the engine exists to
prevent, and each is invisible until an auditor finds the page where the gate
was missing.

## Lists

`SortableListMixin` gives server-side sorting with the user's choice persisted
in `User.table_preferences`, so a sort survives navigation and devices. Combine
it with `ScopeFilterMixin` for tenancy.

Table conventions, column order, alignment, density, are in
[brand/table-standard.md](../brand/table-standard.md).

## Both themes, always

Every component must render correctly in light and dark. Use Bootstrap semantic
classes and the brand's CSS custom properties; never hardcode a colour value.

Check both before calling a change done. A component that only works in the
theme you happen to use is half a component.

## Mobile

Test narrow viewports, and pay attention to the three things that break first :
multi-select widgets, sticky bars and form layouts.

## Icons

[Bootstrap Icons](https://icons.getbootstrap.com/), exclusively. No second icon
set, no inline SVG for something the set already has.

## Strings

Wrapped with `{% trans %}` or `{% blocktrans %}`, with the French entry added in
the same change. A literal string in a template is a bug even when it is an
English word that reads fine. See
[internationalisation](../technical/internationalization.md).

## HTMX

Partial updates return a fragment, not a full page. `django-htmx` puts
`request.htmx` on the request so a view can serve both. Keep the fragment's
template separate rather than branching inside one template with a conditional
wrapper.

Boosted navigation means a page can be swapped into an existing document rather
than loaded fresh. Anything that initialises on page load has to survive that,
which is the usual cause of "it only works after a hard refresh".

## Accessibility

The commitment is WCAG 2.2 AA. In practice, on a new screen: every control has
an accessible name, focus is visible, colour is never the only carrier of
meaning, and motion honours `prefers-reduced-motion`.

## Checklist

- [ ] Built from the [components](ui-components.md) : no hand-written card, `<dl>`, badge colour or field markup
- [ ] No inline `style` for a fixed visual choice (use a component or a utility class)
- [ ] Empty values show the dash (`{% dash %}`, `|or_dash` or a component that applies it)
- [ ] Detail page uses `detail_layout`, ends with `record_card`, tabs only if genuinely distinct modes
- [ ] Forms extend the modal shell, and their page fallback extends `includes/page_form.html`
- [ ] Lifecycle transitions go through the shared stepper
- [ ] Lists use `SortableListMixin` and `ScopeFilterMixin`
- [ ] Renders correctly in light and dark
- [ ] Checked on a narrow viewport
- [ ] Bootstrap Icons only
- [ ] Every string wrapped and translated
- [ ] Works after a boosted navigation, not only a hard refresh
- [ ] Controls named, focus visible, colour not the only signal
