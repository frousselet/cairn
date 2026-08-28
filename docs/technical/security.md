# Security

Cairn holds an organisation's risk register, its audit findings and its incident
evidence. The threat model is therefore not only "an outsider gets in" but also
"an insider sees a scope they were not assigned" and "a record changed and
nobody can prove who changed it".

This page describes what the platform enforces and, at the end, what it leaves
to the operator. The two lists are separate on purpose.

## Authentication

Four ways in, all landing on the same user record.

| Method | Used by | Notes |
| --- | --- | --- |
| Email + password | The web interface | There is no username; the email is the identifier |
| Passkey (WebAuthn) | The web interface | `fido2`, phishing-resistant, usable as the sole factor |
| JWT | Scripts and API clients | 30-minute access token, 7-day refresh, rotation on, blacklist after rotation |
| OAuth 2.0 bearer | MCP clients | Authorisation-code flow; see [mcp-server.md](../reference/mcp-server.md) |

Passwords go through five validators : Django's similarity, minimum length
**12**, common-password and numeric-only checks, plus a project complexity
validator. After **5** failed attempts an account is locked for **15** minutes.

An invited user is created with an unusable password and receives a single-use
activation link. No endpoint accepts a password on someone else's behalf.

## Authorisation

Permissions are flat codenames shaped `module.feature.action`, declared once in
`accounts/constants.py` and created by a data migration. Django's per-model
`add`/`change`/`delete` permissions are **not** used, so there is exactly one
place a permission can come from.

The same codename gates all three surfaces : the web view, the REST endpoint and
the MCP tool. This matters more than it sounds. A permission model that is
enforced in the interface and re-derived in the API is a permission model with
two answers, and an auditor will find the disagreement before you do.

The full list is in
[reference/generated/permissions.md](../reference/generated/permissions.md).
Six system groups ship with the platform and are kept in sync by the same
migration, so a newly declared permission lands in the right groups without
anyone editing a group by hand.

## Tenancy

Scopes are the tenancy axis. A user is assigned scopes; `ScopeFilterMixin`
filters querysets to them, and the same filtering applies on the REST API and
the MCP layer.

Child entities do not carry their own scopes : they inherit the parent's
perimeter through a declared scope path. An incident's timeline entry is
unreachable when its incident is out of perimeter, and it is unreachable on
every surface, including the generic history and workflow endpoints. Shared
catalogues (reporting authorities, obligation templates) are deliberately not
scope-filtered, because they are reference data rather than records.

A superuser bypasses scope filtering. That is the intended escape hatch, and it
is why superuser is not a role you hand out.

## Lifecycle as a control

Governance is not advisory here. A record's step decides whether it counts in
reports (`counts_in_reports`), whether other objects may link to it (`linkable`)
and whether it may be deleted (`deletable`). Deletion is only offered from a
deletable step, which is how a validated risk cannot quietly disappear.

Transitions are the only way a state changes. `workflow_state` is read-only on
the API : there is no `PATCH` that moves a record, because the transition
endpoint is where the permission gate, the mandatory comment and the recorded
lifecycle event live. Three incident registers go further and are append-only at
the router level : `PUT`, `PATCH` and `DELETE` generate no route at all and
answer `405`. Correcting one means appending a correction, not rewriting
history.

## Audit trail

Every domain model carries `django-simple-history`, so every write is a row with
an author and a timestamp, and every object carries a version counter.

Authentication and account events are recorded separately in the access log :
successful and failed logins, logouts, token refreshes, password changes,
lockouts, passkey registration and use, invitations, activations, and
impersonation start and stop. Impersonation is recorded at **both** ends, so
"the administrator was acting as this user" is a fact in the log rather than an
inference.

`GET /api/v1/incidents/<ledger>/<uuid>/history/` is the tamper-detection surface
on the append-only registers : a row whose trail shows more writes than the
design allows was altered outside the supported paths.

## Files

Evidence artefacts, filing proofs and Trust Center documents never appear in a
payload and are never served from a guessable media URL. They stream through
dedicated download endpoints resolved via the scoped queryset and
permission-checked, and gated Trust Center links are signed with a lifetime
(`TRUST_CENTER_DOWNLOAD_TTL`, seven days by default).

Evidence artefacts are hashed on acquisition and can be re-measured on demand,
returning `match`, `mismatch` or `not_verifiable`.

## Front-end supply chain

No page loads a script, a stylesheet or a font from a third party. Every
front-end library is declared in `core/dependencies.py` with its exact files and
their Subresource-Integrity digests, mirrored into `static/vendor/` and served
from this instance. A download whose content does not match its digest is
refused rather than written, so a compromised mirror cannot reach a browser, and
a test fails the build if any template reintroduces a CDN reference.

For an audit this matters twice over : the code a user's browser executes is
fixed at build time and verifiable, and no third party receives a request that
would tell them who consults a compliance platform and when.

## Public exposure

The Trust Center is the only surface meant to be public, and it is a curation
layer : nothing appears there unless someone explicitly published it. When
`TRUST_CENTER_HOST` is set, that hostname serves the Trust Center and nothing
else, with the application, the admin and the internal API returning 404 rather
than a redirect that would confirm they exist.

Public read endpoints are throttled to 120 requests per hour per anonymous
client. The authenticated application is not throttled.

## Ask Cairn

The assistant is off by default because enabling it sends data to a third party.
When on, it does not widen access : the routing model chooses among read-only
tools, and each of those tools runs the caller's permission and scope checks.
An answer cites real records the caller was already allowed to read. Choosing
the `ollama` provider keeps everything on your own infrastructure.

## What the operator still has to do

The platform cannot do these for you, and none of them are on by default because
turning them on blindly breaks an HTTP-only deployment.

1. **Serve over HTTPS and turn on the hardening flags** : `SESSION_COOKIE_SECURE`,
   `CSRF_COOKIE_SECURE`, `SECURE_SSL_REDIRECT`, then HSTS. The order and the
   HSTS caveat are in [configuration.md](configuration.md#https-hardening).
2. **Set a real `SECRET_KEY`** and keep it out of the image.
3. **Set `DEBUG=False`** and a specific `ALLOWED_HOSTS`.
4. **Run `python manage.py check --deploy`** and read what it says.
5. **Back up PostgreSQL and the media directory together.** The history tables
   are in the database, the evidence artefacts are on disk, and a restore that
   has one without the other is not a restore. See [operations.md](operations.md).
6. **Review the group assignments.** The default groups are a starting point;
   who is in them is your decision and your audit finding.

## Reporting a vulnerability

Open a private security advisory on the
[GitHub repository](https://github.com/frousselet/cairn/security/advisories)
rather than a public issue.
