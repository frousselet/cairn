# Changelog

All notable changes to Cairn (formerly Fairway) are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **First-run onboarding screen.** While the instance has no users (a brand-new database), every request is funnelled to a standalone, login-styled onboarding screen (`core.middleware.OnboardingMiddleware`). When the schema has pending migrations it **applies them automatically** behind a **full-screen progress bar** showing the step counter and current migration name - on a fresh database ("Setting up the database") *and* on an upgrade of an already-initialised instance ("Updating the database", which returns to the app when done). On a fresh database it then offers two paths: **Start from scratch** (a two-step wizard - **step 1 configures the company** via `CompanySettingsForm`: name, application name, assistant name, accent colour, logo and address, all optional; **step 2 creates the first super-admin** - with a side rail carrying the vertical stepper and the navigation buttons) or **Start with sample data** (runs the Voltara Energy demo seed behind the same progress bar, then auto-logs-in as the seeded admin and lands on the dashboard). Both jobs run on a background thread and report progress through a process-global store polled over a tiny **DB- and session-free JSON endpoint** - deliberately not a WebSocket, because on a fresh database the session/auth tables a WebSocket would need do not exist yet during the migration phase; the bar surfaces an error if the backend connection drops. The seed (`scripts/seed_demo_data.py`) gained a `_phase()` helper so each phase reports progress while staying a plain `print` on the shell path. The "Start from scratch" wizard writes **nothing to the database until the administrator is created**: the company step is held in the browser (`sessionStorage`, cleared on submit, passwords never stored) and sent in a single request that creates the super-admin and persists the company settings together in one `transaction.atomic()` block. The flow is hard-gated (every action re-checks `is_first_run()` server-side; auto-login is gated to the session that launched the seed), and is intentionally UI-only (a pre-authentication bootstrap has no place on the authenticated API/MCP surfaces). Once the instance is initialised and the schema is up to date, the onboarding screens are unreachable.
- New **Documents** area in the Assets module, starting with **Contracts**. A contract is a first-class scoped entity running the standardised lifecycle engine (`core.lifecycle`, like Suppliers and Scopes, rendered with the directed-graph stepper): Draft (generic entry) -> Contract draft -> Under signature -> In force, with a recurring review cycle (In force <-> Under review), Expire (an expired contract is replaced by a new one via "annule et remplace", not renewed in place), and Archive (from any state). Parties are the union of supplier parties and client (customer stakeholder) parties, amendments (avenants) as child contracts shown nested under their parent in a scope-style **hierarchical list**, a "cancels and replaces" ("annule et remplace") link between contracts/amendments (the superseded one is kept for traceability and flagged), and a single attached **PDF** stored inline in the database and served through a permission-checked, scope-filtered download view (strict validation: `.pdf` extension + `%PDF-` magic bytes + 25 MB cap). Full vertical slice: web CRUD with the generic workflow stepper and a 2-column detail page, DRF API (`/api/v1/assets/contracts/`, `document_url` exposed but never the raw bytes), MCP tools (`list/get/create/update/delete/approve/transition_contract`, parties via `scope_ids`/`supplier_ids`/`client_ids`; PDF upload is web-only), `assets.contract.*` permissions, a new Documents sidebar group, demo seed data, and module documentation. Automatic PDF content extraction via Ask Cairn is left as a clean seam for a later iteration.
- **Certificates** in the Documents area, sibling to Contracts, to store and historise the company's own certificates (ISO/IEC 27001, HDS, SOC 2, ...). Each certificate is **attached to the framework (référentiel) it attests compliance to** (a `compliance.Framework`, `PROTECT` on delete, required at the form / API / MCP layers), and records the certification body (`issuer`, distinct from the framework's issuing body), the certificate number, the issue / expiry dates, and the certified perimeter (free-text `scope_statement` + covered **Sites**). It runs the standardised lifecycle engine (`core.lifecycle`, directed-graph stepper): Draft -> Assessment (certification audit) -> Certified, with a recurring recertification cycle (Certified <-> Under renewal) as the only non-terminal branch; Suspended and Expired are **terminal** outcomes of the renewal (no reinstatement, no renewal in place - re-certifying means a new certificate that supersedes this one via "annule et remplace", so the history is kept), and Archive is the from-any exit. A single attached **PDF** is stored inline and served through a permission-checked, scope-filtered download view (`.pdf` + `%PDF-` magic bytes + 25 MB cap). Full vertical slice: web CRUD with the generic workflow stepper and a 2-column detail page, DRF API (`/api/v1/assets/certificates/`, `framework_label` and `document_url` exposed but never the raw bytes; filters `status`/`framework`/`site`/`expiry_before`/`expiry_after`), MCP tools (`list/get/create/update/delete/approve/transition_certificate`, framework/scopes/sites via `framework_id`/`scope_ids`/`site_ids`; PDF upload is web-only), `assets.certificate.*` permissions, a Certificates entry in the Documents sidebar group, demo seed data, and module documentation.

### Changed

- **Sites migrated to the new lifecycle engine** (`core.lifecycle`, like Scopes and Suppliers). A site now runs the operational location lifecycle `Draft -> Commissioning -> Operational`, with a periodic review cycle (`Operational <-> Under review`), a `Decommissioned` off-ramp from service, and `Archived` as the from-any exit (restoreable to Draft). Only the `operational` and `review` steps count in reports and are linkable, mirroring the governance the legacy default workflow expressed (the validated-equivalent state). The detail page now renders the directed-graph lifecycle stepper; the REST `.../transition/` action and the `transition_site` / `site_allowed_transitions` MCP tools route through the lifecycle service (which records a `LifecycleEvent` per move), and the demo seed places the Voltara sites across the operational / review / commissioning steps.
- **Site detail page redesigned on the standardised 2-column layout** (the Scope / Supplier pattern): a hero overview with the site's address plotted on a theme-aware map and icon-led info rows (type, parent site, address), sub-sites as cards, hosted support-asset and supplier dependencies, an audit-metadata card, and a sticky KPI rail (lifecycle stage, sub-sites, hosted assets, supplier dependencies). The page header now carries the site-ancestry breadcrumb and the edit action opens the form drawer.
- Sites sidebar entry flattened to a direct link: the single-item **Sites** collapsible group in the Assets section is now a top-level sidebar link (matching the Roles / Activities pattern), and its breadcrumb drops the redundant intermediate group (`Assets > Sites` instead of `Assets > Sites > Sites`).
- The DRF `.../transition/` API action is now lifecycle-engine aware: for entities on `core.lifecycle` (Scope, Supplier, Contract, Certificate and now Site) it lists and applies the real lifecycle steps instead of the legacy default-workflow states.
- The scope detail hero map now plots a point per site across the whole perimeter subtree: the scope's own included sites plus the included sites of every sub-scope (descendants), deduplicated, so a parent perimeter's map shows the full geographic footprint. The "Included sites" badges still list the scope's direct sites only.
- Startup migration sequencing now defers to the onboarding screen on a fresh database so migration progress is visible in the browser. The Docker `entrypoint.sh` only auto-migrates when the instance is already initialised (an upgrade, i.e. users exist) or when a super-admin is provisioned via `DJANGO_SUPERUSER_*` env vars; an empty database starts the web server first and the onboarding screen applies the migrations with a live progress bar. The VS Code debug flow follows suit: the `stack: bootstrap` preLaunchTask now only compiles translation catalogs (no migrate/seed), so pressing F5 on an empty `db.sqlite3` lands on the onboarding screen (a new `stack: migrate` task is available for manual CLI migration).
- Demo seed (`scripts/seed_demo_data.py`) now derives every date from the current date instead of hardcoded 2024-2027 literals, so the dataset never goes stale: five audits are completed and spread across the past months, plus three that are deliberately in progress (distinct assessors, distinct date ranges, only a fraction of controls reviewed so far) so the "in progress" state is always represented without any stale or empty future-planned assessment; contracts and reviews keep realistic horizons, and year-bearing labels (audit names, management-review semesters, SWOT, EBIOS cycle) are computed at seed time. Bulk closed/completed action and treatment plans now get a completion date, overdue plans a past target, and expired risk acceptances a past validity, so status and dates stay consistent.
- Demo seed now sets real addresses and coordinates on every supplier (curated and bulk), so the supplier hero maps and scope site maps render correctly on a fresh seed without manual fixes.
- Scopes migrated to the new lifecycle engine (`core/lifecycle.py`), running the perimeter lifecycle Draft -> Definition -> Validation -> In force -> Review (periodic, looping back to In force), Archived as the from-any exit; `in_force` and `review` scopes count in reports and are linkable.
- Scope detail page redesigned on the standardised detail layout (piloted on suppliers): a hero overview with the perimeter's included sites plotted on a theme-aware map, icon-led info rows (dimensions, parent, in-force dates), manager cards, sub-scope cards, and a strategic KPI rail (compliance rate, objectives, essential assets, sites) with one accent colour per tile.
- Governance helpers (`reportable` / `linkable` / `deletable_states`), the list summary rail, the state badge and the unified history timeline are now lifecycle-engine-aware, resolving a model's steps when it sets `LIFECYCLE_NAME` (fixes raw-code badges and missing rail tiles for standardised-engine entities).
- Generic MCP `transition_<entity>` / `<entity>_allowed_transitions` tools route standardised-engine entities through the lifecycle service (previously default-workflow only).
- Lifecycle graph renderer given more breathing room (wider pill gaps, higher loop-arc clearance) so short single-step loops (e.g. a periodic Review) read as airy arcs instead of cramped bumps.
- History trigger is icon-only (clock icon + tooltip).
- Suppliers migrated to the new lifecycle engine (`core/lifecycle.py`), running the supplier-risk lifecycle; old status workflow and title-bar Archive/Restore removed.
- New `LifecycleStepperMixin` and stepper template render any lifecycle; cyclic ones draw as a responsive snake-flow graph with schema-derived SVG arrows.
- Detail page layout standardized (Suppliers pilot) : responsive `.detail-layout` grid with a sticky metadata rail; empty fields hidden, native confirm replaced by a frosted modal.
- Workflow stepper restyled : single centred line on the page, backward moves via clickable earlier pills, detached branch states.
- Supplier lifecycle merged with its status into one workflow (`assets/workflows.py`); default moves to under_evaluation, title-bar action toggles Archive/Restore.
- Rich-text editor replaced (Jodit -> pell) : dependency-free, frosted styling, clean semantic HTML, DOMPurify-sanitized.
- Multi-step form nav moved outside the modal : two floating arrows, no Cancel button, smooth height morph on step change.
- Modals aligned with the frosted system (page-tinted blur backdrop, hairline border, soft shadow).
- Buttons redesigned as a solid frosted system : navy primary, glass neutral, semantic fills, standardized Cancel-left / action-right placement.
- Full-bleed page headers : title bar spans the full main width while content stays aligned.
- Dependency graph switched to a layered `dagre` layout with an Orientation toggle (LR / TB), preserving colours, logos, SPOF edges and zoom.

