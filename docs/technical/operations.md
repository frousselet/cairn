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
from **Administration -> Ask Cairn** (the *Semantic index* view). The cron entry is the self-healing
backstop rather than the primary mechanism.

The complete command list is in
[reference/generated/management-commands.md](../reference/generated/management-commands.md).

## Backups

Two things must be captured, and captured **together**.

1. **The database.** It holds the records, the history tables and the access log.
2. **The media directory** (`MEDIA_ROOT`). It holds incident evidence artefacts,
   proof-of-filing documents and control evidence files.

A restore with one and not the other is not a restore. An evidence register
whose artefacts are missing is worse than an empty one, because the chain of
custody still claims they exist.

### Taking one

```bash
docker compose exec web python manage.py backup
```

writes one archive into `BACKUP_DIR` (`/app/backups` in the image), holding
both :

```text
cairn-backup-20261117-081333Z.tar
    manifest.json      format, Cairn version, engine and server version,
                       applied migrations, size and SHA-256 of every member
    database.pgdump    pg_dump, custom format, one consistent snapshot
    media/...          every file under MEDIA_ROOT
```

The command reads the archive back and checks every checksum before it reports
success, so a backup that cannot be read is known on the day it is made. The
application keeps running : `pg_dump` works on a snapshot.

Mount a volume or a host directory on `BACKUP_DIR`. An archive kept inside the
container goes with the container, and one kept on the disk of the database
goes with the disk : copy it elsewhere.

```yaml
services:
  web:
    environment:
      BACKUP_DIR: /backups
    volumes:
      - media_data:/app/media
      - /srv/cairn/backups:/backups
```

Schedule it from the host, and let it rotate :

```cron
# every night at 02:30, keeping the last fourteen
30 2 * * *  cd /srv/cairn && docker compose exec -T web python manage.py backup --keep 14
```

`--keep N` deletes all but the `N` most recent archives of the directory once
the new one is written and verified. `--output DIR` writes somewhere else for
one run.

The archive holds everything : password hashes, sessions, API tokens, every
record. It is created readable by its owner only; store its copies encrypted
and treat them as the instance itself.

### Restoring

```bash
docker compose exec web python manage.py restore /backups/cairn-backup-20261117-081333Z.tar
```

puts the instance back in the exact state of the archive. In order :

1. Every member is checked against the manifest. A damaged, incomplete or
   altered archive is refused before anything is touched.
2. An archive made by a **newer** release than the one running is refused : its
   schema has tables and columns this code does not know.
3. The current state is saved beside the archive as
   `cairn-before-restore-<time>.tar`, so a restore of the wrong archive can be
   undone. (`--no-safety-backup` skips it, for an empty instance.)
4. The database dump is loaded into a **new database**, which then takes the
   name of the current one. Until that swap the current database is not
   touched : a dump that fails to load costs nothing. The sessions the
   application holds are closed for the swap; it reconnects on its next request.
5. The media directory is replaced by the archive's files.

`--check` stops after steps 1 and 2 : it says whether the archive is sound and
restorable here, and changes nothing. `--yes` skips the confirmation, for a
scripted restore.

The restore is exact : a record, a table or a file created since the backup is
gone afterwards. If the archive is older than the release running, the command
ends by saying how many migrations it is behind : run `python manage.py
migrate` next. Safety backups are not rotated; delete them once the restore is
confirmed.

Two requirements on PostgreSQL :

- The database role must own the database and hold `CREATEDB` (it creates the
  database the archive is loaded into). The role a compose deployment creates
  does. Otherwise the command stops with the statement to run.
- The client tools (`pg_dump`, `pg_restore`, `psql`) must be of the **same
  major version** as the server. The image ships the tools of the server its
  compose file runs (`postgres:18`). An instance still on another major either
  builds the image with `--build-arg POSTGRES_MAJOR=16`, or backs up by hand
  from the database container, which always has matching tools :

  ```bash
  docker compose exec -T db pg_dump -U "$POSTGRES_USER" -Fc "$POSTGRES_DB" > cairn-$(date +%F).pgdump
  docker compose exec -T web tar czf - -C /app media > cairn-media-$(date +%F).tar.gz
  ```

### Testing the restore

An untested backup is a hypothesis. Restore last night's archive on a second
instance (another compose project, its own volumes) and open it : that is the
only proof it works with *your* data and *your* storage. `restore --check` on
the production host verifies the archive without touching anything, and is
cheap enough to run after every backup.

The mechanism itself is tested on every change : the suite backs up a
throwaway instance, damages it, restores it and compares; the PostgreSQL job
does the same on a real server, including a dump that fails half-way and a
restore while the application is connected.

## Upgrading

```bash
docker compose pull
docker compose up -d
docker compose exec web python manage.py migrate
```

Migrations are forward-only in practice : several are data migrations that seed
permissions, system groups, lifecycles and risk criteria, and they reconcile
rather than replace, so re-running them is safe. Take a backup first anyway
(`python manage.py backup`) : it is the way back if the new release misbehaves,
since an archive can be restored on the release that made it or a later one.

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
| The installation screen says *The installation is not progressing* | No job is running behind it and three automatic restarts did not start one. Read the server log : the migration error, if any, is there. Under compose, check that `REDIS_HOST` and `POSTGRES_HOST` name the services (`redis`, `db`), not `127.0.0.1` |
| Widgets show stale counts across reloads | The cache fell back to per-process memory; check `REDIS_HOST` |
| `Cache unreachable (... failed ...). Serving without it.` in the log, once a minute | Redis is down or unreachable. The application keeps serving from the database; the About modal re-asks GitHub, the Trust Center rate limiter lets requests through, and the jobs that take a lock (installation, single point of failure detection, index rebuild) run once per worker instead of once for all |
| A lifecycle edited in the administration seems to apply on some requests only | Expected for up to `LIFECYCLE_CACHE_TTL` seconds (5 by default) : each worker re-reads the definitions at that pace |
