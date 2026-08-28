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

The trade-off has a second consequence worth knowing : **the suite does not
exercise the migrations**. A migration that is broken will pass CI and fail on
deployment. Run `python manage.py migrate` against a scratch PostgreSQL database
before tagging a release.

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
   through a child entity or the generic history endpoint.
3. **The lifecycle.** The transitions that should be allowed are, the ones that
   should not are refused with the right status, and a required comment is
   actually required.
4. **The contract.** Read-only fields cannot be written. Append-only registers
   answer `405` on `PUT` / `PATCH` / `DELETE`. A computed field is not writable.
5. **The behaviour.** Whatever the feature actually does.

## Continuous integration

`.github/workflows/tests.yml` runs on every push to `main` and every pull
request:

1. `ruff check .`
2. `python manage.py compilemessages` (a duplicate `msgid` fails here)
3. `pytest -x -v --tb=short --cov --cov-report=term-missing`

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
