# First-run onboarding

## Purpose

Give a brand-new Cairn instance a guided, in-app bootstrap instead of dropping a
fresh operator on the login screen with no account. While the instance is
un-initialised, the onboarding screen applies any pending database migrations
(with a live progress bar), then lets the operator either create the first
super-admin or load the demo dataset.

## Trigger and gating

The **migration** screen shows whenever the schema has pending migrations (a
fresh database *or* an upgrade of an initialised one). The **choices** (create
admin / seed) are **first-run only** (no users yet). Detection lives in
`core/onboarding/state.py`:

- `is_first_run()` - `True` while there are no users; a `DatabaseError` (missing
  table) is also treated as a first run so the screen can render before any table
  exists. Cached once a user is observed (only ever flips to "initialised").
- `schema_ready()` - `True` when there are no pending migrations. Cached once
  confirmed (a process cannot gain migrations without a restart), so the common
  up-to-date path costs nothing after the first request.
- `migration_status()` - read-only migration state via Django's
  `MigrationExecutor` (`applied`, `total`, `pending`, `up_to_date`).

`core/middleware.py` -> `OnboardingMiddleware` redirects every request (except
onboarding itself and static / i18n assets) to `onboarding:landing` while a job
is running, while migrations are pending (`not schema_ready()`), or during a first
run. Once the instance is initialised *and* the schema is up to date, the
onboarding screens are hidden (the `complete` and `progress.json` paths stay
reachable). It can be disabled with `settings.ONBOARDING_REDIRECT_ENABLED = False`
(the test settings do this so the wider suite is unaffected).

## Flow

Standalone, login-styled pages (they render before authentication, so they do not
extend the app base template). Defined in `core/onboarding/views.py`, templated
under `templates/onboarding/`:

1. **Landing** (`onboarding:landing`)
   - If the schema has **pending migrations**, it starts them automatically
     (`start_migrations()`, idempotent) and renders the full-screen progress bar
     (step counter + current migration name). No button: the operator just
     watches the migrations apply. This covers both a fresh database (heading
     "Setting up the database", which then shows the choices) and an upgrade of an
     already-initialised instance (heading "Updating the database", which returns
     to the app when done). The progress bar surfaces an error if the backend
     connection drops (repeated poll failures).
   - Once the schema is ready, a first run shows the two initialisation choices.
2. **Start from scratch** (`onboarding:scratch`) - a two-step wizard on a single
   page / single `<form>`: **step 1 configures the company** (`CompanySettingsForm`
   - name, application name, assistant name, accent colour, logo, address, all
   optional) and **step 2 creates the administrator** (`FirstAdminForm`). The
   side rail carries the vertical stepper and the navigation buttons. The whole
   submit creates the super-admin **and** persists the company settings in one
   `transaction.atomic()` block, then signs the admin in and redirects to the
   dashboard. **Nothing is written to the database until the administrator is
   created**: the company step is held in the browser (`sessionStorage`, cleared
   on submit, passwords never stored) and everything is sent in a single request.
   A server-side validation error re-opens the wizard on the offending step
   (company first, then admin).
3. **Start with sample data** (`onboarding:seed`) - starts the demo seed on a
   background thread and renders the progress bar. The seed
   (`scripts/seed_demo_data.py`) reports each phase through an injected
   `_phase()`/`SEED_PROGRESS` callback; the runner derives the total step count
   from the number of phase markers in the script.
4. **Complete** (`onboarding:complete`) - after the seed finishes, auto-logs-in as
   the seeded admin and redirects to the dashboard.

## Progress transport: polling, not WebSockets

Both background jobs (migrations and seed) publish progress to the **shared
cache** (Redis in production, see `settings.CACHES`) in `core/onboarding/runner.py`,
exposed as JSON by `onboarding:progress` (`progress.json`). The progress bar polls
that endpoint.

Polling is deliberate. On a fresh database the session and auth tables do not
exist yet, so the Channels auth stack (and DB-backed sessions) cannot run during
the **migration** phase - a WebSocket would fail before the very tables it needs
are created. The JSON poll touches neither the database nor the session, so it
works before any table exists. Using one mechanism for both phases keeps the
client simple.

## Concurrency: one migration across all workers

Production runs several uvicorn workers (see the Dockerfile `CMD`). Every web
request - including the onboarding landing view's automatic `start_migrations()`
call - can land on a different worker process. The runner therefore coordinates
through the **shared cache**, not a per-process flag:

- `start_migrations()` / `start_seed()` acquire a cross-worker lock with an atomic
  `cache.add()` (Redis SET-NX). Exactly one worker wins and runs the job on a
  background thread; every other worker (and any second request) gets `False` and
  simply watches the shared progress. Without this, each worker would believe no
  job was running and launch its **own** migration - several processes applying
  the same DDL at once, which fails with duplicate-column / duplicate-type errors
  and makes the bar jump backwards.
- `is_running()` reads that shared lock, so `OnboardingMiddleware` and the
  background schedulers (SPOF detection, semantic-index rebuild) all agree on
  whether a job is in flight regardless of which worker they run in.
- The lock carries a TTL refreshed by a heartbeat on each migration / seed step,
  so a worker that dies mid-job frees the instance within a few minutes instead of
  wedging onboarding forever.

A per-process `LocMemCache` (Django's default when no `CACHES` is configured)
would make every one of these locks local to a single worker and silently
ineffective, so a shared cache backend is a correctness requirement here, not an
optimisation.

Note: the migration runner applies migrations with ``MigrationExecutor`` (for the
per-migration progress callback) and then emits the ``post_migrate`` signal
itself, because - unlike the ``migrate`` management command -
``MigrationExecutor.migrate()`` does not. Without it, Django ``ContentType`` rows
and built-in permissions are never created and the demo seed fails.

## Startup sequencing

So that migration progress is visible in the browser, the web server must start
**before** migrations are applied on a fresh database:

- Docker `entrypoint.sh` only auto-migrates when the instance is already
  initialised (users exist, i.e. an upgrade) or when `DJANGO_SUPERUSER_*` env
  vars provision an admin non-interactively. An empty database starts the server
  and lets onboarding apply the migrations.
- The VS Code `stack: bootstrap` preLaunchTask only compiles translation
  catalogs (no migrate/seed), so F5 on an empty `db.sqlite3` lands on onboarding.

## Security

- Every onboarding action (create admin, start seed) re-checks `is_first_run()`
  server-side, so the bootstrap actions are impossible once any user exists -
  independent of the middleware.
- The whole seed runs in a single `transaction.atomic()`; on failure it rolls
  back, leaving no users, and the completion view reports an error instead of
  signing anyone in.
- Auto-login on completion is gated by a per-session flag set only when that same
  browser started the seed, and is consumed once. No password is ever exposed;
  correctness is decided by database state (a superuser exists), not by the
  progress animation.

## API / MCP

Intentionally **none**. Onboarding is a pre-authentication, one-time bootstrap;
exposing "create the first admin" / "seed the database" / "auto-login" on the
authenticated REST and MCP surfaces would be contradictory and a security risk.
This is the one documented exception to the project-wide "every feature ships MCP
tools and API endpoints" rule.
