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
| OAuth 2.0 bearer | MCP clients | Authorisation-code flow with PKCE, or client credentials. The token acts as the user who consented, expires after `OAUTH_ACCESS_TOKEN_LIFETIME_DAYS` days and is only sent to a registered address; see [mcp-server.md](../reference/mcp-server.md#authentication) |

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

Scopes are the tenancy axis. A permission says what a user may do; the scopes
of their groups say on which records. Both are checked, on every surface.

Child entities do not carry their own scopes : they inherit the parent's
perimeter through a path **declared on the model** (`scope_parent_lookup`, with
`scope_parent_alternates` for a row filed under one of several parents and
`scope_parent_optional` when the parent is optional). `core/scoping.py` resolves
it for every surface at once. An incident's timeline entry, a risk, a SWOT item
or a supplier contact is unreachable when its parent is out of perimeter, and it
is unreachable everywhere, including the generic history and workflow
endpoints. Shared catalogues (reporting authorities, obligation templates) are
deliberately not scope-filtered, because they are reference data rather than
records; the Trust Center is one publication for the whole instance.

The path is declared on the model and nowhere else. A view that repeats it
(`scope_parent_lookup = "assessment__scopes"` on a list of findings) overrides
nothing : the whole declaration of the model applies, its alternate parents
included. A site is reached through the scopes it is filed under and through
those that include it (`Scope.included_sites`).

| A record is reached through | What checks the scopes |
| --- | --- |
| A list | `ScopeFilterMixin` (web : every list view of a model with a path to the scopes), `ScopeFilterAPIMixin` (REST), `_reach(user, Model)` (MCP) |
| A detail, update or delete view | `PermissionRequiredMixin.get_object` : every generic single-record view, whether or not it also carries `ScopeFilterMixin` |
| An identifier taken from the request by any other view (a transition, a comment, an export, a row added under a parent) | `core.scoping.get_scoped_object_or_404(user, Model, ...)`, or `get_scoped_object_or_none` for an optional lookup |
| A selection of identifiers (a bulk action, the records a report is generated from) | `core.scoping.scoped_queryset(user, queryset)`, `narrow_scope_ids(user, asked)` for a set of scopes |
| A REST resource nested under a parent | `scope_parent = (Model, "url_kwarg")` on the viewset : the parent is fetched within the scopes before any handler runs |
| An identifier given to an MCP tool | `_fetch(user, Model, pk=...)` : a tool never queries `Model.objects` on its own, and no registration can switch the scopes off |
| A relation : a record chosen in a form, or named in the body of a request, to be linked to another | `core.scoping.selectable(user, queryset)` : `restrict_form_relations` (every generic form view through `PermissionRequiredMixin.get_form`, every form built on `ScopedFormMixin`), `restrict_serializer_relations` (every serializer built by `ScopeFilterAPIMixin`), `_refuse_relations_out_of_reach` (every MCP write) |

A record out of reach answers as an unknown one (`404`) : the refusal does not
tell whether it exists. A visitor who is not signed in is sent to the login
page, even by a view that fetches its parent record before its login check
(`accounts.middleware.AuthenticationRequiredMiddleware`). A record filed under
no scope at all stays reachable by its address : scoping restricts what has been
filed under a perimeter, it does not hide what nobody has filed yet.

**A relation is a way to reach a record.** Choosing a record in a form, or
naming its identifier in a request, links it to one's own, shows its name back
and may copy what it holds (a support asset inherits the security needs of the
essential assets it is attached to). So a relation offers and accepts what the
registers show the user, and nothing else :

- a select or a picker lists the records within the user's scopes, plus what
  the record being edited already holds (a link set by someone with a wider
  reach is neither refused nor dropped by saving the form again);
- an identifier out of reach is refused in the words of an unknown one, on the
  web, the REST API and the MCP server alike;
- a user limited to some scopes files what they create under one of them : the
  scopes of a new record are required for them, since a record filed under
  nothing is one its own author no longer finds in the register;
- a scope the editor is not given, set on a record by someone else, is shown
  and kept when the record is saved.

Forgetting the scope on a new surface is a test failure, not a review comment.
`core/tests/test_scoping.py` walks the URL configuration, the models, the forms
and the source of the MCP tools : every single-record view goes through the
guard, every model that hangs under a scoped record declares its path, every
REST class serving such a model carries the mixin, every register (list view)
of such a model does too, no view module calls Django's own
`get_object_or_404`, every form view and every form built by hand
restricts its relations, every serializer built by an action does too, no MCP
tool queries `Model.objects` outside `_reach` and `_fetch`, and every MCP write
checks the relations it is given. Each has an explicit list of exceptions, with
the reason of each.

The structure is not the result, so the result is checked as well.
`core/tests/test_tenancy_sweep.py` loads the demo dataset, signs in a user who
holds every permission but one scope, and asks each surface for what lies
outside it : every `list_` tool of the MCP server and every tool that takes an
identifier, every list and single-record route of the REST API, every register
of the web interface, every page that takes one record, every creation form.
Nothing out of reach may come back. It exists because a test of the filtering helper once passed while sixty
families of MCP tools were registered with the filter switched off.

**A generated report needs every scope it was drawn from.** The usual rule is
"one scope in common" : a record filed under two scopes belongs to both. A
report is not a record of the register, it is a copy of what one or several
scopes held when it was generated : sharing one of them must not open what was
drawn from the other. `Report` sets `scope_requires_every_scope`, which
`core/scoping.py` applies on every surface : a report is reached by who is
given every scope it is filed under, and one filed under none (the whole
instance) by nobody the scopes restrict. `Report.objects.record(author,
sources=..., scope_ids=...)` files it as it is created : the scopes of its
sources, narrowed to those of an author who is limited to some, so that an
author always reads their own report. Reports made before this rule keep the
scopes of the assessment and of the frameworks they still point at; the others
(management review minutes, risk registers) are left filed under nothing until
they are generated again.

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
lifecycle event live. That gate is decided in one place for every surface
(`core.lifecycle.user_can_perform`) : the permission the transition names, or
the roles and users it is restricted to, and for a transition that declares
nothing, the permission to change the record. No transition is open to a
reader. A verdict kept for a stricter permission is therefore named by the
lifecycle, never by a dedicated view alone : validating or rejecting an EBIOS
RM workshop asks for `validate`, an action plan for `validate`, `implement`,
`close` or `cancel` according to the step, closing a management review for
`approve`, whichever endpoint or tool performs the move. The MCP create and
update tools of the entities whose `status` is their lifecycle step may write
it directly, for an import : that write is held to the same permission, and
is refused as a whole when the caller could not have made the move. Three
incident registers go further and are append-only at
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

## Content Security Policy

Every response carries a `Content-Security-Policy` header (`core/csp.py`). It
tells the browser to run a script only when it comes from the instance's own
static files, or carries the nonce generated for that very response :

```text
default-src 'self'; script-src 'self' 'nonce-<random>'; style-src 'self' 'unsafe-inline';
img-src 'self' data: blob: <map tiles>; font-src 'self' data:;
connect-src 'self' ws://<host> wss://<host> <geocoder>;
object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'
```

It is the second line behind output escaping and the rich-text sanitiser : a
script that reached a page anyway (a field that escaped sanitising, a tampered
record) has neither the origin nor the nonce, and is refused. So is an inline
event handler, a `javascript:` link, `eval`, a plugin, a form posting elsewhere
and a page framing this one. The only other origins are the ones a setting
names : the map tiles (`img-src`) and the geocoder (`connect-src`).

What keeps it that way :

- No template has an inline event handler. An element names an action
  registered in `window.cairnActions` (`data-on-click="..."`,
  `static/js/cairn/actions.js`); only a registered function can be named.
- Every inline `<script>` carries `nonce="{% csp_nonce %}"`. htmx gives the
  scripts of a swapped fragment the nonce of the page, and evaluates nothing
  written in an attribute (`allowEval` is off).
- The error pages contain no script (the 500 page is rendered with no context
  and could carry no nonce).
- Tests refuse a handler, a script without its nonce or an `hx-on` attribute
  in any template, and the browser audit of the CI fails on any violation a
  browser reports (see [testing](testing.md#accessibility)).

Styles are allowed inline (`style-src 'unsafe-inline'`). A style cannot run
code, and the libraries in use position their elements with style attributes.
What an injected style could do is leak a value through a request to another
site, and the policy leaves it nowhere to send one : images, fonts and
connections are limited to the instance (and to the map services, when the
operator names some).

Three more headers go with every page and API answer.
`Cross-Origin-Resource-Policy: same-origin` keeps another site from reading
one by embedding it. `Permissions-Policy` switches off the browser features
the application never uses (camera, microphone, geolocation, payment, USB and
sensors), for the page and for anything it could be made to embed. With
`SECURE_SSL_REDIRECT` on, the policy adds `upgrade-insecure-requests`.

A stored file is never served with the type its uploader declared unless that
type is inert (`core/downloads.py`) : a contract uploaded as `text/javascript`
or `text/html` goes out as `application/octet-stream`, always as an
attachment, so it can be neither run nor rendered from the instance's origin.

`CSP_MODE=report` sends the policy as `Content-Security-Policy-Report-Only` :
nothing is blocked, violations appear in the browser console. It is there to
try the policy on an instance whose reverse proxy injects something into the
pages. `CSP_MODE=off` sends no policy. Leave it on `enforce`.

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

What can be safe by default is : cookies only travel over HTTPS, a session
ends after twelve hours, no browser is sent to an outside service, access
tokens expire, pages run under a Content Security Policy. The rest the
platform cannot do for you.

1. **Serve over HTTPS**, then turn on `SECURE_SSL_REDIRECT` and HSTS, which
   stay opt-in because they lock a host out when turned on too early. The order
   and the HSTS caveat are in [configuration.md](configuration.md#https-hardening).
   Set `FORWARDED_ALLOW_IPS` to your proxy's address if the application's port
   can be reached without going through it.
2. **Set a real `SECRET_KEY`** and keep it out of the image. With `DEBUG` off,
   Cairn refuses to start while the key is one of the public placeholders.
3. **Leave `DEBUG` off** (it is the default) and set a specific `ALLOWED_HOSTS`.
4. **Run `python manage.py check --deploy`** and read what it says.
5. **Back up PostgreSQL and the media directory together.** The history tables
   are in the database, the evidence artefacts are on disk, and a restore that
   has one without the other is not a restore. `manage.py backup` writes both
   into one checksummed archive, which holds every secret of the instance :
   store its copies encrypted. See [operations.md](operations.md#backups).
6. **Review the group assignments.** The default groups are a starting point;
   who is in them is your decision and your audit finding.
7. **Decide what may leave a browser.** Maps (`MAP_TILE_URL`) and address
   lookup (`MAP_GEOCODER_URL`) are off until you name a provider, because
   each tells a third party something about what your users look at.

## Reporting a vulnerability

Open a private security advisory on the
[GitHub repository](https://github.com/frousselet/cairn/security/advisories)
rather than a public issue.