### Added

- Supplier contacts : multiple named `SupplierContact` records with inline CRUD, plus REST and MCP.
- Supplier address with map : Photon autocomplete storing lat/long, rendered on a theme-aware Leaflet hero map, exposed via REST and MCP.
- Supplier compliance evaluation : one table merging type-inherited and direct requirements, with an Evaluate modal (level + evidence), an evaluation history, and REST + MCP.
- "Last modified by" chip in detail headers (who and when).
- `page_header` gains a `logo` option to render an entity logo before the title.
- Contracts as an autonomous multi-party entity (v1) : new `Contract` model with many-to-many suppliers and self-referential amendments, rendered as cards on the supplier page.
- Standardised lifecycle architecture (foundation) : model-free engine (`core/lifecycle.py`) with declarative steps, transitions and an immutable `LifecycleEvent` log.
- Dependency graph cascade highlight : clicking a node spotlights its full upstream/downstream chain and dims the rest.
- Compact page header for full-height pages : `page_header` gains `compact=True`; the dependency graph opts in.
- Risk-driven applicability for compliance requirements : `Framework.applicability_managed_by_risks` derives each requirement's applicability from linked risk states, exposed via UI, REST and MCP.

### Fixed

- Site form and detail page no longer reference a non-existent `status` field (a stale leftover that rendered an empty required control on the full-page form and a broken status badge on the detail page).
- Assorted GUI input no longer triggers unhandled exceptions (issue #158) : the dashboard WebSocket consumer guards against a valid-JSON non-object frame (was `AttributeError` -> socket close 1011); the framework cascade delete tolerates an already-deleted section/framework relation (was `DoesNotExist`); the action-plan comment, dashboard indicator-toggle, calendar-subscribe revoke and Trust Center download-token paths validate their UUID input; and indicator measurement values reject `nan` / `inf` at input while `_format_number` no longer crashes on a stored non-finite value.
- Global search and the list toolbar search now clamp the `?q=` length (issue #156) : an unbounded query (~50k chars) built an equally long SQL `LIKE` pattern, raising `OperationalError` on SQLite (HTTP 500) and acting as an unbounded-work DoS vector on any backend. The query is truncated (128 chars) before it reaches the database, on both the global search endpoint and the shared `PredefinedFilterMixin` toolbar search.
- Advanced "filter on any field" builder (`AdvancedFilterMixin`, every list page) no longer returns HTTP 500 on a malformed `?rule=` value (issue #155) : a non-object rule (e.g. `?rule=5`) is ignored, relation values are validated against the related primary-key type (a non-UUID for a UUID PK or an oversized integer for an integer PK is dropped), and an out-of-calendar date (`2024-02-30`) or non-finite number is treated as no value. A shared `SavedFilter` carrying such a rule no longer breaks the list for everyone it is shared with.
- List and detail views no longer return HTTP 500 on a malformed query/POST parameter (issue #154) : a new `core.query_params` helper (`parse_uuid` / `parse_int` / `parse_date_param`) coerces untrusted values before they reach the ORM, so an invalid value skips the filter instead of raising `ValidationError` / `ValueError` / `OverflowError` at query time. Covers the risk register (list, table-body, bulk action, Excel export), treatments, acceptances, threats, vulnerabilities, ISO 27005 and scale-choices endpoints, the compliance requirements list, the suppliers list (`?supplier_type=`) and the calendar feed (`?start=` / `?end=`).
- WebSockets now work under `manage.py runserver` : added `daphne` (first in `INSTALLED_APPS`, and to `requirements.txt`) so the dev server runs the ASGI stack instead of plain WSGI. Without it every `/ws/...` route (live dashboard and notification consumers) returned `404`; production (uvicorn `core.asgi:application`) was unaffected.
- Scope tree field layout / Firefox checkbox : multi-select widgets get the full-width layout, fixing the narrowed field and hidden first checkbox.

### Security

- Workflow transition API errors no longer return the raw exception string (CodeQL `py/stack-trace-exposure`) : the scope `archive`, compliance assessment / action-plan and management-review transition endpoints map known transition errors to safe, translatable messages via the shared `core.transition_messages` helper (promoted from `trust_center`).
- Open redirects closed (CodeQL `py/url-redirection`) : `Referer`-header and `next`-parameter redirects (the approval views in context / assets / compliance / risks, the login view and the OAuth authorize flow) are validated with a shared `core.redirects.safe_redirect_target` guard before redirecting.
- MCP JSON-RPC internal errors and the batch-create error path no longer echo raw exception text to the client (CodeQL `py/stack-trace-exposure`); the exception is logged server-side and a generic message is returned.
- Sidebar flyout menu built with DOM APIs instead of `innerHTML` string concatenation (CodeQL `js/xss-through-dom`).
- Onboarding logo preview validates the data URI before assigning it to `img.src` (CodeQL `js/xss-through-dom`, "DOM text reinterpreted as HTML"): `isSafeImageDataUri()` only accepts a base64 `data:image/...` URI, so a restored hidden-field value can never carry another scheme.
- CI `Tests` workflow pinned to least-privilege `contents: read` token permissions (CodeQL `actions/missing-workflow-permissions`).

## [0.32.0] - 2026-06-25

### Added

- Redesigned list-page chrome on every list page : a four-tile state KPI rail and a toolbar with search, Filters and Columns. Legacy per-page filter forms removed.
- Filter offcanvas with a combinable builder : multi-select facets, free-text operator rules, and a typed "any field" builder serialised to JSON.
- Reworked list pagination and search : HTMX numbered paginator (50 rows/page) and server-side `?q=` search, with quoted queries doing exact matches.
- Saved filters : name and re-apply a list's filters, personal or shared, backed by `SavedFilter` plus REST and MCP.
- Filters staged behind an Apply button with in-place HTMX refresh and a Reset action. Columns dropdown toggles and reorders columns, persisted per user.

### Changed

- List pages adopt the dashboard's main-area plus sticky side-rail layout, the rail carrying a Summary card with a per-state breakdown.

## [0.31.0] - 2026-06-25

### Added

- Configurable widget dashboard : edit mode with drag-to-reorder, resize, remove and an "Add a widget" gallery.
- Widgets use a `WxH` tile standard (1..4 each) with content autofitted to size; placeable as multiple instances, each with its own `params`.
- New Indicator widget replacing the grouped "Key indicators" block, configured and refreshed via a gear dialog.
- Compliance-by-framework and Objectives list widgets are sortable via a gear dialog (value, alphabetical, manual).
- Frameworks widget tightened : inline legend, condensed bar, not-applicable requirements shown.
- Overall-compliance bar made more prominent (gradient, glow, target marker) and configurable via a gear dialog.
- Dashboard split into a 12-column main area and a sticky side rail; widgets drag between zones in edit mode.
- Risk matrices split into `risk_matrix_current` and `risk_matrix_residual`, joined by Upcoming deadlines, Priority risks and Ongoing audits rail widgets.
- Summary widget : an LLM-synthesised daily briefing from the Ask Cairn assistant, fetched async and cached per user.
- Layout persisted per user on `User.dashboard_layout`, exposed via REST and `get_dashboard_layout` / `update_dashboard_layout` MCP tools.
- Section dashboard widget : a full-width bare heading to group widgets into labelled sections.
- Customisable Ask Cairn assistant name in company settings (`assistant_name`), exposed via REST and MCP.

### Changed

- Single typeface : GitLab Sans replaces the Inter + Space Grotesk pairing; hierarchy from weight (titles 810, KPIs 900).
- No negative letter-spacing on titles and indicators; positive tracking kept only on uppercase eyebrows and badges.
- Bootstrap bumped 5.3.3 -> 5.3.8 with refreshed SRI hashes.
- Softer page-header top fade : closely-spaced gradient stops and a progressive blur mask remove the banding lines.
- Indicator widget cards no longer lift on hover.

### Fixed

- Dashboard Summary briefing now follows the reader's language instead of always coming out in French.
- Management review held date and dashboard day-based counts now use `timezone.localdate()`, fixing skews near midnight.

## [0.30.0] - 2026-06-23

### Added

- Navigation breadcrumb in every page header, sourced from `core/navigation.py`.
- Animated Ask Cairn answer : reply types out letter by letter, honouring `prefers-reduced-motion`.
- Unified To do / Doing / Done Kanban board at `/kanban/`, with REST and the `kanban_board` MCP tool.
- Shared `{% progress_bar %}` tag with auto text contrast, applied across the main tables.
- Reusable `{% supplier_avatars %}` tag : overlapping logo stack with a `+N` chip.
- Two-line cell pattern rolled out across nearly all list tables and detail sub-tables (single-line primary, two-line clamped secondary).
- Dependency tables (site-supplier, site-asset, supplier, asset) adopt the pattern : merged Dependency / Type / Criticality cells (nine to six columns).
- Requirements table : inline number / framework / "Not applicable" badge, status over level, new Risks column (eleven to seven).
- Audits table : assessed frameworks, Dates over business-days duration, people-cell Assessor (eleven to nine).
- Action plans table : gap description, Priority badge with target date, people-cell Supervisor (ten to nine).
- Cross-framework mappings table : requirement reference over framework (seven to five).
- Frameworks table : 32px logo, "Mandatory" badge over type and category (nine to six).
- Risk register table : assessment and source, level under priority, decision under status, people-cell Owner, bulk bar removed (twelve to seven).
- Vulnerabilities and threats tables : inline "Catalog" badge over category (to seven columns).
- Risk acceptances table : justification, people-cell Accepted by, validity over acceptance date.
- Treatment plans table : risk and type, people-cell Owner, target over start date (ten to eight).
- Risk assessments table : methodology, people-cell Assessor, assessment over review date (nine to eight).
- Suppliers and supplier types tables : 32px logos, type under name, people-cell Owner, contract end with Expired badge (to seven / five columns).
- Sites table shows each site's address under the name.
- Asset groups table : type and member count, people-cell Owner (eight to six).
- Essential and support asset tables : category / type under name, people-cell Owner, merged C/I/A, EOL fold (to seven columns).
- Indicators tables : current over expected, merged Collection, title over format, per-row Trend sparkline.
- Activities table : parent activity, merged Criticality / type, people-cell Owner (eight to seven).
- Roles table : source standard, "Mandatory" indicator, new Responsibilities RACI column.
- Scopes table : effective over review date, scope icon, Version column removed (nine to seven).
- SWOT analyses table : analysis over review date, Validated by removed.
- Issues table : source, merged Category / type, merged Impact / trend (ten to eight).
- Stakeholders table : contact, merged Category / type, merged Influence / interest (ten to eight).
- Objectives table : category, people-cell Owner, target over review date (nine to eight).
- Users admin table : larger photo, name over email, job title over department (seven to five).
- Image-upload spinner overlay on profile photos and company / supplier / framework logos.
- `SPTY-N` reference surfaced on supplier types in the list, detail, admin and MCP tools.

### Fixed

- Search palette no longer blurry in Firefox.
- French UI no longer partly in English under the VS Code / mise dev setup.
- Warning-highlighted table rows now legible in dark mode.
- Sidebar brand no longer stale after a company logo / name change.
- CDN charts (d3 dependency graph, ECharts Sankey) now load on demand and render under boosted navigation.
- Dependency graph header brought to standard : `NAV_TREE` breadcrumb, full-size toolbar buttons.

### Changed

- Space Grotesk display typeface for titles and key figures (Inter remains the body face).
- Sidebar app name aligned with the compact page title.
- Sticky, frosted page title bar shrinking to a compact toolbar on scroll.
- Uniform detail and list page headers : shared breadcrumb surtitle and module accent.
- Unified outline button system : no solid fills, colour reserved for danger / warning / success.
- Redesigned search palette : split input and results cards, page-tinted backdrop.
- Frosted sidebar fades and centred collapse toggle.
- Action plans lose their dedicated Kanban board, now on the global board.

### Removed

- Per-app action-plan Kanban view, superseded by the unified global board.

## [0.29.1] - 2026-06-22

### Changed

- Uniform list tables app-wide : shared card-wrapped `table-hover`, toolbar, pagination, reference pill, Actions column, tags and empty state.

### Added

- New `{% user_avatars %}` tag : overlapping avatar stack with tooltips and `+N` chip, used for Scopes, action-plan assignees and Roles.
- Single-person columns now render via `{% user_badge %}` (photo + name) across asset, risk, assessment, treatment-plan and review tables.
- Pure-Python debugging setup without Docker via mise and `core.settings_local`, with an install guide and VS Code launch configs.

### Fixed

- Unread-notifications badge now uses `--accent-contrast`, staying legible for any accent in both themes.

## [0.29.0] - 2026-06-19

### Added

- Custom accent colour : `accent_color` company setting overrides the navy accent, clamped per theme, with REST + MCP.
- Custom application name : `app_name` company setting overrides "Cairn" in the sidebar and tab titles, with REST + MCP.
- Company logo as app brand : `use_logo_as_app_brand` toggle swaps the sidebar logo for the company logo, with REST + MCP.
- Dismissible "Today's actions" panel with per-user persisted state.

### Fixed

- Dashboard now counts achieved objectives in the progression panel.
- Changelog "Got it" dismissal now persists.

### Changed

- Dashboard indicators header tidied : Configure button moved into the page header.
- Risk widgets self-titled : Sankey and the two matrices carry their own card titles.
- Uniform 1.5rem gutter across all dashboard panels.
- "Compliance by framework" and "Active objectives progression" now sit side by side, equal-height.
- Sankey labels point inward and are tinted by severity.
- Refined risk-matrix heatmaps : cleaner rest state, hover ring/glow, shared styling across all three views.
- Design-system alignment pass on the ISO 27005 card, compliance bars, finding breakdown and support-assets register.

### Removed

- Leaner dashboard : Governance, Assets, Compliance and risk KPI stat cards dropped (counts stay in modules and API/MCP).

## [0.28.3] - 2026-06-18

### Changed

- Unified audit-grade entity history (`core.history`) : one timeline merging field changes, transitions and approvals, opened from a History off-canvas.
- Same history UI across context, assets, compliance, risks, reports and trust-center, replacing per-entity presentations.
- Action plan transitions and management review status history folded into the unified timeline.
- REST `…/history/` returns the unified timeline with `?limit=` / `?offset=` pagination.
- Generic `get_<entity>_history` MCP tool registered per entity, replacing the action-plan-only tool.

## [0.28.2] - 2026-06-16

### Added

- Manage role responsibilities from the UI : add, edit and delete via an HTMX drawer, with REST + MCP.
- Editing a role's responsibilities sends it back to draft for re-validation, except in terminal states.
- Generic CSV bulk import framework (`core/imports`) : an upload -> preview -> confirm wizard at `/imports/<entity>/`.
- Supplier CSV import : a modal validates and previews rows, resolves relations, and allows per-row replace.

### Fixed

- Role detail page crash : `user.username` referenced on the email-based `User` model now falls back to `user.email`.
- Dashboard "Active objectives progression" bars now render at 8px to match the compliance bars.
- Modal select dropdowns no longer clipped : TomSelect dropdowns attach to `<body>` above the modal.

## [0.28.1] - 2026-06-16

### Changed

- Administration menu reorganised into four permission-aware collapsible groups; Django admin link removed from the sidebar.
- Trust Center moved under Administration, with a "Manage content" link to curation.
- Frameworks menu simplified : direct list link plus an Import button opening the wizard in a modal.
- Self-documenting framework import samples : JSON `_instructions` and an Excel Documentation sheet listing fields and allowed values.
- Action plans kanban header adopts the standard "Compliance" eyebrow and module accent.

### Fixed

- Action plans kanban now positions correctly on first load, boosted swaps and resize.

## [0.28.0] - 2026-06-15

### Added

- Trust Center : public unauthenticated page at `/trust/` for security and compliance posture, with a dedicated `trust_center` app.
- Four content sections under a `trust_center_publication` workflow : certifications, subprocessors, security measures and documents.
- Dual publish gate : an item is public only when published and its source still validated; a global switch takes the whole Trust Center offline.
- Data-leakage safety : field-whitelisted public serializers, anonymous rate-limiting, streamed documents and SVG sanitization.
- Trust Center REST API under `/api/v1/trust-center/` (plus public `/trust/api/`), curation UI at `/trust-center/manage/`, and MCP tools.
- New `trust_center.*` permissions across the six system roles.
- Trust Center branding : company-name hero, favicon, accent `theme-color`, and rich-text intro and descriptions.
- Optional custom CSS in Trust Center settings, sanitized and injected into the public page.

### Changed

- Dependency graph header adopts the standard convention and merges stats, colour legend and zoom controls into one compact toolbar.

## [0.27.2] - 2026-06-15

### Added

- Dashboard risk treatment flow : Sankey chart above the matrices showing each risk moving from current to residual severity.
- Ask Cairn : OpenAI and OpenAI-compatible provider backend (`AI_ASSISTANT_PROVIDER=openai`).
- Ask Cairn : native Claude (Anthropic) provider, no semantic search.
- Ask Cairn : automatic semantic index maintenance with an Administration -> Semantic index page.
- Ask Cairn : new `list_supplier_requirements`, `list_supplier_dependencys`, `list_site_supplier_dependencys`, `list_sites`, `list_activitys` and `list_stakeholders` tools.

### Fixed

- Ask Cairn : SWOT analyses answerable via `list_swot_analysiss`, plus `owner_name` companions for "who is responsible" questions.
- Ask Cairn : `list_suppliers` gains a `type_name` companion, an `expired` filter and an `is_contract_expired` field.
- Ask Cairn : "how many" questions now report the real `total` count.
- Ask Cairn : status filters spell out allowed enum values to the planner.

## [0.27.1] - 2026-06-14

### Fixed

- Command palette no longer breaks under a French locale : palette JS strings are now escaped with `|escapejs`.
- Clearer error when the Mistral API key is missing : `MistralClient` validates `AI_ASSISTANT_API_KEY` up front.

## [0.27.0] - 2026-06-13

### Added

- Ask Cairn : optional AI question mode in the command palette (Ctrl+K) returning matching records and a short summary, off by default.
- Pluggable LLM provider : Mistral AI (EU-hosted, default) or self-hosted Ollama.
- Assistant routes questions to 24 read-only MCP tools as the requesting user, preserving permissions and scope filters.
- REST `POST /api/v1/assistant/ask/` and `ask_assistant` MCP tool.
- Thumbs up/down feedback per answer, stored as `AssistantFeedback`, browsable and JSON-exportable via REST and MCP.
- Feedback can be marked corrected to exclude it from future exports.
- Optional cross-language semantic requirement search (`semantic_search_requirements`), embeddings ranked by cosine similarity.
- `list_scopes` exposes a read-only `manager_names` field.

## [0.26.3] - 2026-06-12

### Added

- Company identity on the dashboard : configured name and logo replace the "Dashboard" title.
- Demo dataset seed script : `scripts/seed_demo_data.py` populates a full "Voltara Energy" company.

### Fixed

- Report download links no longer render as binary in the page.
- Calendar "Upcoming events" no longer shows negative day counts (#112), via `/api/calendar-upcoming/`.
- Search palette now translates navigation and quick-action labels per request.

### Changed

- Search palette contrast : near-opaque frosted surface, darker scrim, stronger group labels.
- README rewritten as a short overview, detailed content moved to `docs/`.
- Documentation screenshots retaken in 4:3 on the current brand.

## [0.26.2] - 2026-06-12

### Fixed

- Predefined compliance indicators now use shared `compliance.services`, matching the dashboard.
- Roles can be assigned from the UI : create / edit modal gains an "Assignment & status" step.

### Changed

- Fold SPOF warnings and calendar deadlines into the dashboard's Today's actions card.
- Move Reports and Management reviews under a new "Strategy" sidebar group.
- Forms adopt the sidebar design language : glass fields, `--field-*` tokens, restyled editor and pickers.
- Spread the sidebar design language across the UI : frosted glass, fading hairlines, sentence-case labels.
- Upgrade CI actions to Node 24 runtimes.

## [0.26.1] - 2026-06-11

### Changed

- Dashboard alerts become "Today's actions" : a calm to-do card grouped by priority, each linking to its page.
- Bolder overall-compliance score on the dashboard (weight 600 -> 700).
- Sidebar redesign : flat panel with a floating search field (Cmd/Ctrl K) and a user footer (Profile / Sign out).
- Search overlay entrance animation : FLIP morph from the sidebar field, disabled under `prefers-reduced-motion`.
- Everything moves into the sidebar : notifications and About join the user footer; the top-right bubble is removed.

## [0.26.0] - 2026-06-11

### Fixed

- Dashboard "Overall compliance" caption now counts only tracked requirements (`tracked_requirement_count`), with proper FR singular/plural.
- Modal step gating no longer blocks steps with filled rich-text fields.

### Changed

- Single sortable lifecycle Status column (`workflow_badge`) across all 27 list views, replacing bespoke status badges and the Approval column.

### Removed

- Legacy approval bar retired from all detail pages : the stepper's Validate step now carries the approval act.
- Publication `status` folded into the lifecycle for Scope, Site, SWOT analysis and Risk criteria, now carried by `workflow_state`.

### Added

- Lifecycle workflow documentation at `docs/modules/governance/workflow.md`.
- Workflow framework (`core/workflow.py`) : ordered states with governance flags, transitions, registry and permission-aware validation; ships the default 4-state lifecycle.
- Workflow data layer : `workflow_state` on `BaseModel` with model API and per-model assignment, backfilled from `is_approved`.
- Workflow report enforcement : SoA and risk register exclude non-validated elements.
- Workflow linking enforcement : pickers and MCP `link_*` / `set_*` tools only accept linkable, non-terminal elements.
- Generic lifecycle stepper and `workflow_badge` : `WorkflowStepperMixin`, a shared transition endpoint and a comment modal for refusals.
- Lifecycle stepper rolled out to every detail page, replacing the bespoke compliance, action plan and review steppers.
- Action plan workflow (`action_plan`) : 8-state machine from the transition constants, legacy contract and audit rows preserved.
- Compliance assessment workflow (`compliance_assessment`) from `ASSESSMENT_STATUS_TRANSITIONS`, with governance and statuses synced.
- Management review workflow (`management_review`, ISO 27001 9.3) : closure under `approve`, mandatory cancellation comment.
- Asset workflows (`essential_asset`, `support_asset`) : decommissioned assets stay reportable but not linkable or deletable.
- Risk-process workflows for risk, treatment plan, risk acceptance and vulnerability, encoding ISO 27005 progressions.
- Risk assessment workflow (draft -> in_progress -> completed -> validated -> archived) with a rework loop.
- EBIOS RM workflows for the six deliverables, each with deletion restricted to its initial state.
- Lifecycle transition API and MCP tools : REST transition endpoints, `?workflow_state=` filter, `transition_<entity>` and `<entity>_allowed_transitions`.
- Notification subsystem : `accounts.Notification` for per-user in-app alerts on submission, with localized post-commit email and opt-out.
- Notification surfaces : header bell with live unread badge, REST endpoints and MCP `list_notifications`, `mark_notification_read`, `mark_all_notifications_read`.

## [0.25.0] - 2026-06-11

### Changed

- Create / edit forms now open in a centered modal instead of an offcanvas drawer.
- Declarative step model for modal forms (`core.modal_forms`) : forms declare ordered `Step` groups covering every field.
- Modal shell auto-renders a stepper or completion meter, driven by generic JS and brand CSS.
- Multi-column rows in the modal form engine, with optional per-cell width.
- Modal form finishing touches : `modal_size`, capped rows per step, ARIA error count.
- Reusable `IconPickerWidget` extracted from the Scope icon picker.
- Reusable `ImageUploadWidget` generalised from the supplier logo upload, resizing to a 128px PNG data-URI.
- Tightened layouts across migrated forms with dense column rows.
- Forms migrated to the modal engine : Mapping, Role, context (8/8), assets (5/5), compliance (5/5) and risks (27/28 total).
- Form doctrine rewritten in the brand guidelines around a modal-first model.
- Modal form engine documented in the brand guidelines, `/styleguide` and README.

### Fixed

- Multi-step modal forms could not be submitted : forms now carry `novalidate` and gate validation per step.

## [0.24.5] - 2026-06-10

### Changed

- CI back on GitHub Actions : `ruff check` quality gate plus Docker Hub release publishing on version tags.

### Removed

- GitLab CI config and all GitLab references.

## [0.24.4] - 2026-06-02

### Fixed

- Fix migration `assets.0029` crashing on duplicate keys when converting site support assets into Site records.

## [0.24.3] - 2026-06-02

### Fixed

- Browser Back no longer gets stuck : history restores scoped to `#page-shell`, title synced on Back.
- Sidebar active highlight now follows Back / Forward.

### Added

- #70 : user-selectable theme (Light / Dark / System) via `User.theme_preference`, in profile, REST and a new `update_me` MCP tool, with FOUC-safe bootstrap.

## [0.24.2] - 2026-06-02

### Added

- MCP endpoint URL surfaced in the profile OAuth card and secret modal, with a copy button.
- `consolidate_iso27005_risk` MCP tool : materialises an ISO 27005 analysis into a `Risk`. Idempotent.
- `download_report` MCP tool : returns a report as base64; `list_reports` adopts the standard envelope.
- `Indicator.owner` plus objective/requirement traceability M2M, exposed via REST + MCP.
- Specifications restructured under `docs/modules/`, one file per entity, with a new Indicator spec.

### Changed

- MCP CRUD aligned with the data model on 30+ entities : `scope_ids` on every `ScopedModel`, full writable field sets everywhere (context, assets, risks, compliance).
- `Objective.progress_percentage` makes the `achieved` status reachable.
- Generic FK kwarg routing in MCP handlers : raw kwargs (`type=12`) rewritten to `_id` form.
- `_serialize_obj` expands M2M / reverse-FK to PK lists and preserves native types.
- `Risk.risk_source` enum aligned with `RiskSourceType`; `ThreatCategory` gains `OTHER`.
- SPOF flag made read-only on `site_asset_dependency` and `site_supplier_dependency`.

### Fixed

- #45 : closing a `ComplianceAssessment` no longer clobbers requirement statuses.
- #46 : `overall_compliance_level` excludes `NOT_APPLICABLE` requirements.
- #41 / #42 : section compliance propagates to ancestor sections.
- #48 : `RequirementMapping` auto-creates the symmetric inverse row, idempotently.
- #49 : `ComplianceActionPlan` M2M relations assignable through MCP via `*_ids`.
- #59 : `RiskTreatmentPlan` flips to OVERDUE when `target_date` is past.
- #60 : `RiskAcceptance` stamps `accepted_at` and `risk_level_at_acceptance` when active.
- #34 : `Supplier.type` ID resolution fixed end-to-end.
- #21 : `IndicatorMeasurement.recorded_at` is now user-writable for backdated imports.
- #27 : `SupportAsset.supplier` FK wired and exposed on MCP.
- #18 : `Activity.essential_assets` reverse manager exposed through MCP.
- #31 : `SiteType` enum values renamed from French to English; rows migrated.
- #30 : Site / `SupportAsset[type=site]` redundancy resolved; `Site` promoted to `ScopedModel`.
- WebSocket consumer no longer crashes on Redis read timeout (switched to PubSub channel layer).
- Boot warning about unapplied migrations silenced.
- Static files served under uvicorn in DEBUG mode.
- SPOF scheduler startup guard rewritten as an explicit allowlist.
- #51 / #43 / #47 : action plan Kanban, assessment divergences and lifecycle documented (no code change).
- #44 : `AssessmentResult.compliance_status` MCP schema exposes the full 11-value enum.
- #39 : `Requirement.compliance_status` keeps the 11-status enum; spec documents the mapping table.
- #35 : Suppliers module specified and SPOF / `redundancy_level` surfaced on MCP.
- #62 : filtered list pages no longer stay stuck on skeletons after browser Back.
- #64 : `HtmxFormMixin` distinguishes drawer requests from `hx-boost` soft-nav.
- #65 : table search field rebinds after HTMX partial swaps.
- #66 : browser Back no longer skips history entries for drawers, modals and detail tabs.
- #67 : WebSocket `setStatus` early-returns when the dot indicator is missing.
- #68 : threat / vulnerability "Manage" links preserve the analysis context via `?assessment=`.
- Browser Back regression : stale title and corrupted body cache after boosted nav fixed.

## [0.24.1] - 2026-05-31

### Fixed

- EBIOS backfill migration (`risks.0024`) : explicit per-model references and empty-reference healing fix a unique-constraint collision, making re-apply safe.

## [0.24.0] - 2026-05-31

### Changed

- Rebrand from Fairway to Cairn, with all 148 references renamed across code, templates, `.po`, Docker, CI and specs.
- New responsive two-variant logo system (`mark.svg` / `mark-sm.svg`) replacing the sailboat, with old logo files removed.
- Identity colour switched from indigo to navy `#1E3A8A`, remapping all `--accent*` tokens.
- Brand guidelines added at `docs/brand/brand-guidelines.md`.

### Added

- UX Phase 0 : `.tabular-nums` utility and an ARIA live region announcing HTMX writes.
- Global `prefers-reduced-motion` guard neutralizing animations.
- UX Phase 1 : shared component library in `core/templatetags/ui.py` with ten reusable tags.
- `/styleguide/` page rendering every component variant and the token palette.
- UX Phase 2 : three-layer design-token system with a new primitive palette layer.
- French translations for all new component and styleguide strings.

### Changed

- UX Phase 2 dark mode repainted from slate-blue to warm charcoal.
- UX Phase 3 : adopted Phase 1 components on `risk_list` and `role_detail`.
- UX Phase 4 : Cmd+K palette gains Navigation and permission-gated Actions groups with combobox ARIA.
- UX Phase 5 : `.split-pane` master-detail pattern with j/k navigation and `?focus=` URL sync.
- UX Phase 6 : sidebar sets `aria-current="page"` and `/styleguide` documents WCAG criteria.
- Premium polish : warm-stone light palette, calmer chromas, recalibrated shadows, larger radii, rebuilt type ladder and calmer cards.
- Home hero redesigned into a sober "Overall compliance" card with progress bar.
- Character pass : per-module accents, eight line-art illustrations, bigger home hero and pill `.ref` codes.
- Impersonation banner and approval badge moved off inline styles to dedicated classes.
- Home hero numbers now use `.tabular-nums`.
- HTMX hx-boost navigation swaps only `<main id="page-shell">`, keeping the sidebar mounted.
- Page headers unified to `{% page_header %}` across 38 templates, aliasing all module accents to navy.
- Forms unified across every CRUD screen : 6 confirm-delete and 63 form templates on a canonical pattern, plus a global autofocus script.
- Forms section added to brand guidelines.
- Default avatar repainted to a navy-soft initials gradient with a new `initials` filter.
- Empty state pattern across 42 list pages via `{% empty_state %}`.
- Filter chip dark mode fixed to `var(--accent)` with white text.
- French translations completed : all entries filled, 213 fuzzy flags reviewed, no duplicate `msgid`.

## [0.23.0] - 2026-05-29

### Added

- EBIOS RM (ANSSI v1.5) foundation : `StudyFramework`, `SecurityBaseline`, `FearedEvent`, `BaselineGap`, auto-bootstrapped on EBIOS assessments with six workshop trackers (W0..W5).
- EBIOS RM W2 : `RiskSource`, `TargetedObjective`, SR/OV pairs with ANSSI threat level and priority score.
- EBIOS RM W3 : `EcosystemStakeholder` (threat level/zone), `StrategicScenario`, `AttackPathStep`, plus an ecosystem graph endpoint.
- EBIOS RM W4 : `OperationalScenario` and MITRE ATT&CK techniques, with consolidate-to-Risk action and a MITRE heatmap.
- EBIOS RM W5 : `EbiosSummary` (residual strategy, before/after mappings) and `PACSMeasure`, with capture-mappings.
- EBIOS RM REST API under `/api/v1/risks/ebios/` for all W0..W5 entities.
- EBIOS RM MCP tools : full CRUD, batch-create and approve on every workshop entity.
- 7 new EBIOS permission features under `risks` (W0..W5), granted to the six system groups.
- EBIOS RM GUI : clickable workshop stepper with validation gates and full pages for W0..W5 (inline create/edit/delete).
- `M4bis_EBIOS_RM_Specifications.md` ANSSI-aligned spec replacing section 4 of M4.
- Persistent management review workflow (ISO 27001 clause 9.3) with full life cycle, stepper, snapshots and 2-column layout.
- `ManagementReview`, `ManagementReviewDecision`, `IsmsChange`, `ManagementReviewParticipant`, `ManagementReviewComment` and `ManagementReviewTransition` models.
- `StakeholderFeedback` in context (clause 9.3.2.e) with channel, sentiment, severity and status.
- Retrochaining `originating_review` FKs on action plans, treatment plans and objectives.
- REST API for management reviews, decisions, ISMS changes and stakeholder feedback.
- Ten new MCP tools for reviews, including `promote_decision_to_action_plan` and `export_management_review`.
- New management-review and stakeholder-feedback permissions, auto-assigned to the six system groups.
- Enhanced PPTX/DOCX export consumes a persistent review : decisions, ISMS changes and pre-filled signatures.
- Graphical participant signature : PNG/JPEG upload embedded in the DOCX, plus MCP tool `set_participant_signature`.
- "Management reviews" link added to the main sidebar.
- Approval workflow on `RiskAcceptance` : REST/MCP/UI actions with badge and new permission `risks.acceptance.approve`.
- `Risk` and `ISO27005Risk` freeze the matrix and criteria (`criteria_snapshot`) at first evaluation, surfaced in a scoring panel.
- Data migration backfilling `criteria_snapshot` for every evaluated risk and ISO 27005 analysis.
- M2M link between `RiskTreatmentPlan` and `ComplianceActionPlan`, with four MCP tools.
- Risk register Excel export at `/risks/register/export/xlsx/` and MCP tool `generate_risk_register`.
- Approval workflow extended to `Threat`, `Vulnerability` and `ISO27005Risk` (REST/MCP/UI + new permissions).
- Factories for threats, vulnerabilities, acceptances, treatment plans, treatment actions and ISO 27005 risks.
- Management commands `expire_risk_acceptances` and `mark_overdue_treatment_plans` (daily cron).
- ISO 27005 assessment DOCX export at `/risks/assessments/<pk>/export/docx/` and MCP tool `generate_iso27005_report`.

### Changed

- Management review export accepts a `review` argument and hydrates from snapshots when closed.
- Management review templates resolve dotted permissions via the `has_perm` tag.
- Management review export query parameter renamed from `format` to `fmt`.
- `RiskAcceptance` updates now reset approval and bump version like other approvable models.
- Risk scoring consults `criteria_snapshot` first, falling back to the live matrix only when absent.
- SoA PDF lists treated risks per control with residual level and decision, plus a per-framework summary.
- `/risks/` now shows a dashboard : counters, heatmaps, distributions, top critical risks and expiring items.
- Advanced filters on the risk register and REST endpoint, via a collapsible panel auto-opened when active.
- REST endpoints for `TreatmentAction` (CRUD), `ScaleLevel` and `RiskLevel` (read-only).
- Batch-create added on the treatment plan, acceptance and ISO 27005 risk viewsets.
- Inline add/edit/delete of treatment actions from the treatment plan detail page.
- Bulk approve and delete on the risk register, with select-all and a sticky toolbar.
- Sticky right sidebar on the four risks detail pages.
- Test suite skips historical migrations, dropping the full run from ~37 min to seconds per parallel job.

### Fixed

- Management review decision and ISMS change serializers no longer require `review` on input.

## [0.22.0] - 2026-04-13

### Added

- Management review export (ISO 27001 clause 9.3) with two output formats : PowerPoint presentation and Word meeting minutes
- Seven structured sections : action plan status, internal/external issues, stakeholder needs, security performance (NC, indicators, audits, objectives), interested party feedback, risk assessment and treatment status, improvement opportunities
- Scope-based filtering for management review data
- Period date range filtering (start/end) for management review exports
- MCP tools `generate_management_review_pptx` and `generate_management_review_docx`
- REST API endpoint `POST /api/v1/reports/reports/generate-management-review/`
- New dependencies : `python-pptx` and `python-docx`

## [0.21.4] - 2026-04-01

### Added

- Changelog popup on dashboard : automatically displays a modal with all changes between the previously seen version and the current version when the app is updated
- `last_seen_version` field on User model to track the last version acknowledged by each user
- Changelog parser utility (`core/changelog.py`) to extract entries from `CHANGELOG.md` between two versions
- Dismiss endpoint (`POST /dashboard/changelog-dismiss/`) to mark the current version as seen

## [0.21.3] - 2026-03-26

### Added

- REST API batch creation endpoints (`POST /api/v1/<module>/<entity>/batch/`) for 10 entities: Requirement, Section, EssentialAsset, SupportAsset, AssetDependency, Threat, Vulnerability, Risk, Stakeholder, Supplier. Each endpoint accepts up to 100 items with partial success support (non-atomic)
- `BatchCreateMixin` reusable DRF mixin for adding batch creation to any ViewSet
- MCP `help` tool providing comprehensive usage documentation (call with no args for full guide, or with topic: context, assets, compliance, risks, batch, workflow, permissions, examples)

### Changed

- MCP batch creation tools now use non-atomic partial success instead of all-or-nothing transactions
- `SupplierDependencyType` choices updated: `provides`, `hosts`, `manages`, `develops`, `supports`, `licenses`, `maintains`, `other`
- `SiteSupplierDependencyType` choices updated to match SupplierDependencyType values

### Fixed

- Fix `Supplier.type` FK resolution in DRF serializer - explicitly declared as `PrimaryKeyRelatedField` for proper SupplierType lookup
- Fix `SupplierDependency.dependency_type` rejecting valid values other than `other`

## [0.21.2] - 2026-03-26

### Added

- `non_compliant` and `partially_compliant` choices for requirement `compliance_status`, enabling simple compliance tracking alongside detailed audit-oriented statuses
- MCP DIC level fields now accept text labels (`negligible`, `low`, `medium`, `high`, `critical`) in addition to integers (0-4)
- MCP batch creation tools (`batch_create_*`) for all entities, allowing up to 500 items per atomic transaction

### Fixed

- Fix `Supplier.type` FK resolution in MCP create/update handlers - string IDs are now properly coerced to integers for SupplierType lookup
- Fix MCP `create_supplier` / `update_supplier` handlers not calling `_coerce_field_value`, causing FK and type coercion failures
- Fix MCP supplier `type` field schema declaring `string`/UUID type instead of `integer` (SupplierType uses AutoField PK)

## [0.21.1] - 2026-03-26

### Added

- Scope managers : assign one or more responsible users to a scope (`Scope.managers` M2M). Managers automatically gain access to the scope even without group-based scope assignment. Available in UI, REST API, and MCP tools
- Reusable `{% user_badge %}` template tag displaying user avatar (with initials fallback) and display name, with configurable size, link, and layout options
- M2M relationship between action plans and requirements (`ComplianceActionPlan.requirements`), enabling linked requirements on action plan detail and requirement detail pages
- Generic M2M field support in MCP `_register_crud` create/update handlers (`m2m_fields` parameter)

### Changed

- Redesign all 16 detail pages to a consistent 2-column card layout (left content, right metadata sidebar) replacing tab-based layouts across context, compliance, risks and assets modules
- Replace all inline user field displays (`{{ obj.owner }}`, `{{ obj.approved_by }}`, etc.) with `{% user_badge %}` tag across 19 detail templates, showing avatar + real name
- MCP tool schemas now document all valid enum values for every choice field across all modules (context, assets, compliance, risks), with `enum` arrays in parameter definitions
- MCP tool schemas now declare `required` fields on create operations, aligned with Django model constraints
- MCP server returns detailed validation error messages instead of generic "Invalid params" / "Internal error" responses
- MCP DIC level fields (`confidentiality_level`, `integrity_level`, `availability_level`) now correctly declared as `integer` type with `enum: [0, 1, 2, 3, 4]` instead of `string`
- MCP supplier `type` field description clarified as a foreign key (UUID of SupplierType) instead of an enum
- Add `create` and `delete` actions to `assets.config` permissions, enabling MCP SupplierType management for non-superuser accounts

### Fixed

- Fix 500 error on requirement detail page caused by missing `action_plans` reverse relation

## [0.21.0] - 2026-03-25

### Added

- User impersonation for administrators (`system.users.impersonate` permission) with session-based switching, fixed amber banner, access log tracking, and security guards (no nesting)
- Robot user type: users can be marked as "Robot" (API/MCP-only accounts with no web login, optional first name, dedicated badge in UI)
- Trivy vulnerability scanning in CI security stage with GitLab container scanning report
- JUnit test report artifacts in CI
- Parallelize CI unit tests into one job per app directory (9 parallel jobs) with combined coverage report

## [0.20.0] - 2026-03-25

### Added

- Enforce RBAC permission checks on all UI views (~200 views across context, assets, compliance, risks and reports apps) via `PermissionRequiredMixin`
- Add parent-based scope filtering (`scope_parent_lookup`) for child models (Requirement, Risk, TreatmentPlan, Finding, etc.) in both UI and API
- Add RBAC (`ModulePermission`) to ReportViewSet and PermissionViewSet API endpoints
- Add `GroupDeleteView` with confirmation page, allowing deletion of any group (including system groups)
- Allow modification of system groups (name, permissions, users, scopes)
- Add ruff linter with syntax-focused config in pyproject.toml
- Split CI into quality (syntax, translations), test (unit), and deploy (docker-image) stages
- Add translations CI job to verify .po files compile without errors
- Add pip caching and Cobertura coverage artifact with MR badge regex
- Factor common CI rules into `.not-tags` YAML template

### Changed

- System groups are no longer locked: they can be edited, have their permissions changed, and be deleted like custom groups
- MCP `action_plan_transition` tool now requires `compliance.action_plan.update` permission instead of `.read`
- Remove all version pins from Docker images (Dockerfile, docker-compose, CI) to always use latest
- Remove all version constraints from Python dependencies in requirements.txt
- PostgreSQL volume mount changed from `/var/lib/postgresql/data` to `/var/lib/postgresql` (required by PostgreSQL 18+)

> **Warning:** The PostgreSQL volume layout changed. Existing deployments must dump and restore their database before upgrading:
>
> ```bash
> docker compose exec db pg_dumpall -U postgres > backup.sql
> docker compose down && docker volume rm <project>_postgres_data
> docker compose up -d
> docker compose exec -T db psql -U postgres < backup.sql
> ```

### Fixed

- Fix undefined `HttpResponseRedirect` in compliance views

## [0.19.1] - 2026-03-24

### Changed

- Redesign logo with a sailboat navigating a channel (fairway) replacing the old F-letter mark
- New logo features curved sails, wind pennant, sleek hull and accentuated waves
- Light, dark and 32x32 icon variants all updated along with all inline SVGs in templates

## [0.19.0] - 2026-03-24

### Changed

- Rebrand from Open GRC to Fairway across all user-facing strings, templates, documentation and CI/CD
- Replace Bootstrap shield icon with custom SVG logo (light/dark variants with inline SVG)
- Add favicon as inline data URI SVG
- Update GitLab registry and Docker Hub image paths to `fairway/fairway`
- Add `STATICFILES_DIRS` setting for project-level static assets

## [0.18.3] - 2026-03-24

### Added

- Branch workflow and git author guidelines in CLAUDE.md

## [0.18.2] - 2026-03-24

### Fixed

- Fix Docker CI job by setting DOCKER_HOST to mounted socket

## [0.18.1] - 2026-03-24

### Fixed

- Fix GitLab CI Docker build by using host Docker socket instead of DinD

## [0.18.0] - 2026-03-24

### Changed

- Switch Docker image publishing from Docker Hub to GitLab Container Registry

## [0.17.0] - 2026-03-24

### Added

- GitLab CI pipeline as primary CI alongside GitHub Actions
- Comprehensive CHANGELOG based on git history and tags
- CHANGELOG and README maintenance guidelines in CLAUDE.md

### Changed

- Set GitLab as primary git remote (origin), GitHub as secondary
- Revamp README with feature tables, MCP tools reference, and missing features list

## [0.16.0] - 2026-03-17

### Added

- Calendar spanning events with iCal subscription support and admin management

### Changed

- Rename ActionPlanStatus constants and DB values from French to English
- Unify action plan page titles between list and kanban views

### Fixed

- Fix AttributeError in MCP action_plan_transitions and kanban tools

## [0.15.0] - 2026-03-16

### Added

- Kanban board workflow for action plans with drag-and-drop status transitions
- Threaded comments on action plans with HTML rendering and user avatars
- Multi-assignee support with avatar display and comment count on Kanban cards
- Offcanvas drawer previews for linked risks and findings on action plans
- Visual workflow stepper for action plan status transitions

### Changed

- Redesign action plan detail page with two-column card layout replacing tabs
- Rename Owner to Supervisor with photo and full name display
- Use display_name (First Last) instead of email fallback for users
- Make kanban board the default view for action plans with full-width layout and scrollable columns

### Fixed

- Fix overdue action plan alert to use correct status values
- Fix MCP action plan tools with proper permissions, error handling, and workflow rules
- Fix drag-and-drop on kanban cards using Sortable.js forceFallback
- Fix French translation escaping in kanban JS

## [0.14.0 - 0.14.2] - 2026-03-13 to 2026-03-14

### Added

- Company settings management (logo, name, address) with report cover page branding
- "Cancelled" audit status with SVG branch lines in workflow stepper
- Confirmation dialog on assessment status transitions
- M2M support for framework_ids and requirement_ids in MCP compliance tools
- Missing reports permissions added to permission system

### Fixed

- Fix migration conflicts with merge migration for 0022 migrations
- Fix stepper layout to use flex instead of grid to prevent pill stretching
- Fix mobile stepper wrapping in single scrollable container
- Fix stats and status propagation for MCP compliance tools
- Clear stale __pycache__ in entrypoint to prevent migration conflicts

## [0.13.0] - 2026-03-13

### Added

- Audit report PDF generation with professional template design
- Scopes displayed as indented tree in audit report PDF
- Finding counts by type and impacted requirements count in report summary
- Assessment limitations field and result attachments
- Requirement body text in audit report finding detail cards

## [0.12.0 - 0.12.1] - 2026-03-13

### Added

- Multi-framework support per assessment with grouped requirements display
- Bulk toggle button to select/deselect all requirements for evaluation
- Visual workflow stepper on assessment detail page
- Per-status required field validation for assessment transitions
- Generic loading spinner for HTMX buttons, delete buttons, and approval actions
- Visual feedback on toggle click in assessment requirements

### Changed

- Revamp assessment workflow with new statuses and sequential transitions
- Exclude non-applicable requirements from coverage and compliance statistics
- Exclude EVALUATED status from compliance percentage calculation
- Auto-create AssessmentResults on assessment create/update
- Reorganize assessment detail with metadata in header, results merged into Planning tab
- Compute framework compliance from latest audit results by end date
- Compute dashboard compliance segments from assessment results

### Fixed

- Fix coverage calculation exceeding 100% for non-applicable requirements
- Fix bulk toggle to auto-initialize missing assessment results
- Fix calendar crash with correct field names for compliance assessments
- Fix dashboard compliance percentage to use computed values
- Fix coverage/compliance columns in assessment list to match detail view
- Redirect to edit form when transition requires missing fields

### Removed

- Remove methodology field from compliance assessments
- Remove per-theme dashboards

## [0.11.0 - 0.11.2] - 2026-03-10 to 2026-03-12

### Added

- SWOT matrix view with CRUD operations and user-defined TOWS strategies
- Logo support for compliance frameworks with dashboard display
- Findings (Constats) tab in compliance assessments with 3-state toggle
- Multi-color stacked progress bars for section compliance breakdown
- Coverage and compliance gauges on assessment detail page
- Audit-grade compliance status vocabulary

### Changed

- Redesign SWOT UI with strategies tab and context badges in matrix cells
- Rename compliance Assessments to Audits in menu and page titles
- Merge Summary tab into General tab on assessment detail page
- Use plain text fields for SWOT descriptions instead of HTML editor

### Fixed

- Fix HTMX delete buttons by adding global CSRF token header
- Fix blank drawer when clicking + on SWOT detail page
- Fix findings table HTML rendering and requirement badge centering
- Fix coverage mismatch by auto-creating AssessmentResult for requirements with findings
- Fix compliance gauge to compute dynamically from covered results only
- Fix finding delete not updating assessment results
- Fix duplicate translation entries in French .po file

## [0.10.0 - 0.10.2] - 2026-03-10

### Added

- Reports module with Statement of Applicability (SoA) PDF generation
- HTML rendering in SoA PDF justification column
- Natural sort for requirements in SoA export

### Fixed

- Fix WeasyPrint import with lazy loading to avoid missing system libs at startup
- Fix Dockerfile package name for gdk-pixbuf on Bookworm
- Fix SoA PDF generation by upgrading WeasyPrint for pydyf compatibility
- Fix SoA PDF download by storing file content in database
- Add media/ and staticfiles/ to .gitignore

## [0.9.0 - 0.9.1] - 2026-03-09 to 2026-03-10

### Added

- Interactive compliance evaluation UI with guided workflow
- Coverage % and compliance % columns in assessment list and detail
- Segmented compliance bars on dashboard using requirement-level status
- recalculate_compliance management command
- assessed_at, assessed_by_id, and observations fields in MCP assessment_result tool

### Changed

- Propagate assessment results to requirements, sections, and framework
- Show compliance from latest assessment on dashboards
- Treat not-assessed as 0% and not-applicable as 100% in compliance calculation

### Fixed

- Fix SPOF scheduler starting during management commands
- Fix dark theme and natural sort for assessment results table
- Fix swot_item MCP tool using wrong field names
- Fix phantom fields and missing required fields across 10 MCP tools
- Fix duplicate msgid entries in French translations

## [0.8.0] - 2026-03-09

### Added

- Versioning behavior management in Administration with translated field verbose names

### Fixed

- Fix versioning config form not saving by populating major_fields choices from POST data
- Standardize helpers display and add missing helper content
- Fix missing versioning_tags load in asset list templates

## [0.7.0 - 0.7.5] - 2026-03-07 to 2026-03-08

### Added

- HTMX offcanvas drawer forms for create/edit across all apps (context, risks, compliance, assets)
- Drawer modals for indicator create/edit forms
- OAuth token authentication added to REST Framework defaults
- logo_32 field in SupplierListSerializer for iOS app

### Changed

- Redesign drawer forms following Ant Design/Stripe/Linear patterns with metadata bar and single-column flow
- Convert list page header buttons to icon buttons, keeping only create button
- Change OAuthAuthorizationCode.redirect_uri from URLField to CharField for custom URL schemes

### Fixed

- Fix indicator values losing decimal precision on dashboard
- Fix indicator number input to accept locale-specific decimal formats
- Fix indicator decimal animation using raw numeric value
- Fix OAuth redirect to support custom URL schemes (e.g. opengrc://)
- Fix OAuth/JWT auth chain to return None instead of raising on unknown token

## [0.6.0] - 2026-03-06

### Added

- Global search bar with dynamic results grouped by item type

### Fixed

- Fix WebSocket proxy support with SECURE_PROXY_SSL_HEADER, CSRF_TRUSTED_ORIGINS, and AllowedHostsOriginValidator

## [0.5.0] - 2026-03-06

### Added

- WebSocket support for real-time dashboard updates
- Animated indicator cards with smooth counting animation on WebSocket value changes
- Sonar-style animated dot for WebSocket connection status
- Thousand separators preserved on indicator values during animations

## [0.4.5 - 0.4.8] - 2026-03-04 to 2026-03-06

### Added

- Image URL support for supplier logo upload via MCP
- Risk-to-requirement linking with ergonomic Tom Select UI and MCP tools
- Rich text editor (Jodit) with centralized dark theme support
- Sticky action bar with gradient fade on forms
- Sortable column header translations in all list views
- Floating user bubble in header with about modal
- Collapsible sidebar with icon-only mode, flyout sub-menus, and smooth animations
- Pill/chip-style table filters replacing select-based filters
- Stat card count-up animations and scroll-triggered progress bar animations

### Changed

- Redesign requirement form with grouped fields and two-column layout
- Render rich text as HTML in all detail templates
- Fullscreen dependency graph with zoom-to-fit default view and edge-to-edge layout
- Theme-aware form fields and Bootstrap components for dark mode
- Improve MCP tool descriptions for LLM clarity

### Fixed

- Fix AssessmentResult ordering after order field removal
- Fix card-header background leaking through rounded corners
- Fix mobile display for multi-select dropdowns
- Fix 5 MCP API issues blocking ISO 27005 risk assessment workflow
- Fix action logs 500 error on pagination by handling str() failures
- Fix sidebar collapse flash on page reload
- Fix flyout sub-menus disappearing when moving mouse to them
- Fix mobile sidebar layout and sub-menu alignment
- Fix dependency graph supplier nodes, gap, and legend alignment

### Removed

- Remove colored left border from indicator cards

## [0.4.2 - 0.4.4] - 2026-03-03 to 2026-03-04

### Added

- Server-side sorting and filtering for all list tables with persisted user preferences
- Natural sorting for references and requirement numbers
- Scope sorting with tree hierarchy and predefined filter chips
- Missing supplier, supplier_dependency, and indicator permissions
- Treatment_type and missing fields added to MCP risk tools
- Supplier logo support and missing fields in MCP tools

### Changed

- MCP OAuth tokens set to never expire
- Improve rights management GUI ergonomics

### Fixed

- Fix MCP disconnect by allowing DELETE without strict auth and revoking token
- Fix natural_sort_key array index for REGEXP_MATCHES result
- Fix SQLite compatibility for natural_sort_key migration

## [0.4.0 - 0.4.1] - 2026-03-03

### Added

- Indicators module with dashboard widget, user-configurable pinning, and sparkline charts
- Daily and weekly measurement frequencies for indicators
- Min/max critical thresholds with green/red/default card border status
- Persistent helper dismissal per user with reset in profile
- Toast notifications replacing inline alerts
- Tab persistence across page refresh via URL hash and sessionStorage
- Modern table design with dot-pill status badges
- User scopes displayed on all dashboard pages

### Changed

- Auto-generate reference fields and make them non-editable
- Reorder dashboard with overall compliance above SPOF and objectives progression
- Display 10 indicators (5 per line) with optional evolution chart
- Indicator cards use icons, locale-formatted numbers, and delta display
- Halve outer spacing around sidebar menu

### Fixed

- Fix migration ordering for auto-references before unique constraint
- Fix NameError from missing gettext_lazy import
- Fix tab underline alignment offset across all detail pages
- Fix sparkline draw animation on Safari
- Fix accounts migration dependency referencing nonexistent migration
- Replace PostgreSQL-specific RunSQL with database-agnostic RunPython
- Skip SPOF scheduler during test runs
- Fix MCP notification accumulation
- Fix indicator card width uniformity with CSS Grid

## [0.3.0 - 0.3.1] - 2026-03-02

### Added

- Integrated MCP server with OAuth 2.0 authentication (JSON-RPC 2.0)
- OAuth credential management UI in user profile page
- OAuth Authorization Code + PKCE flow for Claude.ai MCP integration

### Fixed

- Fix weak cryptographic hashing on sensitive data (code scanning alert #13)
- Fix information exposure through exceptions (code scanning alerts #11, #12)

## [0.2.12 - 0.2.16] - 2026-03-02

### Added

- Passkey (WebAuthn/FIDO2) authentication support
- Multi-scope support with hierarchical tree selector and breadcrumb-style badges
- Automatic SPOF detection service with 5 rules running at startup and every 5 minutes
- Compact count popover for scopes in list tables

### Fixed

- Fix passkey RP ID mismatch by deriving from request
- Fix passkey JS broken in French due to unescaped apostrophes
- Fix scope filtering for multi-scope M2M relationships
- Fix scope popover clipped by table-responsive overflow

## [0.2.7 - 0.2.11] - 2026-03-01

### Added

- User profile photo (avatar) support
- Auto-resize uploaded images to reduce DB and bandwidth load
- Missing help_modal tags added to 36 templates

### Changed

- Finalize interface modernization with pixel-perfect design polish
- Replace sidebar glassmorphism with clean solid style
- Redesign profile, supplier, and all form templates with multi-column grouped layouts
- Replace table action text buttons with icon buttons
- Replace sidebar footer dropdown with direct profile link and logout icon
- Store images and files as base64 data URIs in database instead of filesystem
- Round compliance percentages to whole numbers
- Improve dark theme sidebar text contrast and sub-menu colors

### Fixed

- Fix risk matrix padding, event alignment, and missing translations
- Fix supplier type creation by adding requirement formset to template
- Fix help_modal template tag syntax errors
- Crop non-square supplier logos with object-fit:cover

## [0.2.1 - 0.2.6] - 2026-03-01

### Added

- Floating mobile menu button with animated hamburger

### Changed

- Improve mobile responsive dashboard and add new KPIs
- Use version.txt for app version instead of git describe
- Bake APP_VERSION into Docker image via build arg
- Style sidebar as floating glass panel with backdrop blur

### Fixed

- Fix mobile menu overlap and overflow issues
- Fix version stuck on 0.2.0 by writing to /etc/app-version outside volume mount

## [0.2.0] - 2026-03-01

### Added

- Supplier management with dependencies and dependency graph visualization
- Supplier logo support with display in list, detail, and graph views
- SPOF and redundancy tracking for supplier dependencies
- Supplier type management with configurable requirements and review system
- Supplier reviews added to calendar
- Site management moved to assets with site dependency models

### Fixed

- Fix version display when APP_VERSION env var is unset
- Fix supplier list layout
- Fix migration for CharField to FK data migration

## [0.1.1] - 2026-03-01

### Added

- Unique auto-generated references for all items in PREFIX-N format
- References displayed in all list tables and detail views with monospace font
- Clickable references in tables

### Fixed

- Fix data migrations to handle NULL references in historical tables

## [0.1.0] - 2026-03-01

### Added

- Tag support for all items with ergonomic Tom Select input and inline creation
- Tag administration page with usage tracking, editing, and deletion

## [0.0.5] - 2026-03-01

### Added

- App version display from Git tag in sidebar
- Vertical divider line for sidebar submenus

### Changed

- Increase text size and lighten sidebar sub-links

### Fixed

- Set is_approved default to False so items require explicit approval

## [0.0.2 - 0.0.4] - 2026-02-28

### Changed

- Auto-run migrate and create super-admin on container startup

### Fixed

- Prevent Gunicorn worker crashes in Docker behind a reverse proxy
- Add --preload to Gunicorn to prevent worker timeout on startup
- Wait for PostgreSQL to be fully ready before running migrations

## [0.0.1] - 2026-02-28

### Added

- Initial release with Django 5.2 GRC platform
- Organizational context management (scopes, sites, issues, stakeholders, objectives, SWOT, roles, activities)
- Asset management with DIC valuation and support assets
- Risk management with ISO 27005 analysis and treatment plans
- Compliance tracking with frameworks, requirements, and assessments
- Custom user model with email-based authentication and UUID primary keys
- Role-based access control with 6 system groups and custom permissions
- Full i18n support (English and French)
- Calendar view for all dated elements
- Contextual help banners
- REST API under /api/v1/
- Docker Compose deployment with PostgreSQL
- GitHub Actions CI with pytest
- Docker Hub publish workflow on version tags

[0.32.0]: https://github.com/frousselet/cairn/compare/v0.31.0...v0.32.0
[0.31.0]: https://github.com/frousselet/cairn/compare/v0.30.0...v0.31.0
[0.30.0]: https://github.com/frousselet/cairn/compare/v0.29.1...v0.30.0
[0.29.1]: https://github.com/frousselet/cairn/compare/v0.29.0...v0.29.1
[0.29.0]: https://github.com/frousselet/cairn/compare/v0.28.3...v0.29.0
[0.28.3]: https://github.com/frousselet/cairn/compare/v0.28.2...v0.28.3
[0.28.2]: https://github.com/frousselet/cairn/compare/v0.28.1...v0.28.2
[0.28.1]: https://github.com/frousselet/cairn/compare/v0.28.0...v0.28.1
[0.28.0]: https://github.com/frousselet/cairn/compare/v0.27.2...v0.28.0
[0.27.2]: https://github.com/frousselet/cairn/compare/v0.27.1...v0.27.2
[0.27.1]: https://github.com/frousselet/cairn/compare/v0.27.0...v0.27.1
[0.27.0]: https://github.com/frousselet/cairn/compare/v0.26.3...v0.27.0
[0.26.3]: https://github.com/frousselet/cairn/compare/v0.26.2...v0.26.3
[0.26.2]: https://github.com/frousselet/cairn/compare/v0.26.1...v0.26.2
[0.26.1]: https://github.com/frousselet/cairn/compare/v0.26.0...v0.26.1
[0.26.0]: https://github.com/frousselet/cairn/compare/v0.25.0...v0.26.0
[0.25.0]: https://github.com/frousselet/cairn/compare/v0.24.5...v0.25.0
[0.24.5]: https://github.com/frousselet/cairn/compare/v0.24.4...v0.24.5
[0.24.4]: https://github.com/frousselet/cairn/compare/v0.24.3...v0.24.4
[0.24.3]: https://github.com/frousselet/cairn/compare/v0.24.2...v0.24.3
[0.24.2]: https://github.com/frousselet/cairn/compare/v0.24.1...v0.24.2
[0.24.1]: https://github.com/frousselet/cairn/compare/v0.24.0...v0.24.1
[0.24.0]: https://github.com/frousselet/cairn/compare/v0.23.0...v0.24.0
[0.23.0]: https://github.com/frousselet/cairn/compare/v0.22.0...v0.23.0
[0.22.0]: https://github.com/frousselet/cairn/compare/v0.21.4...v0.22.0
[0.21.4]: https://github.com/frousselet/cairn/compare/v0.21.3...v0.21.4
[0.21.3]: https://github.com/frousselet/cairn/compare/v0.21.2...v0.21.3
[0.21.2]: https://github.com/frousselet/cairn/compare/v0.21.1...v0.21.2
[0.21.1]: https://github.com/frousselet/cairn/compare/v0.21.0...v0.21.1
[0.21.0]: https://github.com/frousselet/cairn/compare/v0.20.0...v0.21.0
[0.20.0]: https://github.com/frousselet/cairn/compare/v0.19.1...v0.20.0
[0.19.1]: https://github.com/frousselet/cairn/compare/v0.19.0...v0.19.1
[0.19.0]: https://github.com/frousselet/cairn/compare/v0.18.3...v0.19.0
[0.18.3]: https://github.com/frousselet/cairn/compare/v0.18.2...v0.18.3
[0.18.2]: https://github.com/frousselet/cairn/compare/v0.18.1...v0.18.2
[0.18.1]: https://github.com/frousselet/cairn/compare/v0.18.0...v0.18.1
[0.18.0]: https://github.com/frousselet/cairn/compare/v0.17.0...v0.18.0
[0.17.0]: https://github.com/frousselet/cairn/compare/v0.16.0...v0.17.0
[0.16.0]: https://github.com/frousselet/cairn/compare/v0.15.0...v0.16.0
[0.15.0]: https://github.com/frousselet/cairn/compare/v0.14.2...v0.15.0
[0.14.0 - 0.14.2]: https://github.com/frousselet/cairn/compare/v0.13.0...v0.14.2
[0.13.0]: https://github.com/frousselet/cairn/compare/v0.12.1...v0.13.0
[0.12.0 - 0.12.1]: https://github.com/frousselet/cairn/compare/v0.11.2...v0.12.1
[0.11.0 - 0.11.2]: https://github.com/frousselet/cairn/compare/v0.10.2...v0.11.2
[0.10.0 - 0.10.2]: https://github.com/frousselet/cairn/compare/v0.9.1...v0.10.2
[0.9.0 - 0.9.1]: https://github.com/frousselet/cairn/compare/v0.8.0...v0.9.1
[0.8.0]: https://github.com/frousselet/cairn/compare/v0.7.5...v0.8.0
[0.7.0 - 0.7.5]: https://github.com/frousselet/cairn/compare/v0.6.0...v0.7.5
[0.6.0]: https://github.com/frousselet/cairn/compare/v0.5.0...v0.6.0
[0.5.0]: https://github.com/frousselet/cairn/compare/v0.4.8...v0.5.0
[0.4.5 - 0.4.8]: https://github.com/frousselet/cairn/compare/v0.4.4...v0.4.8
[0.4.2 - 0.4.4]: https://github.com/frousselet/cairn/compare/v0.4.1...v0.4.4
[0.4.0 - 0.4.1]: https://github.com/frousselet/cairn/compare/v0.3.1...v0.4.1
[0.3.0 - 0.3.1]: https://github.com/frousselet/cairn/compare/v0.2.16...v0.3.1
[0.2.12 - 0.2.16]: https://github.com/frousselet/cairn/compare/v0.2.11...v0.2.16
[0.2.7 - 0.2.11]: https://github.com/frousselet/cairn/compare/v0.2.6...v0.2.11
[0.2.1 - 0.2.6]: https://github.com/frousselet/cairn/compare/v0.2.0...v0.2.6
[0.2.0]: https://github.com/frousselet/cairn/compare/v0.1.1...v0.2.0
[0.1.1]: https://github.com/frousselet/cairn/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/frousselet/cairn/compare/v0.0.5...v0.1.0
[0.0.5]: https://github.com/frousselet/cairn/compare/v0.0.4...v0.0.5
[0.0.2 - 0.0.4]: https://github.com/frousselet/cairn/compare/v0.0.1...v0.0.4
[0.0.1]: https://github.com/frousselet/cairn/releases/tag/v0.0.1
