# Operations

What a Cairn deployment needs from you after it is running.

## Scheduled commands

Three commands keep records in step with the passage of time. Nothing else runs
on a timer, and none of them are triggered by a user action, so if they are not
scheduled the data silently ages instead of failing loudly.

| Command | What it does | Cadence |
| --- | --- | --- |
| `expire_risk_acceptances` | Marks an active risk acceptance `EXPIRED` once `valid_until` has passed, and prints acceptances expiring within `--reminder-days` (30 by default) | Daily |
| `mark_overdue_treatment_plans` | Marks an in-flight treatment plan `OVERDUE` once `target_date` has passed (skips completed, cancelled and already-overdue plans) | Daily |
| `rebuild_semantic_index` | Refreshes the Ask Cairn requirement embeddings | Daily, only if semantic search is on |

Both lifecycle commands accept `--dry-run`.

```cron
# /etc/cron.d/cairn
15 2 * * * cd /opt/cairn && docker compose exec -T web python manage.py expire_risk_acceptances
20 2 * * * cd /opt/cairn && docker compose exec -T web python manage.py mark_overdue_treatment_plans
25 2 * * * cd /opt/cairn && docker compose exec -T web python manage.py rebuild_semantic_index
```

`rebuild_semantic_index` is idempotent : it re-embeds only changed requirements
and prunes deleted ones, so a daily run is cheap. The index is also refreshed at
startup, pruned immediately when a requirement is deleted, and can be forced
from **Administration -> Semantic index**. The cron entry is the self-healing
backstop rather than the primary mechanism.

The complete command list is in
[reference/generated/management-commands.md](../reference/generated/management-commands.md).

## Backups

Two things must be captured, and captured **together**.

1. **PostgreSQL.** It holds the records, the history tables and the access log.
2. **The media directory** (`MEDIA_ROOT`). It holds incident evidence artefacts,
   proof-of-filing documents, contract and certificate PDFs, and Trust Center
   documents.

A restore with one and not the other is not a restore. An evidence register
whose artefacts are missing is worse than an empty one, because the chain of
custody still claims they exist.

```bash
docker compose exec -T db pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" | gzip > cairn-$(date +%F).sql.gz
tar czf cairn-media-$(date +%F).tar.gz media/
```

Test the restore. An untested backup is a hypothesis.

## Upgrading

```bash
docker compose pull
docker compose up -d
docker compose exec web python manage.py migrate
```

Migrations are forward-only in practice : several are data migrations that seed
permissions, system groups, lifecycles and risk criteria, and they reconcile
rather than replace, so re-running them is safe. Take the database backup first
anyway.

The first-run onboarding runner coordinates through the shared cache, so
migration runs once across the worker fleet rather than three times.

## Logs

uvicorn writes an access log to stdout; Django's logging goes to the same place.
In a compose deployment, `docker compose logs -f web`.

Two categories are worth routing somewhere durable rather than reading ad hoc :

- **Access events** are in the database, not the log stream, and are visible at
  **Administration -> Access log**. That is the record of who signed in, what
  failed, and who impersonated whom.
- **MCP and API errors** surface as JSON-RPC or HTTP errors. An MCP internal
  error is logged with a stack trace server-side and returned to the client as a
  bare `Internal error`, deliberately, so a tool call never leaks internals to a
  connected assistant.

## Health

There is no dedicated health endpoint. `GET /accounts/login/` returning 200 is a
sufficient liveness check for a reverse proxy; it exercises the ASGI stack, the
template layer and the session middleware without touching a protected view.

Readiness is `python manage.py check` plus a database connection. The compose
file already gates `web` on the `db` and `redis` healthchecks.

## When something is wrong

| Symptom | Likely cause |
| --- | --- |
| Every page redirects to the onboarding screen | The database has no migrations applied, or no user exists |
| Sessions drop immediately after sign-in | `SESSION_COOKIE_SECURE=True` without HTTPS in front |
| CSRF failures behind a proxy | `CSRF_TRUSTED_ORIGINS` missing the scheme, or the proxy not setting `X-Forwarded-Proto` |
| Passkey registration refused by the browser | `WEBAUTHN_RP_ID` does not match the host the user sees |
| The interface is English despite a French preference | `compilemessages` never ran, so there are no `.mo` files |
| Static files 404 under `DEBUG=False` | `collectstatic` never ran |
| The live dashboard never updates | Redis unreachable, so the Channels layer has no transport |
| Widgets show stale counts across reloads | The cache fell back to per-process memory; check `REDIS_HOST` |
