# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Cairn is a Governance, Risk and Compliance (GRC) platform built with Django 5.2, PostgreSQL 18, and Bootstrap 5.3 + HTMX for the frontend. It covers organizational context, asset management, risk management (ISO 27005/EBIOS RM), and compliance tracking.

## Development Commands

### Running with Docker

```bash
docker compose up --build          # Start all services
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser
```

### Running Tests

```bash
pytest                             # Run all tests
pytest accounts/tests/             # Run tests for a specific app
pytest accounts/tests/test_models.py  # Run a specific test file
pytest -k "test_name"              # Run a specific test by name
pytest --co                        # List tests without running them
```

Tests use `core.settings_test` (configured in `pytest.ini`), which uses SQLite in-memory and fast MD5 password hashing. CI runs the suite a second time on PostgreSQL with every migration replayed (`pytest --ds=core.settings_test_postgres`, see `docs/technical/testing.md`) : on `main`, and on a pull request when it carries the `ci:postgres` label. The interface sweep (`core/tests/test_site_sweep.py`, about a minute) crawls every page and submits every form on the demo dataset; leave it out while iterating with `pytest -m "not sweep"`.

### Django Management

```bash
python manage.py runserver 0.0.0.0:8000   # Dev server (used by docker-compose)
python manage.py makemigrations           # Generate migrations
python manage.py migrate                  # Apply migrations
python manage.py compilemessages          # Compile i18n translation files
python manage.py collectstatic --noinput  # Collect static files
python manage.py backup                   # Database + media into one verified archive (BACKUP_DIR)
python manage.py restore <archive>        # Put the instance back in the state of an archive
```

## Architecture

### Django Apps

| App | Purpose |
| ----- | --------- |
| `core` | Project settings, root URL config, shared mixins (`SortableListMixin`), base views (dashboard, calendar) |
| `accounts` | Custom `User` model (email-based auth, UUID PKs), groups with 6 system roles, custom permissions (`module.feature.action` codenames), passkey/WebAuthn support, access logging |
| `context` | Organizational context: Scopes, Sites, Issues, Stakeholders, Objectives, SWOT, Roles, Activities, Tags |
| `assets` | Essential assets (with DIC valuation), support assets (IT infra with lifecycle), dependencies, asset groups, suppliers |
| `compliance` | Frameworks, sections, requirements, assessments, action plans, inter-framework mappings, Excel import |
| `risks` | Risk assessments, risk criteria, risks (3-level tracking), threats, vulnerabilities, ISO 27005 analysis, treatment plans, risk acceptance |
| `helpers` | Help banners with multilingual content |
| `mcp` | MCP (Model Context Protocol) server integration with OAuth 2.0 |

### Key Patterns

**Base Models** (`context/models/base.py`):

- `BaseModel` - UUID PK, timestamps, `created_by`, lifecycle state (`workflow_state`), versioning, tags. All domain models inherit from this.
- `ScopedModel` - extends `BaseModel` with many-to-many `scopes` for organizational tenancy.
- `ReferenceGeneratorMixin` - auto-generates sequential references (e.g., `RISK-1`, `ASST-2`). Subclasses set a 4-char `REFERENCE_PREFIX`.

**App Structure** - each domain app follows a consistent layout:

- `models/` - model package with one file per model
- `views.py` - class-based views (Django generic views)
- `forms.py` - model forms
- `urls.py` - web UI URL patterns
- `api/` - DRF serializers, viewsets, and URL routes under `/api/v1/`
- `constants.py` - choice tuples and enums
- `templates/<app>/` - Django templates
- `tests/` - tests with `factories.py` (factory-boy) and `test_*.py` files

**URL Structure**:

- Web UI: `/<app>/...` (e.g., `/context/`, `/assets/`, `/risks/`)
- REST API: `/api/v1/<app>/...`
- Admin: `/admin/`

**Testing**: Uses pytest-django with factory-boy factories. Each app has a `tests/factories.py` defining model factories.

**Audit Trail**: All models use `django-simple-history` (`HistoricalRecords`) for change tracking.

**i18n**: Bilingual support (English/French). Translation files are in `locale/`.

**Frontend**: Server-rendered Django templates with Bootstrap 5.3, HTMX for dynamic partial updates, dark mode via OS preference.

