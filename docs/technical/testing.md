# Testing

## Running the suite

```bash
pytest                                   # everything
pytest incidents/tests/                  # one app
pytest incidents/tests/test_models.py    # one file
pytest -k "custody"                      # by name
pytest --co                              # collect only, run nothing
pytest -n auto                           # parallel (pytest-xdist)
pytest --cov --cov-report=term-missing   # with coverage
```

`pytest.ini` pins `DJANGO_SETTINGS_MODULE=core.settings_test`, so there is
nothing to export. Those settings use an in-memory SQLite database, MD5 password
hashing, an in-memory channel layer and a local-memory cache : the suite needs
neither PostgreSQL nor Redis.

## Why it starts fast, and what that costs

The test settings disable migrations, so Django builds the schema directly from
the current models. That skips roughly 150 historical migrations and cuts
start-up by an order of magnitude, but it also skips the **data** migrations
that seed permissions, system groups, lifecycles and risk criteria.

`conftest.py` puts that back : a session-scoped `django_db_setup` fixture
recreates the permissions and system groups once, after the schema exists. If
you add a data migration that seeds reference rows the suite depends on, it
needs a matching line there, or the tests will pass locally against a stale
database and fail on a fresh one.

The trade-off has a second consequence worth knowing : **this fast run does
not exercise the migrations, nor PostgreSQL**. That is what the second run is
for.

## The PostgreSQL run

```bash
docker run -d --name cairn-test-pg -e POSTGRES_USER=cairn -e POSTGRES_PASSWORD=cairn \
  -e POSTGRES_DB=cairn -p 127.0.0.1:55432:5432 postgres:18-alpine
POSTGRES_HOST=127.0.0.1 POSTGRES_PORT=55432 POSTGRES_USER=cairn POSTGRES_PASSWORD=cairn \
  POSTGRES_DB=cairn pytest --ds=core.settings_test_postgres
```

`core.settings_test_postgres` keeps everything from the fast settings except
the database, which is PostgreSQL, and the migrations, which are replayed from
the first one. CI runs the whole suite a second time with it
(`test (PostgreSQL, migrations)` in `tests.yml`), after checking with
`makemigrations --check` that no model changed without its migration : on every
push to `main`, and on a pull request when it carries the `ci:postgres` label
or when the workflow is run by hand on its branch. It takes about five minutes
locally instead of one, which is why it is not the default; run it
locally before a change to a migration, to a raw query or to anything that
groups, orders or compares in the database. Do not add `-n` to it : every
worker would replay the migrations on a database of its own, and the run gets
slower.

## The interface sweep

`core/tests/test_site_sweep.py` loads the demo dataset, follows every link from
the dashboard as a superuser, requests the same pages as an administrator who
is not a superuser and as a user with no permission, then submits every create
and edit form empty and with invalid values. No page may answer a server error
and no printed link may be broken. It covers what nobody thought of writing a
test for : it was first run by hand and found four server errors the rest of
the suite was green on.

It is also the only test that executes `scripts/seed_demo_data.py`, so it is
what enforces that the seed follows the schema. It is part of the default run
and takes under a minute; while iterating on something else, leave it out with
`pytest -m "not sweep"`. A page it should not open (one whose `GET` has an
effect) goes in its `SKIP` pattern, with the reason.

## The tenancy sweep

`core/tests/test_tenancy_sweep.py` loads the same dataset and signs in a user
who holds every permission but is given one scope. It then asks each surface
for what lies outside that scope : every `list_` tool of the MCP server, every
MCP tool that takes an identifier (handed one of each model out of reach, the
tools that change and delete included), every list and single-record route of
the REST API, every register of the web interface, every page that takes one
record, every creation form. Nothing
out of reach may come back, and nothing out of reach may have moved. With
every permission granted, a refusal can only come from the scopes, so a
surface that answers is a leak.

It complements `core/tests/test_scoping.py`, which checks the structure (the
mixin a class must carry, the helper a tool must call). The structure once
held while sixty families of MCP tools were registered with the scope filter
switched off : a test of a helper proves the helper, not the surfaces that are
supposed to call it. It is marked `sweep` as well, and adds about fifteen
seconds.

## Accessibility

The target is WCAG 2.2 AA, held by three checks that each see what the others
cannot.

**The tokens** (`core/tests/test_contrast.py`). The palette is read from
`static/css/cairn/00-tokens.css` and every text token is measured against
every surface, in the light and the dark theme : under 4.5:1, the test fails.
It also refuses a *fill* token (`--accent`, `--success`...) used as a text
colour anywhere in the style sheets and templates; text uses the ink tokens
(`--accent-text`, `--success-text`...). A rule of the design system that draws
at a partial `opacity` must be listed in the test with its reason (a disabled
control, an icon, an animation) : a text is made quieter by a text token or a
weight, never by an opacity. The colours an administrator types
(company accent, Trust Center accent) are covered through `core/colors.py`,
which derives a readable tone from any of them.

