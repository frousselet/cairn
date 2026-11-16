# Operations

What a Cairn deployment needs from you after it is running.

## Scheduled commands

Five commands keep records in step with the passage of time. Nothing else runs
on a timer, and none of them are triggered by a user action, so if they are not
scheduled the data silently ages instead of failing loudly.

| Command | What it does | Cadence |
| --- | --- | --- |
| `expire_risk_acceptances` | Marks an active risk acceptance `EXPIRED` once `valid_until` has passed, and prints acceptances expiring within `--reminder-days` (30 by default) | Daily |
| `mark_overdue_treatment_plans` | Marks an in-flight treatment plan `OVERDUE` once `target_date` has passed (skips completed, cancelled and already-overdue plans) | Daily |
| `documents_sweep` | Sends the document review reminders (due within 30 days, overdue) and the acknowledgement reminders (7 days before a campaign's due date and the day after it), each once | Daily |
| `controls_sweep` | Sends the control test reminders (due within 14 days once per cycle, overdue once then every 7 days) and recomputes the derived effectiveness of every planned or implemented control | Daily |
| `rebuild_semantic_index` | Refreshes the Ask Cairn requirement embeddings | Daily, only if semantic search is on |

The lifecycle commands, `documents_sweep` and `controls_sweep` accept `--dry-run`.

```cron
# /etc/cron.d/cairn
15 2 * * * cd /opt/cairn && docker compose exec -T web python manage.py expire_risk_acceptances
20 2 * * * cd /opt/cairn && docker compose exec -T web python manage.py mark_overdue_treatment_plans
22 2 * * * cd /opt/cairn && docker compose exec -T web python manage.py documents_sweep
23 2 * * * cd /opt/cairn && docker compose exec -T web python manage.py controls_sweep
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

uvicorn writes an access log to stdout; the application logs to stderr, in
production as under `DEBUG`, one line per record :
`time level logger : message`. In a compose deployment,
`docker compose logs -f web`. `LOG_LEVEL` sets the verbosity.

An unhandled error shows the user the error page and writes its traceback
here, under the `django.request` logger. Start there when someone reports
"Something went wrong on our side".

Two categories are worth routing somewhere durable rather than reading ad hoc :

- **Access events** are in the database, not the log stream, and are visible at
  **Administration -> Access log**. That is the record of who signed in, what
  failed, and who impersonated whom.
- **MCP and API errors** surface as JSON-RPC or HTTP errors. An MCP internal
  error is logged with a stack trace server-side and returned to the client as a
  bare `Internal error`, deliberately, so a tool call never leaks internals to a
  connected assistant.

## Health

`GET /health/` answers `200 {"status": "ok"}` when the process can serve a
request that needs the database, and `503 {"status": "unavailable"}` when it
cannot. It is the endpoint to give a container healthcheck, a load balancer or
an orchestrator probe.

- It needs no session and no cookie, and it is answered before host
  validation : a probe that calls by IP or by `localhost` is not refused by
  `ALLOWED_HOSTS`, nor redirected to the sign-in or the onboarding screen.
- It discloses nothing : no version, no hostname, no error text. The reason of
  a failure is in the log.
- It does not check Redis. The application keeps serving without it (see
  [architecture.md](architecture.md#redis-is-not-optional)), so a Redis outage
  must not take the instance out of a load balancer.

The image declares it as its `HEALTHCHECK`, so `docker ps` shows the container
as `healthy` once migrations have run and the server answers. The compose file
also gates `web` on the `db` and `redis` healthchecks.

## The account the container runs as

No web worker runs as root. The container starts as root for one job : handing
`/app/media` and `/app/staticfiles` to the unprivileged `cairn` account (uid
1000) when they are still root-owned, which is the case of a media volume
written by an image older than this arrangement. It then restarts its
entrypoint as that account and never goes back.

- With the development bind-mount (`.:/app`), the account is the owner of the
  checkout on the host, so generated files stay yours.
- Started with `user:` (or an orchestrator's `runAsUser`), the container runs
  as given and skips the hand-over. That account must be able to write the
  media volume.

## Error pages

Outside `DEBUG`, a missing page, a refused permission, an expired form (CSRF)
and an unhandled error each render a page in the product's own design, in the
reader's language, with a way back. They are self-contained (`templates/errors/`
: no query, no static file to resolve), so the 500 page still renders when the
database is what failed.

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
| `Cache unreachable (... failed ...). Serving without it.` in the log, once a minute | Redis is down or unreachable. The application keeps serving from the database; the About modal re-asks GitHub, the Trust Center rate limiter lets requests through and the scheduler locks are not taken until it is back |
| A lifecycle edited in the administration seems to apply on some requests only | Expected for up to `LIFECYCLE_CACHE_TTL` seconds (5 by default) : each worker re-reads the definitions at that pace |