**View Mixins** (`core/mixins.py`, `accounts/mixins.py`):

- `SortableListMixin` - server-side sorting with user preferences persisted in `User.table_preferences` JSON field
- `CreatedByMixin` - auto-populates `created_by` on form save
- `LifecycleStepperMixin` (`accounts/mixins.py`) - builds the lifecycle stepper context for a DetailView
- `ScopeFilterMixin` - filters querysets by user's assigned scopes

**MCP Server** (`mcp/`): JSON-RPC 2.0 server with 40+ tools across all modules. Tool permissions enforced via `@require_perm` decorator. OAuth 2.0 authorization flow for external clients.

### CI/CD

GitHub Actions (`.github/workflows/`) is the CI:

- `tests.yml` (Tests) - on every push to `main` and on pull requests, three jobs: `test` installs dependencies, runs `ruff check`, compiles `.po` translations, then runs `pytest -x -v --cov` on SQLite; `test (PostgreSQL, migrations)` checks that models and migrations are in sync (`makemigrations --check`) and runs the same suite on PostgreSQL 18 (the major the compose file ships) with every migration replayed; it runs on every push to `main`, and on a pull request only with the `ci:postgres` label or a manual run of the workflow (add the label when a change touches a migration, a raw query, or database-side grouping / ordering). `accessibility (axe-core, both themes)` migrates a PostgreSQL service with the real migrations (cached as a dump keyed on the migration files), seeds and serves a demo instance, then runs `scripts/a11y_audit.py` : axe-core on every page of the screenshot set in the light and the dark theme, failing on any WCAG 2.2 A / AA violation, any Content Security Policy violation and any script error. Never build that instance from the models to save time : what data migrations write (help content, lifecycles, reference data) is part of the pages.
- `docker-publish.yml` (Docker) - on version tags (`v*`): builds and pushes the Docker image to Docker Hub (`frousselet/cairn`) with semver + `latest` tags. Requires the `DOCKERHUB_USERNAME` / `DOCKERHUB_TOKEN` repository secrets.
- `docs.yml` (Documentation) - on every push to `main`, on pull requests and on version tags: verifies the generated reference is current (`manage.py generate_docs --check`) and that every internal documentation link resolves (`scripts/build_wiki.py --check`); on a tag it also builds the wiki and pushes it to the wiki repository. Wiki push needs a `WIKI_DEPLOY_KEY` repository secret : the private half of a **deploy key** with write access on this repository (`GITHUB_TOKEN` generally cannot write to a wiki, and fine-grained PATs have no wiki permission at all). Never use a classic PAT here : its `repo` scope would grant the workflow write access to every repository the account owns, whereas a deploy key reaches this repository alone. Without the secret the job prints the setup steps and fails rather than dying on an opaque git error.
- CodeQL scanning runs on pushes to `main` and on a schedule.

Ruff config lives in `pyproject.toml`.

### Documentation

All documentation sources live in `docs/`, which is the only source : the GitHub wiki is a rendering of it, republished by CI on every version tag. Never edit the wiki directly.

| Directory | Contents |
| --------- | -------- |
| `docs/user-guide/` | End-user documentation, illustrated from `docs/screenshots/` |
| `docs/technical/` | Architecture, installation, configuration, security, operations, i18n, testing, contributing, release process, and how the documentation system itself works |
| `docs/sdk/` | One page per extension point (dashboard widget, entity, lifecycle, REST endpoint, MCP tool, report, assistant provider, UI conventions) |
| `docs/reference/` | Exhaustive listings. Everything under `reference/generated/` is code-derived |
| `docs/specs/` | The per-module contract : one directory per module, one Markdown file per domain entity, plus `governance/` for the cross-cutting specifications |
| `docs/brand/` | The visual system |
| `docs/qa/` | Historical test-campaign artefacts, excluded from publication |

Detailed specs live in `docs/specs/` : one directory per module (`m0-accounts/`, `m1-context/`, `m2-assets/`, `m3-compliance/`, `m4-risks/` with the `ebios-rm/` sub-module, `m5-trust-center/`, `m6-incidents/`, `management-review/`, `assistant/`, `governance/`), and one Markdown file per domain entity inside each. Each module's `README.md` holds the cross-cutting sections (business rules, API conventions, permissions, UI, notifications, technical considerations). Reference the right entity file when implementing a feature change, and update it in the same commit. See `docs/specs/README.md` for the layout conventions.

