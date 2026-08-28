# Architecture

Cairn is a single Django application, server-rendered, with a REST API and an
MCP server over the same models and the same permission checks. There is no
separate front-end build : no bundler, no npm, no compile step. That is a
deliberate constraint, not an accident of age, and it is what makes the platform
deployable as one container behind one reverse proxy.

## Stack

| Layer | Choice | Why it is that one |
| --- | --- | --- |
| Language | Python 3.12 | The version CI pins and the image ships |
| Framework | Django 5.2 LTS | Long-term support matters more than novelty for a platform that outlives audits |
| Database | PostgreSQL 16 | JSON fields, real constraints, and a migration story |
| Async | Django Channels 4 over ASGI | WebSocket push for the live dashboard |
| Message layer / cache | Redis | Both the Channels layer and the shared cache; see below |
| API | Django REST Framework | Plus `django-filter` and SimpleJWT |
| History | `django-simple-history` | Every model change recorded, not derived |
| Front end | Bootstrap 5.3 + HTMX + Apache ECharts | Server-rendered HTML, HTMX for partial swaps, ECharts for the graphs |
| Documents | WeasyPrint, `python-docx`, `python-pptx`, `openpyxl` | PDF, DOCX, PPTX and Excel generation and import |
| Auth | Session, JWT, OAuth 2.0, WebAuthn (`fido2`) | Four callers : browser, script, MCP client, passkey |
| Server | uvicorn (ASGI), WhiteNoise for static | Three workers in the shipped image |

`requirements.txt` is the authoritative list of Python distributions, and the
front-end libraries are pinned by URL in the templates. `core/dependencies.py`
describes both in one registry, with the official repository of each component :
it is what the About dialog, `GET /api/v1/dependencies` and the
`list_dependencies` MCP tool answer from. Python versions are resolved from the
installed metadata rather than declared, and `core/tests/test_dependencies.py`
fails if the registry drifts from `requirements.txt` or from the versions the
templates actually load.

## Redis is not optional

It carries two distinct jobs, and both are correctness requirements rather than
optimisations.

The **Channels layer** uses `RedisPubSubChannelLayer` (push) rather than the
historical `RedisChannelLayer` (which polls `BLPOP` and raised a timeout every
few seconds when nothing was published). The trade-off is that messages are not
queued for a consumer that drops briefly, which is acceptable here because the
broadcasts are dashboard refresh hints, not durable work items.

The **cache** is Redis-backed because the shipped image runs three uvicorn
workers and several code paths coordinate *across* those processes through it :
the first-run onboarding runner (one migration and seed across the fleet, not
three), the semantic index rebuild lock, the SPOF scheduler's single-runner gate
and the Trust Center rate limiter. Django's default per-process `LocMemCache`
would make each of those locks local to one worker and silently ineffective.

The test settings override both with in-memory equivalents, because the suite is
single-process and must not need a live Redis.

## Applications

| App | Responsibility |
| --- | --- |
| `core` | Settings, root URLs, the lifecycle engine, the dashboard registry, shared mixins, history and workflow views, imports, onboarding |
| `accounts` | The custom `User` (email login, UUID keys), groups, the permission registry, passkeys, access logging, notifications |
| `context` | Organisational context : scopes, sites, issues, stakeholders, objectives, SWOT, roles, activities, indicators, tags. Also home to `BaseModel` |
| `assets` | Essential and support assets, valuations, dependencies, SPOF detection, suppliers, contracts, certificates |
| `compliance` | Frameworks, sections, requirements, assessments, findings, the nonconformity register, action plans, inter-framework mappings, Excel import |
| `risks` | Risk assessments and criteria, risks, threats, vulnerabilities, ISO 27005 analysis, the full EBIOS RM workshop set, treatment plans, acceptance |
| `incidents` | Security events, incidents, evidence and chain of custody, notification obligations and filings, personal data breaches, post-incident reviews |
| `reports` | Report generation (PDF / DOCX / PPTX) and the ISO 27001 management review |
| `trust_center` | The public, curated Trust Center and its request workflow |
| `assistant` | Ask Cairn : the optional LLM question mode, providers, semantic search |
| `mcp` | The MCP server, its tool registry and OAuth 2.0 authorisation |
| `helpers` | Contextual help banners |

The full model inventory, with each model's reference prefix, lifecycle and
tenancy, is in [reference/generated/models.md](../reference/generated/models.md).

## Per-app layout

Every domain app follows the same shape, which is what makes a new module
predictable rather than a matter of taste.

```
<app>/
├── models/          one file per model, re-exported from __init__.py
├── constants.py     choice tuples and enums; the single source for status codes
├── lifecycles.py    the app's registered lifecycles
├── forms.py         model forms
├── views.py         class-based views
├── urls.py          web UI routes, mounted at /<app>/
├── api/             DRF serializers, viewsets and routes, mounted at /api/v1/<app>/
├── templates/<app>/ the app's templates
└── tests/           factories.py plus test_*.py
```

## How a request is served

