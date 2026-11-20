# Changelog

All notable changes to Cairn are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- A documented UI component framework (`detail_layout`, `section_card`, `overview`, `meta_list`, `kpi_tile`, `record_card`, `ref_link`, `tag_list`, `choice_badge`, the dash) with shared page-form and delete shells, catalogued in `docs/sdk/ui-components.md` and on `/styleguide/`.
- A Documents module (ISO 27001 clause 5.2, 7.5, A.5.1) : policies, procedures, standards and charters with frozen, approved versions (one in force at a time), a review cycle with reminders, and acknowledgement campaigns whose confirmations are kept as evidence, on the web, the REST API and MCP.
- A Controls module (ISO 27001 clause 6.1.3, 9.1) : security controls linked to requirements, risks, treatment plans, PACS measures, assets, objectives and documents, tests with independently validated runs and evidence, derived effectiveness, findings raised from failed runs, an enriched Statement of Applicability, on the web, the REST API and MCP.
- `GET /health/` reports whether the instance can serve (database reachable), with no session and whatever the Host header, and is the image's `HEALTHCHECK`.
- Error pages in the product's design and in the reader's language for a missing page, a refused permission, an expired form and a server error.
- The basemap of the scope, site and supplier maps is a deployment setting (`MAP_TILE_URL`, `MAP_TILE_URL_DARK`, `MAP_TILE_ATTRIBUTION`); an empty value switches the maps off.
- `manage.py backup` writes the database and the uploaded files into one archive with a manifest and a checksum per file, and `manage.py restore` puts an instance back in its exact state after verifying it and saving what it replaces (`BACKUP_DIR`, `MEDIA_ROOT`).
- A *Skip to main content* link is the first stop of the keyboard on every page, and dashboard tiles gain *Move earlier* / *Move later* buttons so the layout can be rearranged without dragging.
- The dashboard of a new instance opens on its first steps, a short ordered list of what to do first, until the instance holds its first records.
- A record is created on one screen, then completed on its own page, which lists what it still needs and edits it one card at a time : the context module (scopes, issues, stakeholders, objectives, SWOT analyses, roles, activities and indicators), the assets module (essential and support assets, suppliers, asset groups, sites, contracts, certificates), the compliance module (frameworks, requirements, assessments, nonconformities, action plans), the ISO 27005 side of the risks module (assessments, analyses, risks, treatment plans, acceptances, the threat and vulnerability catalogues) the security controls with their tests and runs, the documents with their versions and acknowledgement campaigns, the security events, the incident file with its response actions, its chronology, its evidence items, its personal data qualification and its post-incident review, the response plans, the reporting authorities and the obligation templates are the first to follow the usability standard (`docs/sdk/usability-standard.md`).
- What a stakeholder expects is added, edited and removed from its page : the interface listed expectations and could not write one (REST API and MCP only).
- An objective names the issues it answers and the stakeholders that expect it, an issue the stakeholders it concerns, an activity the objectives it helps to reach, an indicator who reads it and the objectives it tells the progress of : these links are set and read on their pages, where only the REST API and the MCP server reached them; a validated issue offers the creation of an objective that answers it.
- The About dialog states what Cairn claims about its accessibility : built to meet WCAG 2.2 AA, what is checked on every change, and that its conformance has not been assessed (also `GET /api/v1/accessibility/` and the `get_accessibility_statement` MCP tool).
- A glossary in the application : each notion under the one name the interface gives it, a plain definition, the other names people know it by and the acronyms spelled out, on its page, in the search, over `GET /api/v1/glossary/` and the `get_glossary` MCP tool.
- A help on the pages that had none : the registers of contracts, certificates, nonconformities, security events, response plans, management reviews, reports and lifecycles, and the six EBIOS RM workshops.
- The external participants of an EBIOS RM study are typed on the page of workshop 0, one per line, and held on every surface to a list of `{name, role, organization}` texts : the page did not show them and the REST API stored whatever it was given.
- The demo dataset holds an EBIOS RM operational scenario, its attack techniques and a written summary : workshops 0 to 3 of its study are validated, workshop 4 is under way.
- The MCP server sets the relations of the EBIOS RM records that the REST API alone could write : what a study covers on the security baseline, the support assets of a baseline gap, of an ecosystem stakeholder and of an operational scenario, the feared events of a targeted objective and of a strategic scenario, what a PACS measure links to, the participants and the applicable frameworks of a study.

### Changed