The full mechanics are documented in `docs/technical/documentation.md`.

## Development Guidelines

- **MCP tools are mandatory**: Every new feature must be exposed as MCP tools in `mcp/tools.py` with accurate docstrings and parameter descriptions. MCP is the primary integration surface for external clients.
- **API endpoints are mandatory**: Every new feature must include corresponding DRF endpoints in the app's `api/` directory (serializers, viewsets, URL routes under `/api/v1/`).
- **UI quality in both themes**: All templates and CSS must render correctly in light and dark mode. Test both themes when adding or modifying UI components.
- **Audit-grade rigor**: This platform supports real compliance audits. Data integrity, traceability, and correctness are critical - lifecycle workflows, versioning, history tracking, and permission checks must never be bypassed or degraded.
- **Fix security issues autonomously**: When a security problem is identified (a CodeQL alert, information exposure, injection, open redirect, XSS, missing permission, etc.), fix it without asking for confirmation, as long as the fix introduces no regression (tests still pass). Chain such fixes and record them under a `### Security` entry in `CHANGELOG.md`.
- **Safe by default, and nothing leaves by default**: the secure behaviour is the one an unconfigured instance has, and the unsafe one is an explicit choice of the operator (cookies are HTTPS-only outside `DEBUG`, a session lasts twelve hours, OAuth tokens expire and act as the person who consented, maps and geocoding are off until a provider is named). A new feature that makes a browser or the server call another service is off by default, named by a setting, added to the policy in `core/csp.py` and documented as traffic leaving the instance. A stored file is served through `core.downloads.safe_content_type`, as an attachment. An identity is never inferred from something shared (an application, a link) : it comes from the session or the token of the person acting. `core/tests/test_security_defaults.py` reads the settings as a fresh process loads them.
- **Scope tenancy is checked wherever a record is reached** (`core/scoping.py`): a permission says what a user may do, their scopes on which records. A model that hangs under a scoped record declares its path (`scope_parent_lookup = "parent__scopes"` on the model, never on a view alone); a view that takes an identifier from the request and is not a generic detail / update / delete view fetches with `get_scoped_object_or_404(request.user, Model, pk=pk)` (never Django's `get_object_or_404`), a selection with `scoped_queryset`; a REST class serving such a model carries `ScopeFilterAPIMixin`, and a nested one names its parent (`scope_parent = (Model, "url_kwarg")`). A relation is a way to reach a record : a form or a serializer built by hand goes through `restrict_form_relations(form, user)` / `restrict_serializer_relations(serializer, user)` (the generic views and `ScopedFormMixin`, which lives in `core/modal_forms.py` and nowhere else, do it themselves), and a user limited to scopes files what they create under one of them. An MCP tool reads through `_reach(user, Model)` and `_fetch(user, Model, pk=...)`, never `Model.objects`, and checks what it writes with `_refuse_relations_out_of_reach`. A record out of reach answers as an unknown one (`404`, *not found*). `core/tests/test_scoping.py` walks the URLs, the models, the forms and the MCP source and fails on a surface that forgets, with an explicit list of exceptions and the reason of each; `core/tests/test_tenancy_sweep.py` asks every surface, on the demo dataset, as a user with every permission and one scope : test the surface, never the helper alone. See the Tenancy section of `docs/technical/security.md`.
- **Pages run under a Content Security Policy** (`core/csp.py`): only the instance's own script files and the inline scripts carrying the response's nonce are run. Every inline `<script>` carries `nonce="{% csp_nonce %}"`; never write an inline event handler (`onclick=`...) : name an action registered in `window.cairnActions` (`data-on-click="name" data-arg="..."`, `static/js/cairn/actions.js`; `data-confirm="..."` for a confirmation); never use `hx-on`, a `js:` value or a trigger filter (htmx `allowEval` is off); never load anything from another origin (a new outside service is a setting added to the policy and documented as traffic leaving the browser). A page that breaks this still renders and passes its view tests, its controls just do nothing : `core/tests/test_csp.py` and the browser audit (`scripts/a11y_audit.py`, which fails on any policy violation or script error) are what catch it. See the Scripts section of `docs/sdk/ui-conventions.md`.
- **Accessibility is checked, not assumed (WCAG 2.2 AA)**: text takes a text token (`--text-primary`, `--text-secondary`, `--text-muted`) or, for a colour, its *ink* token (`--accent-text`, `--success-text`, `--warning-text`, `--danger-text`, `--info-text`) : never a fill token (`--accent`, `--success`...) as a text colour, never a hard-coded white on an accent fill (`--accent-contrast`), never an `opacity` to quieten a text. Every control has an accessible name (an `aria-label` on an icon-only button, a label or `aria-label` on a form control; a formset rendered as a grid uses `LabelledRowsFormSet`), every acting link keeps an `href` beside its `hx-get`, a focus style uses `--focus-ring`, and an interaction by dragging has a button that does the same. Three checks enforce it : `core/tests/test_contrast.py` (the tokens), the markup audit of the interface sweep (every page), and `scripts/a11y_audit.py` (axe-core in a browser, in CI). A colour typed by an administrator goes through `core/colors.py`. What the product states about its own accessibility is one statement (`core/accessibility.py` : the About dialog, `GET /api/v1/accessibility/`, the `get_accessibility_statement` MCP tool) : built to meet the level, conformance `not_assessed`. Never write a conformance claim anywhere (interface, README, documentation) that goes beyond it, and never change the status without the record of the evaluation that establishes it. See `docs/technical/testing.md` and the Accessibility section of `docs/sdk/ui-conventions.md`.
- **A newcomer must be able to use it (usability standard)**: `docs/sdk/usability-standard.md` is the standard, rule by rule, and `core/tests/test_usability_standard.py` lists the screens held to it (scopes and essential assets first; add an entity to that list when it is brought to the standard, never claim it otherwise). Its idea is *create short, complete on the record* : a creation form asks for six fields at most on one screen (its own form class and `Meta.fields`) and lands on the record (`land_on_record = True`); each step of the edit form is a section (`Step(..., key=..., intro=...)`) that the matching card of the detail page opens on its own (`{% section_edit %}`); the model says what complete means (`COMPLETENESS`, `core/completeness.py`) and the page lists it (`{% completeness_card %}`, `CompleteOnRecordMixin`), the lifecycle refusing the steps named in `before` while a blocking requirement is missing. A helper says what its label does not (an example, a consequence, how to answer) or is absent, never the label again; a label is words, an acronym follows in brackets; a default never stands for a decision (an unassessed level is empty and reads *Not assessed*); a button carries its word (*Create*, *Save*, *Previous*, *Next*, *Cancel*); an empty register ends on `{% list_empty %}`. An action names what it is about : a step to take, a line of the *To complete* list, the title of a card or of a form section says *List the essential assets*, *Assign an owner*, *Set the next review date*, with the word of the menu and of the field, never a description in its place (*List what the business cannot do without*, *Name who answers for it*); a helper or an empty state names its subject too (*The person responsible for the objective*, not *Whoever answers for it*). The words are held for the whole product : one thing has one name, the one of `docs/brand/glossary.md` (adopted; `core/glossary.py` is the same vocabulary shown in the application, and a new notion gets its row and its entry before its first string), an acronym is never a label alone, and every page has a help written for a newcomer (a title that says what the thing is, an example, what to do first; a data migration of `helpers`, never an inline text). `core/tests/test_glossary.py`, `core/tests/test_translations.py` and `helpers/tests/test_help_content.py` fail on a retired spelling, a string without its French, a plural filed as a singular or a help that explains nothing.
- **Mobile-first care**: Always test and ensure UI components render well on mobile. Pay special attention to multi-select widgets, sticky bars, and form layouts on small screens.
- **Systematic French translations**: Every new user-facing string must be wrapped with `_()` or `{% trans %}` and have a corresponding French translation in `locale/fr/LC_MESSAGES/django.po`. Never leave untranslated strings.
- **No duplicate translation entries**: After modifying `locale/fr/LC_MESSAGES/django.po`, always verify there are no duplicate `msgid` entries (same `msgid` without different `msgctxt`). Duplicates cause `compilemessages` to fail. If a string already exists in the `.po` file (e.g., from another app/context), use `pgettext_lazy` in Python and `{% trans "..." context "..." %}` in templates to disambiguate, and add the entry with a `msgctxt` line in the `.po` file.
- **Lifecycles govern every domain element**: all `BaseModel` subclasses run a registered lifecycle (`core/lifecycle.py`; default 4-state Draft / Pending / Validated / Archived, specific lifecycles declared per app in `<app>/lifecycles.py` and assigned via `LIFECYCLE_NAME`). Governance is step metadata (`counts_in_reports`, `linkable`, `deletable`): never hardcode status values in reports, pickers or deletion logic - use `reportable()` / `linkable()` / `deletable_states()` and the model properties. New entities with operational stages get a specific lifecycle generated from their transition constants (single source of truth). There is no separate approval axis: validation means reaching a reportable step, gated by the transition's `permission_action`. A transition that declares no `permission_action` and is restricted to no role or user asks for the entity's `update` permission (or `approve`) : no transition is open to a reader (`core.lifecycle.user_can_perform`, `core/tests/test_transition_permissions.py`). The canonical spec is `docs/specs/governance/workflow.md` (engine internals in `lifecycle.md`).
- **Lifecycle stepper UI for state transitions**: every detail page renders the generic lifecycle stepper: add `LifecycleStepperMixin` (`accounts/mixins.py`) to the DetailView and `{% include "includes/lifecycle_stepper.html" %}` to the template. It renders the **lifecycle bar** : one line built from the registered lifecycle with the steps of the path the record is on (completed / current as its status badge / ahead, read from the schema so a branch that was not taken is left off), a button named after the transition for each step the user may move to (permission-aware, highlighted forward, quiet for a way back or an exit), and a toggle that opens the full directed graph underneath; the shared comment and confirmation modals are gated by each transition's `requires_comment` and the target step's `confirm` trigger. Transitions post to `workflow:transition` by default; views with bespoke side effects set `lifecycle_transition_url_name`. State badges use `{% workflow_badge obj %}`. Never use a hand-written button or a status select for a lifecycle transition, never render the graph in place of the bar, and never reintroduce per-page stepper markup.
- **Detail page layout - minimize tabs**: Detail pages use `{% detail_layout %}` : a stack of `{% section_card %}` in the main column and a rail of at most four `{% kpi_tile %}` (lifecycle stage first), closed by `{% record_card obj %}`. Tabs hide content and increase cognitive load - use them only when truly necessary (e.g., assessment detail with distinct Planning/Findings/History views); use collapsible section cards instead. Reference `compliance/templates/compliance/action_plan_detail.html` as the canonical example, and `docs/sdk/ui-components.md` for the anatomy.
- **Compose screens from the UI framework**: Templates are assembled from the components in `core/templatetags/ui.py` (`page_header`, `detail_layout`, `section_card`, `overview`/`ov_row`, `meta_list`/`meta_item`, `kpi_tile`, `record_card`, `ref_link`, `tag_list`, `choice_badge`, `dash`/`or_dash`, `back_url`) and the shared shells (`includes/modal_form.html`, `includes/page_form.html`, `includes/confirm_delete_modal.html`, `includes/confirm_delete_page.html`). Never hand-write card, `<dl>`, badge-colour (`{% if status == ... %}` chains) or form-field markup, and never use an inline `style` for a fixed visual choice (use a component or a utility class from `static/css/cairn/10-framework.css`). Stored rich text is rendered with `|rich` (sanitized at render time), never `|safe`. A missing pattern is added to the framework (tag + template + CSS + test + `docs/sdk/ui-components.md`), then used. The catalogue is `docs/sdk/ui-components.md`; `/styleguide/` renders it live.
- **Branch workflow**: All commits must be made on a new branch (never directly on `main`). The only exception is the release version bump: when tagging a release, the CHANGELOG promotion commit goes directly on `main` with the exact message ``Bump version `vX.Y.Z` ``.
- **One session = one branch, always**: all the work done in a single session lives on one and the same branch. Create that branch at the first commit and keep committing to it for every subsequent change in the session, even when later requests are unrelated to the first. Never open a second branch or split a session's work across branches/PRs.
- **Push as you go**: push the session branch to `origin` after each commit (`git push -u origin <branch>` the first time), so the work is never only local. Do not batch pushes to the end of a session. This is about pushing often, not committing often: keep committing whole, coherent, verified units of work, and never split one into a trail of small tentative commits ("wip", "fix typo", "try again"). If a change is not yet coherent or its tests do not pass, finish it before committing rather than committing a broken step and correcting it in the next one.
- **Fix a bad commit by rewriting it, never by adding a correction commit**: when a commit turns out to contain botched or incomplete work, amend or rebase it so history shows the work as it should have been done (`git commit --amend`, or `git rebase -i` for an older commit in the session branch). Never leave a "fix the previous commit" commit behind. Since the branch is pushed after every commit, rewriting it means re-pushing with `git push --force-with-lease` (never a bare `--force`: the lease is what refuses to clobber someone else's push). This applies **only** to the session's own feature branch: never rewrite `main`, never rewrite a commit that is already merged, and stop rewriting once someone has started reviewing the PR - at that point a follow-up commit is the honest option because the reviewer's comments anchor on the commits they read.
- **GitHub release on every version tag**: after pushing a version tag, always create the matching GitHub Release: `gh release create vX.Y.Z --title "vX.Y.Z"` with the CHANGELOG section of that version as the notes, ending with the full-changelog comparison link (`https://github.com/frousselet/cairn/compare/vPREV...vX.Y.Z`).
- **Git author**: All commits must be authored as `Claude <noreply@anthropic.com>`. Use `git commit --author="Claude <noreply@anthropic.com>"` for every commit.
- **Commit messages in English**: All git commit messages must be written in English, regardless of the conversation language.
- **English for written deliverables**: All GitHub issues, pull request titles and descriptions, and any specification or design document authored from now on must be written in English, regardless of the conversation language. French remains only for user-facing translated UI strings and pre-existing French content (existing French specs under `docs/specs/` are not retroactively translated unless requested).
- **English in code**: All code must use English - variable names, constant names, function names, class names, comments, docstrings. French is only used in user-facing translated strings (via `_()`, `pgettext_lazy()`, `{% trans %}`) and DB string values that are already stored.
- **No em dash character**: Never use the em dash character (U+2014) in code, strings, or display text. Use ` : ` or ` - ` instead.
- **Keep README.md up to date**: After any change that adds, removes or modifies a feature, model, MCP tool, dependency, or configuration, update `README.md` accordingly (feature tables, MCP tools section, tech stack, installation instructions). The README is the public-facing documentation and must always reflect the current state of the codebase.
- **Keep CHANGELOG.md up to date**: Before committing and before creating a version tag, update `CHANGELOG.md` following the [Keep a Changelog](https://keepachangelog.com/) format. Add entries under `## [Unreleased]` with the appropriate category (Added, Changed, Fixed, Removed). When tagging a release, move the unreleased entries under a new `## [x.y.z] - YYYY-MM-DD` heading and add the comparison link at the bottom of the file.
- **CHANGELOG entries are terse and non-redundant** (strict, do not repeat this mistake): (1) **one line maximum per entry** - a single sentence, no multi-paragraph explanations, no exhaustive lists of files/flags/internals (that detail lives in the git history and PR); (2) **each category appears at most once per release** - a version has a single `### Added`, a single `### Changed`, etc., never repeated blocks (consolidate before tagging); (3) **never log a Changed or Fixed entry about something Added in the same release** - fold that detail into the Added entry instead, since a feature that only exists as of this release was never in a prior state to change or fix.
- **Backups must keep restoring**: `core/backup.py` (`manage.py backup` / `restore`) writes the database and `MEDIA_ROOT` into one checksummed archive and restores it exactly (`docs/technical/operations.md`). A new place where the application stores state outside the database and `MEDIA_ROOT` must be added to the archive, with a test in `core/tests/test_backup.py`. The PostgreSQL client tools in the `Dockerfile` (`POSTGRES_MAJOR`), the compose file's `postgres` image and the CI job move together : the tools must be of the server's major.
- **Keep the seed in sync with the schema**: Whenever you change the database schema (add or modify a model or field, with a migration), add or update the matching example data in `scripts/seed_demo_data.py` so the demo dataset (Voltara Energy) keeps exercising every model and field. The seed feeds the dashboard, list views and documentation screenshots, so a schema change with no seed update leaves those surfaces empty or stale.
- **Brand guidelines must be respected**: Any visual, typographic, motion or component change MUST follow `docs/brand/brand-guidelines.md`. This is the single source of truth for the palette (one identity colour: navy `#1E3A8A`; semantic colours reserved for statuses only), typography (a single family, **GitLab Sans** - an Inter v4 derivative, OFL-1.1, self-hosted via `@font-face`, not a Google Font - used for both `--font-sans` and `--font-display`; hierarchy comes from weight, not a second face: titles `h1`/`h2`/page-header/brand at weight 810 and emphasized KPI / Overall compliance values at 900; **no negative tracking** on titles or KPIs - `letter-spacing: normal`, positive tracking only on uppercase eyebrows/badges; no UPPERCASE on titles), spacing / radii / shadow tokens, iconography (Bootstrap Icons exclusively), component principles (1px borders, soft shadows, calm hover states), motion (`--ease-out`, durations 150/220/320 ms, `prefers-reduced-motion` honoured), accessibility commitments (WCAG 2.2 AA), and voice/tone (sober, precise, action-oriented, bilingual). The logo must use the responsive system: `mark.svg` ≥ 24 px, `mark-sm.svg` ≤ 22 px. If a proposed change cannot be expressed within these constraints, update the guidelines first (with user approval), then apply.
- **Screenshots in 16:9 at 1440p**: All project and documentation screenshots (the `docs/screenshots/` set, README and docs images) must be captured at **2560x1440** (16:9, 1440p) so the set stays visually consistent. Capture with headless Chrome at that exact viewport.
- **Always use the GitHub templates**: Every GitHub issue MUST be filed through a form in `.github/ISSUE_TEMPLATE/` (`bug_report.yml` or `feature_request.yml`), and every pull request MUST use `.github/PULL_REQUEST_TEMPLATE.md` : fill the Summary / Related issue / Changes sections and tick every applicable checklist item. Never open a bare issue or PR that bypasses these templates. When creating a PR with the `gh` CLI, build the PR body from `PULL_REQUEST_TEMPLATE.md` (gh does not apply it automatically).
- **PR progress tracking**: For any chantier tracked by a PR that carries a checklist, comment the progress on the PR at each commit (what changed, why, which checklist items it covers, verification status) AND tick the corresponding checklist items in the PR body as they are completed. This is the standard way of working for all changes.
- **Never edit the generated reference by hand**: everything under `docs/reference/generated/` is rendered from the code's own registries by `python manage.py generate_docs`. After changing a permission, a lifecycle, a dashboard widget, an MCP tool, a REST route, a model or an environment variable, re-run the command and commit its output : `docs.yml` fails the build on a stale page. The generator is deterministic and removes pages it no longer produces.
- **Documentation must survive publication to the wiki**: the GitHub wiki has a flat page namespace (directories have no effect on a page's URL), so every internal link in `docs/` must point at a **file**, never at a directory, and must be relative so the build can rewrite it. Images live in `docs/screenshots/` and are captured at 2560x1440. `python scripts/build_wiki.py --check` validates all of it and runs in CI.
- **A feature change updates its documentation in the same commit**: the specification under `docs/specs/` always, the user guide under `docs/user-guide/` when the interface changes, the SDK page under `docs/sdk/` when an extension point changes, and the generated reference by re-running `generate_docs`.
- **Dependencies are locked, Django stays on its LTS line**: everything installs from `requirements.txt`, the exact, hash-checked set compiled by `pip-compile` from `requirements.in` (the direct dependencies). Add or change a dependency in `requirements.in` (and in `core/dependencies.py`), recompile with the command given in `docs/technical/contributing.md`, commit both. Dependabot proposes the weekly updates (`.github/dependabot.yml`). Django is constrained to the current LTS line (5.2.x; the next is 6.2) and Python to the version shared by the `Dockerfile`, the workflows and `mise.toml` (3.14) : never loosen either as a side effect of another change.
- **Persistent instructions**: When the user asks to "always do something" or to "remember something", add it to this `CLAUDE.md` file so it persists across sessions.