```
                 ┌─────────────────────────────────────────────┐
   browser ─────▶│ uvicorn (ASGI, 3 workers)                   │
   script  ─────▶│  └─ WhiteNoise ──▶ /static/                 │
   MCP     ─────▶│  └─ Django                                  │
                 │      ├─ middleware chain                    │
                 │      │   security, sessions, locale,        │
                 │      │   Trust Center host isolation, CSRF, │
                 │      │   auth, onboarding, user language,   │
                 │      │   impersonation, HTMX, history       │
                 │      ├─ URL resolver                        │
                 │      │   /<app>/       web views            │
                 │      │   /api/v1/      DRF viewsets         │
                 │      │   /api/v1/mcp   JSON-RPC tools       │
                 │      │   /trust/       public Trust Center  │
                 │      │   /ws/          Channels consumers   │
                 │      └─ view ──▶ model ──▶ PostgreSQL       │
                 └─────────────────────────────────────────────┘
                                    │
                            Redis (cache + pub/sub)
```

Three middlewares deserve a note because they change what a request can reach.
`TrustCenterHostMiddleware` isolates the public Trust Center when it is served on
its own domain : on that host, the application, the admin and the internal API
return 404 rather than merely refusing. `OnboardingMiddleware` redirects a fresh
database to the first-run screen. `ImpersonationMiddleware` swaps the effective
user for an administrator acting as someone else, and the substitution is
recorded in the access log at both ends.

## Cross-cutting patterns

These are the ones you inherit by subclassing rather than by remembering.

**`BaseModel`** (`context/models/base.py`) gives every domain model a UUID
primary key, `created_at` / `updated_at`, `created_by`, a `workflow_state`
running a registered lifecycle, a version counter and tags. **`ScopedModel`**
adds the `scopes` many-to-many that drives tenancy. **`ReferenceGeneratorMixin`**
issues the sequential business reference (`RISK-1`, `ASST-2`) from a
four-character `REFERENCE_PREFIX`.

**Lifecycles** (`core/lifecycle.py`) are the governance backbone. A lifecycle is
ordered steps plus transitions; each step carries `counts_in_reports`,
`linkable` and `deletable`, and the rest of the platform reads those flags
through `reportable()`, `linkable()` and `deletable_states()` instead of
hardcoding a status value. This is why adding a step to a lifecycle does not
require touching the dashboards, the pickers or the deletion logic. The contract
is [governance/workflow.md](../specs/governance/workflow.md), the engine
internals are [governance/lifecycle.md](../specs/governance/lifecycle.md), and
the shipped lifecycles are listed in
[reference/generated/lifecycles.md](../reference/generated/lifecycles.md).

**Permissions** are flat codenames shaped `module.feature.action`, declared once
in `accounts/constants.py` and created by a data migration. Django's per-model
`add`/`change`/`delete` permissions are not used. Every surface, web, REST and
MCP alike, gates on the same codename.

**Tenancy** is scope-based. `ScopeFilterMixin` filters a queryset to the scopes
the user is assigned; child entities inherit their parent's perimeter through a
declared scope path so a timeline entry is never reachable when its incident is
not.

**History** is `django-simple-history` on every domain model, exposed through a
generic history view rather than a per-model one.

**View mixins** (`core/mixins.py`, `accounts/mixins.py`) carry the rest :
`SortableListMixin` (server-side sorting persisted per user in
`User.table_preferences`), `CreatedByMixin`, `LifecycleStepperMixin`.

## Front end

Server-rendered Django templates with Bootstrap 5.3. HTMX handles partial
updates and boosted navigation; Apache ECharts draws the graphs. Dark mode
follows the OS preference unless the user overrides it, and every component is
expected to render correctly in both themes. Icons are Bootstrap Icons,
exclusively. The visual system is specified in
[brand-guidelines.md](../brand/brand-guidelines.md), and `/styleguide/` renders
it live in a running instance.

### Every library is served from the instance

No page ever loads a script, a stylesheet or a font from a CDN. Each front-end
library is declared in `core/dependencies.py` with the exact files it needs and
their Subresource-Integrity digests, and `manage.py vendor_assets` mirrors those
files into `static/vendor/`, where `collectstatic` and WhiteNoise pick them up
like any other static file. Templates reference them through `{% static %}` and
carry no version of their own, so the registry cannot drift from what a browser
actually receives.

That buys three things : an instance on an isolated network works; no third
party learns who browses a compliance platform; and the interface cannot break
because someone else's infrastructure did. The mirror is never committed - the
Docker build populates it (`RUN python manage.py vendor_assets`) and a direct
install fetches whatever is missing on its first launch. A download whose
content does not match its declared digest is refused rather than served.

The one outbound call the interface can make is the About modal asking GitHub
whether a newer release exists, and only when someone opens that modal. See
[configuration.md](configuration.md) for `UPDATE_CHECK_ENABLED` and
`VENDOR_ASSETS_AUTO_DOWNLOAD`.

## What is deliberately absent

No JavaScript build step, no SPA, no GraphQL, no per-model Django admin as the
primary interface, no separate worker queue. Each of those would buy something,
and each would cost the property that makes this deployable and auditable : one
process, one language, one place where a permission is checked.
