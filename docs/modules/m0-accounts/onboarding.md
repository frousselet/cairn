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
2. **Start from scratch** (`onboarding:scratch`) - `FirstAdminForm` creates the
   first `create_superuser`, signs them in, and redirects to the dashboard.
3. **Start with sample data** (`onboarding:seed`) - starts the demo seed on a
   background thread and renders the progress bar. The seed
   (`scripts/seed_demo_data.py`) reports each phase through an injected
   `_phase()`/`SEED_PROGRESS` callback; the runner derives the total step count
   from the number of phase markers in the script.
4. **Complete** (`onboarding:complete`) - after the seed finishes, auto-logs-in as
   the seeded admin and redirects to the dashboard.

## Progress transport: polling, not WebSockets

Both background jobs (migrations and seed) publish progress to a process-global
store in `core/onboarding/runner.py`, exposed as JSON by `onboarding:progress`
(`progress.json`). The progress bar polls that endpoint.

Polling is deliberate. On a fresh database the session and auth tables do not
exist yet, so the Channels auth stack (and DB-backed sessions) cannot run during
the **migration** phase - a WebSocket would fail before the very tables it needs
are created. The JSON poll touches neither the database nor the session, so it
works before any table exists. Using one mechanism for both phases keeps the
client simple.

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