- The design system stylesheet moves out of `base.html` into ordered, browser-cached files under `static/css/cairn/`.
- The six EBIOS RM workshops follow the usability standard : the page names what the study covers and edits it one card at a time, its rows (feared events, baseline gaps, risk sources, targeted objectives, pairs, ecosystem stakeholders, strategic and operational scenarios, attack path steps, attack techniques, PACS measures) are added in the side panel with two to six fields, and a gravity, a likelihood or a rating is picked by the name of its level.
- An EBIOS RM workshop is validated on its deliverables : its page lists what is missing, workshop 0 waits for the mission statement and the perimeters of the study, workshop 1 for its essential and support assets and a feared event for each essential asset, workshop 2 for a retained pair, workshop 3 for a retained strategic scenario, workshop 4 for an operational scenario per retained strategic scenario, workshop 5 for a measure and the residual risk strategy.
- An EBIOS RM operational scenario records by itself the version of the MITRE ATT&CK catalogue its techniques come from, and asks for a reason when it is given a gravity of its own.
- An EBIOS RM pair is named by its targeted objective alone, on the form, the REST API and the MCP server : the risk source and the study follow the objective, and a pair that contradicts it is refused.
- Status, level and lifecycle badges render as the same dot pill in tables, cards and headers alike.
- A custody act recorded by hand on an evidence item asks which act it is, where a transfer was preselected, and is proposed as happening now.
- Multi-select fields in forms become searchable pickers with removable chips instead of native list boxes.
- Every screen is rebuilt on the component framework : one detail page anatomy, one section title, one empty-value marker, one badge and tag pill, and form footers with a neutral Cancel on the left.
- Dates follow the active locale everywhere, and short numeric dates put the day first in English as in French.
- The lifecycle editor shows its steps, transitions and JSON as stacked cards instead of tabs.
- The assessment result toggles read the planning / fieldwork phase from the assessment instead of comparing a status string in the template.
- EBIOS RM workshop 5 measures can be linked while they are planned, in progress or overdue.
- List pages read their tags, scope ancestors and filter options in a constant number of queries instead of one per row or per option, and so do the tag list and the dashboard's indicators.
- Detail pages show the lifecycle as a one-line bar (the path the record is on, each possible move as a button named after its transition, the full graph on demand) instead of a full-width diagram.
- Pages are denser : content starts near the top of the window, record titles step down a size and keep their actions beside them, and key figures form a slim strip above the content.
- The sidebar has two levels instead of three : seven sections that open on their pages, with the reference data (types, criteria, catalogs, authorities, templates) in a section of its own, and indicators and dependencies as one entry each with a view switcher on their pages.
- A menu entry is shown only to the users its page lets in, and stays marked on the records of its register.
- Detail pages are shorter : traceability becomes a single line, an empty section a line of small print, long embedded tables show their first rows behind "Show all", and an audit folds its requirements by section.
- A detail page with six sections or more gains a "Jump to a section" menu in its header.
- The incident registers show their references as the clickable pill every other list uses.
- The French interface names one thing one way, as `docs/brand/glossary.md` now settles it : *bien* and never *actif*, *partie intéressée*, *appréciation des risques*, *mesure*, *étiquette*, *cycle de vie*; the menu section becomes *Biens et fournisseurs* (*Assets and suppliers*) and the documents register is named *Documents*.
- The help of every page is rewritten for a newcomer (the name of the page as its title, then what the thing is in one sentence, an example, what to do first) and, once hidden, comes back from a *Help on this page* button; a help an administrator rewrote is left as it is.
- An acronym no longer stands alone as a label : *Sharing level (TLP)*, *Single point of failure (SPOF)*, *Recovery time objective (RTO)*, *Key performance indicator (KPI)*, *Involvement (RACI)*, and the English labels no longer carry the French *DIC*.
- The buttons that open a creation read *New ...* everywhere, in the search palette and on the users and groups pages as on the registers.
- The dashboard summary heads its card on one line when there is no written briefing, instead of leaving a column empty.
- Empty selects read "Choose…" or "None" instead of a row of dashes, and on a phone the form step indicator shows the current step's name in full.
- The security needs a support asset inherits are empty (*Not assessed*, `null` over the REST API and MCP) until an essential asset that relies on it is assessed, instead of reading *Negligible*.
- A card of a record page with nothing filled in reads as one line naming its fields, instead of a grid of dashes.
- The criticality of a supplier, the type of a site, the severity of a vulnerability and the method of a risk assessment are no longer preselected when one is created : the form asks, and waits for the answer.
- The form of an issue asks its category alone, offered under *Internal* and *External* : the type follows from it, and a pair the record refuses can no longer be composed.
- The thresholds of an indicator are picked among those its format allows (a number falls below or exceeds a figure, a yes or no answer is true or false), and its format is asked with no answer preselected.
- A card or a label names what it holds (*Obligation*, *Transmission*, *Deadline status*, *Child documents*) where it described it (*What is owed*, *What was transmitted*, *Where we stand*, *Documents under it*).
- A compliance action plan is created without its gap and its remediation plan : they are written on its page, and its lifecycle refuses to submit it for validation without them (web, REST API, MCP).
- A compliance assessment cannot be planned without a framework and its dates on any surface : the rule was checked by the web interface alone, and is now held by its lifecycle for the REST API and the MCP server as well.
- The form of a requirement offers the sections of its framework alone and refuses one of another framework; how a nonconformity came to light is no longer preselected when one is raised.
- The ratings of an ISO 27005 analysis are picked on the named levels of its assessment's criteria, where a bare number was typed; the analysis is rated on its own page, and its dialogs say *analysis* where they said *ISO 27005 risk*.
- The container runs as an unprivileged account (uid 1000) instead of root, handing over a media volume written by an earlier image on first start.
- `DEBUG` is off unless set, instead of on : development environments set `DEBUG=True` (`.env.example` and `core.settings_local` do).
- Outside `DEBUG`, the session and CSRF cookies are only sent over HTTPS, and a session ends twelve hours after sign-in instead of two weeks (`SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, `SESSION_COOKIE_AGE`); the sign-in page says so when opened over plain http.
- Maps are off until a tile provider is named in `MAP_TILE_URL` : an instance that showed maps must set it to keep them (`https://tile.openstreetmap.org/{z}/{x}/{y}.png` for the former default).
- The image reads which proxy to believe from `FORWARDED_ALLOW_IPS` (still `*` by default) instead of a fixed command-line flag.
- A group's permission matrix folds each module behind a line showing how many of its permissions the group holds, instead of a form several screens long.
- The geocoder the maps and address fields called from the browser is a setting, `MAP_GEOCODER_URL`, off by default : addresses no longer leave the instance unless a geocoder is named.
- The image ships the PostgreSQL client tools of the server the compose file runs, for the backup and restore commands.
- The compose file fixes the major versions of its services (`postgres:18`, `redis:8-alpine`) instead of following `latest`.
- CI crawls every page and form of the demo dataset, and runs the suite a second time on PostgreSQL with every migration replayed (on `main`, and on a pull request labelled `ci:postgres`).
- Python dependencies install from a compiled `requirements.txt` (exact versions, hash-checked, generated from `requirements.in` and refreshed weekly by Dependabot) instead of the latest release of everything, with Django held on its 5.2 LTS line and the image on Python 3.14, the version CI tests.
- The application logs to the console in production as under `DEBUG`, tracebacks of request errors included (`LOG_LEVEL` sets the verbosity).
- Texts meet the WCAG 2.2 AA contrast level in both themes : the muted grey, status badges, and links and accent labels on the dark theme take readable tones (ink tokens `--accent-text`, `--success-text`...), and placeholders lose their transparency.
- The calendar shows an event as a tint and a rule in its category colour with the title in the text colour, instead of white text on hues half of which could not carry it.
- A custom accent colour (company or Trust Center) stays readable whatever it is : the text drawn in it, the label on it and the Trust Center banner are derived from it for each theme.
- Keyboard focus is one neutral ring that stands out on every surface, instead of pale halos on buttons, close buttons and switchers.
- CI audits every page of the demo dataset with axe-core in the light and the dark theme, recomputes the palette's contrast ratios and parses every page for unnamed controls.
- Every form ends on a footer whose buttons carry words (Cancel, Previous, Next, Create or Save) instead of arrows floating outside the dialog; its steps are buttons, a record being edited can be saved from any step, and a required field left empty answers with its own name.
- A scope cannot be submitted nor put in force until it says where it stops and names a manager, and an essential asset cannot become active until its security needs are assessed : the refusal says what remains to be done, on the web, the REST API and MCP.
- The security needs of an essential asset have no default level : left out they read *Not assessed* instead of *Medium*, on the REST API and MCP as well, and the web form no longer asks for the type, which its category names.

### Fixed

- Creating or editing a management review, and editing an ISMS change, failed with a server error; their scope pickers now offer the linkable scopes.
- Opening an assessment result's edit page directly failed with a server error, and so did the preview of a finding recorded without an audit.
- The lifecycle journal of a compliance assessment did not record who moved it; every transition now names its author, from the page, the REST API and the MCP server.
- On a phone, a selected item of a multi-select whose label was cut short scrolled sideways, out of reach of the keyboard and hiding its remove button; the label now ends on an ellipsis and the button stays in reach.
- On a phone, a risk matrix wider than the screen scrolled sideways without being reachable from the keyboard.
- A malformed identifier in the address of a risk creation, or posted to the form of a risk or of a treatment plan, raised a server error.
- The register of ISO 27005 analyses stacked two links in a cell, closer than a pointer target allows.
- The links of the component inventory in the About dialog were shorter and closer together than a pointer target allows.
- Saving a role silently removed a holder whose account had been deactivated.
- In EBIOS RM, adding a second feared event for the same essential asset and criterion, giving two steps of an attack path or two techniques of a scenario the same rank, and deleting a row that its lifecycle protects, failed with a server error; a targeted objective was offered the feared events of every study, the texts of the study framework and of the summary were shown with their formatting tags, and the French named a risk source *source du risque*.
- Creating a predefined indicator without choosing its source failed with a server error, and every reader of an indicator was shown a Delete button.
- The description of a treatment action and the measurement method of an objective, typed in the editor, were shown with their formatting tags.
- Global search results for sites had no link, and the SWOT item and strategy dialogs could not be closed or cancelled.
- The group permission matrix lacked its Validate column, which shifted the labels of the columns after it, and the decision and ISMS change forms never showed field errors.
- Risk criteria pages had no lifecycle stepper, so a criteria set could not be submitted or validated from the interface.
- With Redis unreachable, the detection of single points of failure and the index rebuild stopped; they now take a lock of their own process, and a database lock keeps two workers from applying the migrations at once.
- Installing a new database no longer leaves hundreds of `relation does not exist` errors in the database log, and its progress screen restarts a job that is not running instead of waiting for ever.
- Sentences shown with a count (the evidence and the notification obligations of an incident, the requirements of a nonconformity) appeared in English in the French interface, their translation being filed as a singular, and two strings still named the product *Open GRC*.
- The empty risk assessment register explained compliance assessments, and the risk module called its assessments *évaluations*.
- Choosing another assessment on a new risk now reloads its likelihood and impact scales, in the dialog as on the page (it only ever worked on a fully reloaded page).
- Opening a drawer-only delete link directly (incidents, nonconformities, supplier contacts and sub-processors) rendered a bare dialog fragment instead of a confirmation page.
- The Trust Center hub and the semantic index pages showed a loose eyebrow (the hub's even read "Strategy") instead of their menu breadcrumb.
- Lifecycle governance helpers given an `app.Model` label (rather than the model) silently used the default lifecycle.
- The dashboard failed with a server error for every non-superuser member of a group that allows all scopes.
- Submitting the nonconformity register form failed with a server error when its source was Audit; that source is now only offered for a finding that has its audit.
- A lifecycle edited in the administration was only applied by the worker process that saved it; every worker now picks it up within `LIFECYCLE_CACHE_TTL` seconds (5 by default).
- Pages touching the cache (the update check, the assistant briefing, the Trust Center rate limiter) failed with a server error whenever Redis was unreachable; the cache now degrades to a miss and logs the outage.
- The Docker-less development settings (`core.settings_local`) still required Redis for the cache.
- A framework listed its requirements in lexicographic order (A.5.10 before A.5.2) instead of the natural order of their numbers.
- For the first hours of each day, "today" was still the previous day (the UTC date) : overdue action plans, expired contracts and certificates, and document review dates were a day behind.
- A risk's scoring snapshot showed its capture time as a raw ISO timestamp.
- Two developer comments were printed as text on the management review page and in an incident's regulatory obligations.
- The pages of an API list could repeat a record and skip another, on the lists with no default order and under any `?ordering=` with ties; every list is now paginated in a total order.
- The `date_before` filter of the risks API left out the risks created on the day given.
- The dashboard's "what's new" dialog never appeared on the published image, which left `CHANGELOG.md` out; the image also carries its `LICENSE` and `README.md` again.
- The documented deployment of the published image had no volume for uploaded files, which were lost each time the container was recreated.
- A list table wider than its card had its last columns clipped and unreachable on laptop screens; it now scrolls inside the card.
- The scope, site and supplier maps showed an "API key required" watermark instead of the map, their tile provider no longer serving anonymous requests; they draw OpenStreetMap tiles by default.
- The Edit buttons of fourteen lists and the days of the calendar's year view could not be reached from the keyboard.
- The parent scopes shown in a scope pill were dimmed under the contrast threshold; they are now set apart by their weight.
- The level name in a cell of the risk matrix was white on the default red, under the contrast threshold; the label of a cell is now chosen by its measured contrast.
- Saving a record filed under several scopes removed, without a word, the scopes the editor was not given.
- The members of an asset group could not be chosen from the interface, which only listed them; its page has a *Members* card that picks them.
- The page of a site, a supplier or a scope kept a tall blank area where its map could not be drawn (no basemap configured, or an address nobody could place).
- Filter panel fields, grid forms (risk criteria, supplier type requirements, review participants), the mobile menu button and the calendar arrows had no accessible name.
- The public Trust Center was unreadable in places on the dark theme (navy links on charcoal, grey text and buttons).
- On a phone, the rows of the dashboard's progress-bar tiles (frameworks, objectives) collapsed onto each other.
- Form dialogs had no accessible name, their searchable selects were announced twice (once with no name), and a table scrolling sideways could not be scrolled from the keyboard.
- The dashboard's framework tile read "90 requirement" whatever the count.
- The action log loaded the whole audit trail into memory on every visit; it now asks the database for the page shown, so opening it no longer slows down as the history grows.
- The dashboard of an instance with nothing in it read "you're all clear" and showed an overall compliance of 0% in red; it now says there is nothing to report yet.
- Setting the security needs of an essential asset in the web form did not record the assessment in its history, as the REST API did.
- The help banner of the scope list still said that a single scope could be active at a time.

### Security

- Saving a group's permission matrix silently revoked the permissions it did not display (assess, implement, close, cancel, override dates); they now have a column, and permissions outside the registry are never touched.
- Tag colours are validated before reaching a style attribute, and Cancel / Back links no longer echo an unchecked Referer header.
- The risk scale endpoint no longer answers with the criteria of an assessment outside the user's scopes.
- The relation pickers of every list's advanced filter listed related records unscoped, printing the names of records outside the reader's scopes into the page.
- Rich text fields were rendered unsanitized on every detail page and report (stored XSS); they are now sanitized at render time (a value with no markup stays escaped text with its line breaks), and JSON embedded in pages can no longer close its script element.
- With `DEBUG` off, Cairn refuses to start while `SECRET_KEY` is one of the public placeholder values, instead of signing sessions with a key anyone can read.
- Nonconformities raised by an incident were visible to every finding reader whatever their scopes, and the MCP finding update and delete tools did not check the caller's scopes.
- Every page is served with a Content Security Policy : only the instance's own scripts run (inline ones by a per-response nonce), no inline event handler, no `eval`, no other origin than the map services (`CSP_MODE`).
- Refusing an OAuth consent redirected to the address carried by the form before checking it was one the application registered.
- An OAuth token obtained through the consent screen acted as whoever had authorized the client first, not as the person who consented : tokens now carry their user, and those issued to public clients before this release are revoked (their users approve the client once more).
- OAuth client registration accepted any redirect address, including none (then any address was accepted at consent) : it requires `https`, loopback `http` or an application's private scheme, matched exactly, and the consent screen shows where the access goes.
- OAuth access tokens expire (`OAUTH_ACCESS_TOKEN_LIFETIME_DAYS`, 90 days by default) instead of living for ever; existing ones are brought back to that lifetime.
- The open OAuth endpoints (registration, token) are rate limited, an authorization code is spent atomically, and consent is only offered to accounts allowed to use MCP.
- A user restricted to some scopes could change or delete the records of another scope by their address, and read them through 28 REST resources (the whole EBIOS RM API among them), report generation and the generic transition and history endpoints : every way a record is reached now checks the scopes, and structural tests fail on a surface that does not.
- The transitions of 22 lifecycles (scopes, assets, suppliers, risks, risk acceptances, assessments, action plans, management reviews) declared no permission and could be performed by a reader, or by a user with no permission on the module, through the generic transition endpoint and the MCP transition tools : a transition now asks for the permission to change the record.
- The verdict of an EBIOS RM workshop, the validation, implementation, closure and cancellation of an action plan and the closure of a management review asked for their own permission on their dedicated screen only : the generic transition endpoint and the MCP tools performed them for anyone who could edit the record; the lifecycles now name these permissions, and a step written directly through MCP is held to them.
- A stored contract, certificate or Trust Center document was served with the content type its uploader declared; one declared as a script or a page is now served as opaque bytes.
- Pages and API answers carry `Cross-Origin-Resource-Policy: same-origin` and a `Permissions-Policy` switching off the browser features the application never uses.
- The MCP server let a user restricted to one scope list, read, change and delete the records of every other (risks, requirements, dependencies, assessment results, management reviews and more) : sixty tool families were registered with the scope filter off and forty fetches by identifier had none; every tool now reads and writes within its caller's scopes, and answers *not found* for the rest.
- A form, the REST API and the MCP server let a user restricted to one scope link a record to the record of another (whose name came back in the answer) and file a record under a scope they were not given; a relation now offers and accepts what the user may select, and a user limited to scopes files what they create under one of them.
- A generated report that hung under no assessment (statement of applicability, management review minutes, risk register, ISO 27005 report) was listed to and downloaded by any holder of the read permission whatever their scopes, and the report register listed them all; a report is now filed under the scopes it was made from and read by who is given every one of them.
- The registers of dependencies, sites and management reviews listed the records of every scope to any holder of the read permission, and the register of nonconformities those raised by an incident of another scope; a site is now reached through the scopes it is filed under and those that include it.

## [0.36.1] - 2026-11-03

### Added

- `scripts/bootstrap_dev.sh` provisions a Docker-less Debian/Ubuntu development sandbox with every system and Python dependency the image carries.

### Changed

- The sidebar menu ships folded and keeps a single group open at a time : the one holding the current page.
- Front-end libraries move to their current releases : DOMPurify 3.4.15 and ECharts 6.1.0.

### Fixed

- Lifecycle graphs stayed blank until a manual reload when their page was reached by in-app navigation, on detail pages as well as in the lifecycle editor.

### Security

- The ECharts upgrade clears GHSA-fgmj-fm8m-jvvx, an XSS in the `lines` series tooltip that Cairn's charts never exercised.

## [0.36.0] - 2026-08-28

### Added

- The About dialog lists the open source libraries the instance is built on as `owner / library - version` in two columns, each linking to its official repository, also exposed at `GET /api/v1/dependencies` and through the `list_dependencies` MCP tool.
- Front-end libraries are served from the instance instead of a CDN : `manage.py vendor_assets` mirrors them into `static/vendor/` from the pins in `core/dependencies.py`, at Docker build time or on a direct install's first launch, verifying each download against its Subresource-Integrity digest.
- The About dialog reports whether a newer release is published, from the GitHub releases of the project, also exposed at `GET /api/v1/update-check` and through the `check_for_updates` MCP tool (`UPDATE_CHECK_ENABLED=False` to switch it off).

### Changed

- Front-end libraries are upgraded to their current releases : Bootstrap Icons 1.13.1, htmx 2.0.10, Tom Select 2.6.2, DOMPurify 3.4.14, Sortable 1.15.7 and ECharts 5.6.0.

## [0.35.1] - 2026-08-28

### Added

- Documentation is rebuilt from `docs/` into the GitHub wiki by CI on every version tag, with a user guide, a technical section, an SDK and a code-generated reference (`manage.py generate_docs`), gated on every push by a staleness and link check.
- HTTPS hardening is configurable from the environment (`SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, `SECURE_SSL_REDIRECT`, `SECURE_HSTS_*`), all defaulting to off so an HTTP-only deployment is unaffected.

### Changed

- `README.md` is a short overview again : the encyclopaedic module descriptions move to the user guide, leaving a scannable feature table and four points on what the platform actually does differently.
- `.env.example` documents the 21 environment variables the code reads but the template omitted, among them the email, Redis, WebAuthn and assistant tuning settings.
- The demo dataset ends on realistic lifecycle states : every default-lifecycle row used to stay in `draft`, so roughly seven hundred records counted in no report and the dashboard read 0% compliance.
- Action plan cancellable statuses are an ordered tuple rather than a set, so the generated lifecycle no longer varies between processes.

### Fixed

- `recalculate_compliance` raised `FieldError` on every invocation : it selected the assessment's `framework`, a relation that had become the `frameworks` many-to-many.
- The Docker image declared an `MIT` license label while the project is `AGPL-3.0-or-later`.

## [0.35.0] - 2026-08-28

### Added

- Suppliers gain a supply-chain layer: subsidiaries (filiales) via a `parent_company` self-relation and sub-processors (sous-délégataires) via the `SupplierSubprocessor` link, exposed on the detail page, the REST API and MCP tools.
- Security incident register (module 6, ISO 27001 A.5.24 to A.5.28 and A.6.8): security events assessed before promotion, incidents with an append-only chronology, evidence under a chain of custody, statutory notification obligations on their own legal clocks, GDPR breach qualification and post-incident reviews feeding the nonconformity register.

### Changed

- Cairn is now licensed under the GNU Affero General Public License v3 or later (`AGPL-3.0-or-later`) instead of MIT, with an SPDX header on every source file and a trademark notice in `README.md`.
- Findings are now the organisation-wide nonconformity register (ISO 27001 clause 10.1/10.2), with their own list and detail pages under Compliance: they carry a source, survive the deletion of the audit that raised them, record whether the corrective action was effective, and move from `compliance.assessment.*` to their own `compliance.finding.*` permissions, which the migration grants to every group that already held the assessment ones.

### Security

- Child records that inherit their scopes from a parent (requirements, sections, assessment results, findings, requirement mappings) are no longer readable, transitionable or auditable outside the user's scopes: the generic workflow and history endpoints and the MCP list layer guarded only on a direct `scopes` relation and returned everything else unfiltered.

### Fixed

- Column-header sorting on list pages works again: the table toolbar lost the `data-sort-view-key` marker the sort script needs, so header clicks were silently ignored.
- Onboarding no longer returns a 500 on every request when the shared cache (Redis) is unreachable: the runner degrades to a process-local coordination store instead of propagating the connection error.

## [0.34.1] - 2026-07-03

### Added

- MCP `create_user` tool and DRF `POST /api/v1/users/invite/` endpoint provision users via an invitation flow (unusable password, returned single-use activation link) so imports can reference owners; gated by `system.users.create`.
- MCP `batch_create_*` accept an optional `match_on` business key for idempotent upsert, so a partially failed import can be replayed without creating duplicates.

### Changed

- MCP `get_me` and DRF `auth/me` report `can_override_import_dates` / `can_create_users` capability flags, and create / batch tools flag when supplied `created_at` / `updated_at` were ignored for lack of permission.

### Fixed

- Translated strings placed in single-quoted JavaScript literals are now escaped with `escapejs`, so a French translation containing an apostrophe (e.g. the rich-text toolbar's "l'URL") no longer breaks the page script.

## [0.34.0] - 2026-07-03

### Added

- MCP `create_*` / `batch_create_*` can preserve legacy `created_at` / `updated_at` timestamps for callers holding the new `system.data_import.override_dates` permission (bulk migration); ignored otherwise.

## [0.33.3] - 2026-07-01

### Fixed

- Static files are now served by the ASGI app via WhiteNoise, so they load under `DEBUG=False` behind uvicorn without a reverse proxy (the previous setup returned `text/html` 404s that `nosniff` blocked).

## [0.33.2] - 2026-07-01

### Fixed

- Static assets are now re-collected at container start (not only at image build), so newly added JS/CSS reach `STATIC_ROOT` under the compose bind-mount and no-rebuild deploys, fixing `text/html`/`nosniff` errors on files like `lifecycle_graph.js`.

## [0.33.1] - 2026-07-01

### Fixed

- First-run onboarding is now safe under multiple web workers: the migration/seed runner and its progress live in the shared Redis cache behind a cross-worker lock, so several uvicorn workers no longer race the same migrations (duplicate-column crashes, progress bar jumping backwards).
- Configured a shared Redis cache (`CACHES`), making the semantic-index rebuild lock, the new SPOF single-runner gate and the trust-centre rate limiter effective across worker processes instead of silently per-process.

## [0.33.0] - 2026-07-01

### Added

- Single JSON-driven, admin-editable lifecycle engine (`core.lifecycle`) replacing the first-generation workflow: graphical editor (Administration > General > Lifecycles) with Steps/Transitions/JSON tabs and a live dagre graph preview, generic Draft/Archived bookends, per-transition permissions and an immutable `LifecycleEvent` log, wiring every domain element (assets, compliance, risks/EBIOS, reports, trust center, scopes, suppliers, sites) through the web stepper, DRF `.../transition/` and MCP `transition_*` tools.
- Lifecycle step triggers fired on entry, starting with a Yes/No confirmation modal (`"triggers": [{"type": "confirm"}]`), toggled per step in the editor.
- Lifecycle graphs rendered with dagre and locally-vendored d3/dagre (air-gapped safe), edges routed so arrows never overlap a node at any width.
- Documents area in Assets: Contracts (multi-party, amendments, inline PDF) and Certificates (bound to a framework, inline PDF), each a full web / REST / MCP slice.
- First-run onboarding screen: applies pending migrations behind a progress bar, then a start-from-scratch wizard (company + first admin) or the Voltara demo seed.
- Supplier contacts, address with map (Photon autocomplete + Leaflet) and compliance evaluation, each via UI, REST and MCP.
- Risk-driven applicability for compliance requirements (`Framework.applicability_managed_by_risks`), via UI, REST and MCP.
- `page_header` gains `logo` and `compact` options, plus a "Last modified by" chip in detail headers.

### Changed

- Scope, Supplier and Site detail pages rebuilt on the standardised 2-column layout (hero map, icon info rows, sticky KPI rail); the Sites sidebar entry is flattened to a top-level link and the scope hero map plots the whole perimeter subtree.
- Dependency graph switched to a layered dagre layout with an LR/TB orientation toggle and a cascade highlight of a node's upstream/downstream chain.
- UI system pass: frosted buttons and modals, full-bleed page headers, icon-only history trigger, rich-text editor moved from Jodit to pell, multi-step form nav floated outside the modal.
- Demo seed derives all dates from the current date and sets real supplier addresses/coordinates so it never goes stale.

### Removed

- First-generation workflow engine deleted (`core/workflow.py`, per-app `workflows.py`, `WorkflowStepperMixin`, `includes/workflow_stepper.html`).
- Separate approval axis removed (`is_approved`/`approved_by`/`approved_at`, the `approve_*` MCP tools and the approval UI); validation is now reaching a reportable lifecycle step.
- Legacy duplicate `status` column dropped where it merely mirrored `workflow_state` (kept as a read/write alias via `LegacyStatusMixin`).
- `VersioningConfig` admin screen and model deleted (migration `core.0005_delete_versioningconfig`).

### Fixed

- List and detail views no longer return HTTP 500 on malformed query/POST parameters (`?q=` length clamp, `?rule=` validation, UUID/int/date coercion via `core.query_params`) (issues #154, #155, #156).
- Assorted GUI input no longer triggers unhandled exceptions (issue #158).
- WebSockets work under `manage.py runserver` (added `daphne`), fixing `404` on every `/ws/...` route in the dev server.
- Docker image build fixed by disabling the optional `autobahn` NVX C extension (`AUTOBAHN_USE_NVX=0`).
- Scope-tree multi-select layout and the Firefox hidden-first-checkbox rendering.

### Security

- Transition API and MCP JSON-RPC errors no longer leak raw exception strings (CodeQL `py/stack-trace-exposure`).
- Open redirects closed via a shared `core.redirects.safe_redirect_target` guard (CodeQL `py/url-redirection`).
- Sidebar flyout and onboarding logo preview hardened against DOM XSS (CodeQL `js/xss-through-dom`).
- CI `Tests` workflow pinned to least-privilege `contents: read` permissions (CodeQL `actions/missing-workflow-permissions`).

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

[0.36.1]: https://github.com/frousselet/cairn/compare/v0.36.0...v0.36.1
[0.36.0]: https://github.com/frousselet/cairn/compare/v0.35.1...v0.36.0
[0.35.1]: https://github.com/frousselet/cairn/compare/v0.35.0...v0.35.1
[0.35.0]: https://github.com/frousselet/cairn/compare/v0.34.1...v0.35.0
[0.34.1]: https://github.com/frousselet/cairn/compare/v0.34.0...v0.34.1
[0.34.0]: https://github.com/frousselet/cairn/compare/v0.33.3...v0.34.0
[0.33.3]: https://github.com/frousselet/cairn/compare/v0.33.2...v0.33.3
[0.33.2]: https://github.com/frousselet/cairn/compare/v0.33.1...v0.33.2
[0.33.1]: https://github.com/frousselet/cairn/compare/v0.33.0...v0.33.1
[0.33.0]: https://github.com/frousselet/cairn/compare/v0.32.0...v0.33.0
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