**The markup of every page** (`core/tests/markup_audit.py`, run by the
interface sweep). Each page the crawl reaches is parsed for an image without
`alt`, a link or button without an accessible name, a link that acts without
an `href` (out of the keyboard's reach), a form control without a label, a
positive `tabindex`. It sees closed panels and modals, which a browser audit
skips because they are hidden.

**The rendered pages** (`scripts/a11y_audit.py`, the `accessibility` job).
Contrast on a tinted row, the name of a control drawn by a script, the size of
a target : only a browser knows. The script opens every page of the screenshot
set plus the sign-in page, a form and the component catalogue, in both themes,
runs [axe-core](https://github.com/dequelabs/axe-core) on each and fails on
any violation of a level A or AA rule. It also opens an edit dialog, a filter
panel and the About dialog before auditing them (axe skips what is hidden),
and audits the dashboard, a list, a record and the calendar again at a phone's
width : about a hundred and ten renderings in four minutes. To run it locally :

```bash
npm pack axe-core@4.10.3 && tar -xzf axe-core-4.10.3.tgz package/axe.min.js
export DJANGO_SETTINGS_MODULE=core.settings_local LOCAL_POSTGRES=1    # with the POSTGRES_* variables of a scratch server
python manage.py migrate --noinput
python manage.py shell -c "exec(open('scripts/seed_demo_data.py').read())"
python manage.py runserver 127.0.0.1:8000 --noreload &
python scripts/a11y_audit.py --axe package/axe.min.js            # every page, both themes
python scripts/a11y_audit.py --axe package/axe.min.js --only calendar --theme dark
```

It needs `google-chrome-stable` on the `PATH`. A page that does not render
fails the audit : an error page would otherwise pass for the page it stands in
for.

**The instance must be built by the real migrations**, which is why the job
runs on PostgreSQL (`LOCAL_POSTGRES=1` keeps the main settings' database under
the local settings). The help content, the default lifecycles and the
reference data are written by data migrations : an instance without them is
not the one a deployment serves. The audit first ran on a database built
straight from the models, and passed while the help dialog's script was being
refused on every real instance.

For a quick look while working on one page, a throwaway SQLite instance is
ready in fifteen seconds, with that blind spot :

```bash
export DJANGO_SETTINGS_MODULE=core.settings_local SQLITE_PATH=/tmp/cairn-a11y.sqlite3 SCHEMA_FROM_MODELS=1
python manage.py migrate --run-syncdb --noinput
python manage.py shell -c "from accounts.reference_data import sync_system_permissions; sync_system_permissions(); exec(open('scripts/seed_demo_data.py').read())"
``` `--best-practice` adds axe's advisory rules, which never fail the
run. axe-core is fetched, not vendored : it is a development tool that is
never served to a user, and its version is pinned in the workflow.

The same visit checks that the page **works under the Content Security
Policy** : anything the browser refused (an inline handler, a script without
its nonce, a request to an origin the policy does not list) and any error a
script threw fail the page. Server-side tests cannot see this, since the page
renders either way; `core/tests/test_csp.py` covers what can be read from the
sources (no handler, no script without nonce, every named action registered).

No automated check proves a page accessible : these catch regressions on what
a machine can measure. A new kind of page is added to the audit's page list,
and tried once with the keyboard alone.

**What the product says of itself** (`core/accessibility.py`). The About
dialog, `GET /api/v1/accessibility/` and the `get_accessibility_statement` MCP
tool give one statement : the level the product is built to meet, these three
checks, and a conformance of `not_assessed`, since nobody has evaluated the
product against every criterion. `core/tests/test_accessibility.py` holds the
statement to the checks (the level it names is the one the browser audit
fails on, every check it lists is a file the workflow runs) and pins the
status : the day an evaluation exists, the status, the test and the record of
who made it change together.

## Usability

What a screen owes to someone who has never used the product is written as a
standard ([usability standard](../sdk/usability-standard.md)), and the part of
it that can be measured is held by tests, the way contrast is :

| Test | What it holds |
| --- | --- |
| `core/tests/test_usability_standard.py` | The forms and pages brought to the standard : a creation of six fields at most on one screen, helpers that say something (in English and in French), no acronym alone as a label, sections on the edit form, landing on the record, the completeness card, the empty register |
| `core/tests/test_modal_forms.py` | The shared shell : a footer whose buttons carry words, steps as buttons, sections, required errors named after their field |
| `core/tests/test_completeness.py` | What *complete* means for each model that declares it, against its lifecycle and its form; the refusal on the web, the REST API and MCP; permission answered before completeness |
| `core/tests/test_getting_started.py` | The first steps of a new instance, and that an empty instance reports neither success nor failure |

| `core/tests/test_glossary.py` | The vocabulary, for the whole product : no spelling the glossary retires in the French catalogue, no acronym alone as a label, an acronym that spreads explained; the glossary on its page, in the search palette, over REST and MCP |
| `core/tests/test_translations.py` | The French catalogue against the code : nothing missing (the menu and the column headings included), a counted sentence filed as a plural, variables kept. Needs `xgettext`; fails rather than skips in CI without it |
| `helpers/tests/test_help_content.py` | The help of every page : one per page that asks for it, in both languages, a title that defines, a body with an example, acronyms spelled out; the migration leaves a rewritten help alone; hiding and bringing back |

A screen is added to the list of the first test when it is brought to the
standard : the list is what is claimed, nothing more. The three tests about
words hold every screen, listed or not.

## Warnings

The suite runs with no warning, and two of them fail it on purpose
(`filterwarnings` in `pytest.ini`), because they are defects rather than noise :

- **an API list paginated without a total order** (`UnorderedObjectListWarning`),
  whose pages can repeat one row and skip another;
- **a date-time compared with a naive value**, which is read in the wrong time
  zone.

A warning that appears after a dependency upgrade is either fixed or silenced
there with the reason, so the next one is noticed. The only one silenced today
is the notice Django 5.2 prints about `FORMS_URLFIELD_ASSUME_HTTPS`, a
transitional setting the project sets on purpose.

Factories whose post-generation hooks only set relations declare
`skip_postgeneration_save = True`. One that relies on a save once its relations
exist (`ObjectiveFactory`, whose model checks scopes on save) does that save
itself in `_after_postgeneration`.

## How tests are organised

Every app has a `tests/` package with the same two kinds of file.

```
<app>/tests/
├── factories.py      factory-boy factories, one per model
├── test_models.py    validation, computed fields, lifecycle side effects
├── test_views.py     the web surface : permissions, filtering, HTMX partials
├── test_api.py       the REST surface : contract, permissions, tenancy
└── test_*.py         one file per behaviour worth isolating
```

Use the factories. They set the required fields, respect the lifecycle's initial
step and generate references, so a test that builds a model by hand is usually a
test that will break when a field becomes required.

## What a test for a new feature has to cover

A feature is not tested because it has a test; it is tested when the things that
would be embarrassing to get wrong are pinned down. For this platform that
means, in order:

1. **The permission.** An unauthorised caller is refused, on the web view, the
   REST endpoint and the MCP tool. Three surfaces, three assertions.
2. **The tenancy.** A user outside the scope does not see the record, including
   through a child entity or the generic history endpoint, and can neither
   change nor delete it by its address. The structural tests of
   `core/tests/test_scoping.py` already fail on a view, a model or a REST class
   that forgets the scopes; a feature adds the behavioural assertion for its
   own records.
3. **The lifecycle.** The transitions that should be allowed are, the ones that
   should not are refused with the right status, and a required comment is
   actually required.
4. **The contract.** Read-only fields cannot be written. Append-only registers
   answer `405` on `PUT` / `PATCH` / `DELETE`. A computed field is not writable.
5. **The behaviour.** Whatever the feature actually does.

## Continuous integration

`.github/workflows/tests.yml` has three jobs. All install `requirements.txt`
on the Python version of the image.

`test`, the fast run on SQLite, on every push to `main` and every pull request :

1. `ruff check .`
2. `python manage.py compilemessages` (a duplicate `msgid` fails here)
3. `pytest -x -v --tb=short --cov --cov-report=term-missing`, interface sweep
   included

`test (PostgreSQL, migrations)`, on the PostgreSQL major the compose file
ships, on every push to `main`, and on a pull request only when it carries the
`ci:postgres` label or when the workflow is run by hand
(`gh workflow run tests.yml --ref <branch>`) :

1. `python manage.py makemigrations --check --dry-run` (a model changed without
   its migration fails here)
2. `pytest --ds=core.settings_test_postgres -x`, every migration replayed

Both run with `DEBUG` off and a key of their own, like a deployment.

`accessibility (axe-core, both themes)`, on every push to `main` and every
pull request :

1. a demo instance is migrated on PostgreSQL, seeded and served
   (`core.settings_local` with `LOCAL_POSTGRES=1`). The migrated, still empty
   database is cached as a dump keyed on the content of the migration files,
   since replaying them takes seven minutes; `migrate` runs after a restore
   too
2. `python scripts/a11y_audit.py` audits every page in both themes (see
   [Accessibility](#accessibility))

`.github/workflows/docs.yml` adds the documentation gate : the generated
reference pages must be current, and every internal documentation link must
resolve. See [documentation.md](documentation.md).

`-x` means the first failure stops the run, so read the first failure rather
than the last line.

## Linting

```bash
ruff check .          # what CI runs
ruff check --fix .    # apply the safe fixes
```

The configuration lives in `pyproject.toml`.
