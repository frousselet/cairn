# Brand guidelines v2 (proposal)

**Status : proposal.** This is the visual system the redesign proposes. Until
the migration described in the [redesign proposal](README.md) lands, the
reference for the running product stays the
[current brand guidelines](../brand-guidelines.md); the first lot of the
migration promotes this page in its place.

The system is built on [Basecoat](https://basecoatui.com/introduction), the
shadcn/ui design system rewritten in plain HTML and CSS. Basecoat supplies the
components; this page says how Cairn uses them, and what Cairn adds on top.

## 1. The idea

A cairn is a pile of stones that marks a path. The product does the same for a
security programme : it shows where you stand, what comes next, and how far
you have come. The visual system follows from that.

- **Guide.** Every page answers one question and offers one main action.
- **Make it readable.** Hierarchy comes from type and space, not from boxes.
- **Show progress.** States, levels and steps are always visible, in words.

The product remains audit-grade : sober, precise, bilingual. "Sober" means
no decoration that carries no information, not "grey".

## 2. Logo

| File | Use |
| --- | --- |
| [mark.svg](logo/mark.svg) | The mark on a light background, 24 px and above |
| [mark-reversed.svg](logo/mark-reversed.svg) | The mark on a dark background |
| [mark-mono.svg](logo/mark-mono.svg) | One colour (Cairn Blue), for single-ink uses |
| [mark-sm.svg](logo/mark-sm.svg) | 22 px and below : three chunkier stones, wider gaps |
| [app-icon.svg](logo/app-icon.svg) | The application tile : sidebar, home screen, touch icon |
| [favicon.svg](logo/favicon.svg) | The browser tab |
| [wordmark.svg](logo/wordmark.svg), [wordmark-reversed.svg](logo/wordmark-reversed.svg) | "Cairn" alone |
| [lockup.svg](logo/lockup.svg), [lockup-reversed.svg](logo/lockup-reversed.svg) | Mark and wordmark together |

**Construction.** Four stones stacked on a 32-unit grid, each a pebble
outline (domed top, flatter base), each turned a few degrees so the stack
reads as balanced rather than mechanical. The stones darken from the top to
the base : the base is what the rest stands on. The small mark keeps three
stones, offset left and right, so the stack never reads as a head and
shoulders at favicon size. The wordmark is "Cairn" in Geist SemiBold,
vectorised, so it renders without the font installed.

**Clear space.** Half the height of the mark on every side.

**Never** : stretch or rotate the mark, recolour one stone, set the wordmark
in another face, put the light mark on a dark background (use the reversed
files), or use the full mark below 24 px.

**White label.** An instance that uploads its own logo shows it in place of
the tile (`CompanySettings.use_logo_as_app_brand`); the wordmark is then the
company's application name, set live in Geist SemiBold.

## 3. Colour

All colours are tokens, defined once in
[cairn-theme.css](theme/cairn-theme.css) for the light and the dark theme.
They follow the shadcn/ui variable names Basecoat reads, plus a few Cairn
additions. A fill is never used as a text colour, and no text is quietened
with an opacity.

### Identity

| Token | Light | Dark | Use |
| --- | --- | --- | --- |
| `--primary` | `#2449D8` | `#8AA4FF` | Primary buttons, the selected state, focus ring |
| `--primary-foreground` | `#FFFFFF` | `#09090B` | Text on a primary fill |
| `--primary-text` | `#2449D8` | `#8AA4FF` | Links and text in the identity colour |
| `--primary-soft` | `#EEF2FE` | `#1D2547` | Selected rows, the current step of a progress |

Cairn Blue replaces the navy `#1E3A8A` of v1 : brighter, so the product
stops reading as a bank statement, and still 6.95:1 on white.

### Neutrals : zinc

Cool neutral greys from the Tailwind *zinc* scale. No surface carries a warm
tint : no yellowish background in the light theme, no brownish one in the
dark theme.

| Token | Light | Dark |
| --- | --- | --- |
| `--background` (page) | `#FAFAFA` | `#09090B` |
| `--card`, `--popover` | `#FFFFFF` | `#18181B` |
| `--muted`, `--secondary`, `--accent` (hover surface) | `#F4F4F5` | `#27272A` |
| `--foreground` | `#18181B` | `#FAFAFA` |
| `--muted-foreground` | `#6B6B73` | `#A1A1AA` |
| `--border` | `#E4E4E7` | `#2E2E33` |
| `--input` (light fills, as Basecoat uses it) | `#D4D4D8` | `#3F3F46` |
| `--control-border` (control boundary, 3:1) | `#85858D` | `#7A7A83` |
| `--sidebar` | `#F4F4F5` | `#111113` |

Basecoat uses `--input` both for control borders and for light fills
(`bg-input/30`). The theme keeps `--input` light for the fills and gives the
boundary of every form control `--control-border` : a control must be found
at a glance, and WCAG 1.4.11 asks 3:1 for its boundary.

### Status

Each status has an ink for text and marks, a soft fill and a border. Status
colours carry a meaning and are never decoration; a status always shows its
word, and an icon where space allows. A yellow or brown fill is never used :
warning, and danger in the dark theme, sit on the neutral surface and carry
their colour on the text, the dot and the border.

| Status | Ink light | Ink dark | Fill light | Fill dark |
| --- | --- | --- | --- | --- |
| Success | `#047857` | `#34D399` | `#ECFDF5` | `#0F2A21` |
| Warning | `#B45309` | `#FBBF24` | none (card) | none (card) |
| Danger | `#B91C1C` | `#F87171` | `#FEF2F2` | none (card) |
| Info | `#0369A1` | `#38BDF8` | `#F0F9FF` | `#0C2533` |

### AI

Violet is reserved for what the model wrote, and for nothing else : an
auditor sees at a glance which sentence comes from the assistant.

| Token | Light | Dark |
| --- | --- | --- |
| `--ai` (text) | `#6D28D9` | `#C4B5FD` |
| `--ai-mark` (icon, outline) | `#7C3AED` | `#A78BFA` |
| `--ai-soft` | `#F5F3FF` | `#241B3D` |
| `--ai-border` | `#DDD6FE` | `#4C3A86` |

### Risk levels

The colours of the risk levels are the ones the administrator typed in the
risk criteria (`RiskLevel.color`). Matrices and level chips show them as they
are, and compute the label colour with `core/colors.py`. The brand never
overrides them, and never spreads them over an area : an empty matrix cell is
neutral, a cell takes its level colour once it holds a risk, and the bands of
the treatment flow are grey between their coloured level bars.

### Contrast, computed

Every text token was measured on every surface it can sit on, in both themes
(script in the proposal, same formula as `core/tests/test_contrast.py`).
Lowest ratio of each, all at or above WCAG AA :

| Text | Light | Dark |
| --- | --- | --- |
| `--foreground` | 15.83:1 | 14.27:1 |
| `--muted-foreground` | 4.81:1 | 5.81:1 |
| `--primary-text` | 6.22:1 | 6.27:1 |
| `--success` | 4.99:1 | 7.75:1 |
| `--warning` | 4.57:1 | 8.92:1 |
| `--danger` | 5.89:1 | 5.38:1 |
| `--info` | 5.40:1 | 6.95:1 |
| `--ai` | 6.46:1 | 8.07:1 |
| Label on `--primary` | 6.95:1 | 8.37:1 |
| `--control-border` boundary (3:1 needed) | 3.51:1 | 4.17:1 |
| `--ring` focus (3:1 needed) | 6.66:1 | 7.45:1 |

## 4. Typography

One family, **Geist** (OFL-1.1, the default face of Basecoat), and its mono
companion **Geist Mono**, both served by the instance as variable fonts.

| Role | Size / line height | Weight |
| --- | --- | --- |
| Page title (`h1`) | 28 px / 1.2 | 600, tracking -0.015em |
| Section title (`h2` in a card) | 15 px / 1.3 | 600 |
| Body, controls, table cells | 14 px / 1.5 | 400 (500 for names and labels) |
| Helper, meta, captions | 12 to 13 px | 400 |
| Key figure (KPI) | 28 px, 44 px for the one headline figure | 600 |
| Reference (`RISK-1`) | Geist Mono 12 px | 500 |

- Figures that line up take tabular numerals (`.tabular-nums`, `.num`).
- Titles are sentence case; no uppercase anywhere except keyboard keys.
- Running text stays under 80 characters per line.

## 5. Layout

- **Shell.** A sidebar (Basecoat `.sidebar`, 264 px, collapsible, a sheet on
  a phone) holds the navigation of `core/navigation.py`. A thin top bar holds
  the breadcrumb, the search, Ask Cairn, the notifications and the theme : the
  breadcrumb no longer disappears when the page header compacts.
- **Pages.** A page starts with its header : title, its facts, its actions on
  the right. Dashboards and registers use the full width; a record page caps
  at 1 728 px with a 352 px rail.
- **Radius.** `--radius` is 8 px (Basecoat Nova derives the rest from it).
- **Elevation.** Cards are a 1 px ring, no shadow; a shadow means something
  floats (menu, popover, dialog, palette).
- **No accent bars.** A card is never marked by a coloured left border; a
  state is a badge with its word.

## 6. Iconography

[Lucide](https://lucide.dev) (ISC), the set Basecoat and shadcn/ui use,
replaces Bootstrap Icons. Icons are inline SVG from a sprite, 16 px in
controls, 2 px stroke, `currentColor`. A decorative icon is
`aria-hidden="true"`; an icon-only button carries an `aria-label`.

## 7. Components

Basecoat provides the components, in its **Nova** style (compact spacing,
8 to 12 px radii). Cairn adds only what the product needs and Basecoat lacks.

| Cairn need | Basecoat component | Cairn addition |
| --- | --- | --- |
| Buttons | `.btn` with `data-variant` and `data-size` | `data-variant="success"`, `"warning"` |
| Status of a record | `.badge` | `data-variant="success"`, `"warning"`, `"danger"`, `"info"`, `"ai"`; the lifecycle badge (dot and word) |
| Section card | `.card` with `header` / `section` / `footer` | Count beside the title, section *Edit* button |
| Forms | `.field`, `.label`, `.input`, `.select` | Required meter, named errors, scope tree |
| Dialog (create, edit, delete) | `dialog.dialog` (native `<dialog>`) | Opened by `window.cairnActions`, never an inline handler |
| Menus, popovers | `.dropdown-menu`, `.popover` | Row actions, AI explanation |
| Command palette | `.command` | Ask Cairn row and answer |
| Navigation | `.sidebar` | Sections and their entries from `core/navigation.py` |
| Lifecycle | None | The lifecycle bar : completed steps folded to ticks, current step as its badge, the next transition as the only filled button, exits on the right |
| Key figures | None | KPI tile (label, figure, unit, sparkline), rail tile |
| Risk | None | Level chip (administrator colour and word), matrix 5 x 5 |

**One primary action.** On a record page, the next lifecycle transition is the
only filled button; *Edit* is outlined. On a list, the creation button is the
filled one; a register that cannot create (risks come from assessments) has
none.

## 8. Data visualisation

Charts follow the dataviz method used for this proposal : choose the form
first, colour last, validate the palette by script.

- **Categorical palette** (`--chart-1` to `--chart-5`), in this fixed order :
  `#2a78d6`, `#eb6834`, `#1baf7a`, `#eda100`, `#e87ba4` (light);
  `#3987e5`, `#d95926`, `#199e70`, `#c98500`, `#d55181` (dark). Validated for
  colour-vision deficiencies on the Cairn card surfaces (worst adjacent CVD
  distance 9.1 light, 8.4 dark). Three light slots are under 3:1 on white :
  charts that use them carry direct labels.
- **Ordinal ramp** for ordered steps (lifecycle distribution) : one blue hue,
  light to dark, nine steps.
- **Status** colours only for statuses (compliant, non-compliant); *not
  applicable* is a texture, *not assessed* a neutral.
- A single series has no legend, its title names it; two or more have one.
- Text in a chart wears text tokens, never the series colour.
- Work not started is not a red 0 % : a framework with no requirement says
  *No requirements yet*.

## 9. AI presence

- Text written by the model sits on the AI soft surface and carries the
  **AI label** (violet pill with a sparkle). The label opens a popover that
  says what the model received, which provider and model answered, and how
  often it runs, an idea taken from IBM Carbon for AI.
- The attribution line stays under the text, as the product writes it today.
- Records shown with an answer are built by the server, never by the model,
  and the tools the assistant consulted are listed by their labels and counts,
  never their arguments.
- What the server computes (links, counts, audits) is never marked AI.
- Violet is never used for anything else, including as a chart colour.

## 10. Motion

Durations 150, 220 and 320 ms with `--ease-out`; nothing longer than 400 ms
and nothing perpetual. `prefers-reduced-motion` reduces every transition to
nothing.

## 11. Accessibility

WCAG 2.2 AA in both themes, checked, not assumed : contrast computed on the
tokens (section 3), axe-core on every mockup in both themes at desktop and
phone width, and the same three checks as v1 once migrated
(`core/tests/test_contrast.py`, the markup audit of the interface sweep,
`scripts/a11y_audit.py`). Focus is a 2 px ring in `--ring`. Controls have
accessible names; touch targets are at least 24 px. The product's
conformance statement (`core/accessibility.py`) is not changed by this
proposal.

## 12. Voice and tone

Unchanged from v1 : sober, precise, action-oriented, bilingual, one thing
one name (`docs/brand/glossary.md`). An action names its object
(*Assign an owner*), a button carries its word (*Create*, *Save*, *Cancel*),
a helper says what its label does not, and no sentence circles around what it
means.

## 13. What changes from v1

| Topic | v1 | v2 |
| --- | --- | --- |
| Components | Bootstrap 5.3 restyled by 6 004 lines of Cairn CSS | Basecoat (Nova), Bootstrap kept for its grid and utilities only |
| Identity colour | Navy `#1E3A8A` | Cairn Blue `#2449D8` |
| Neutrals | Zinc greys, unequal across the stylesheets | Zinc greys from one token set, no warm tint |
| Typeface | GitLab Sans, titles at 810 | Geist and Geist Mono, titles at 600 |
| Icons | Bootstrap Icons | Lucide |
| Logo | Navy tile, arc and three bars | Four stacked stones; tile for the app icon |
| Shell | Sidebar only, header compacts | Sidebar and a top bar that always shows the breadcrumb |
| KPI tiles | Coloured left border | Plain tile, state as a badge |
| AI | "AI" badge in the palette | AI label, violet reserved, explainability popover |
| Record page | Two blue buttons (*Edit*, transition) | The transition is the only filled button |
