# Contributing

## The shape of a change

Work happens on a branch, never on `main`. One session of work is one branch,
even when the later parts of it turn out to be unrelated to the first : a
session split across two branches is two half-reviews.

```bash
git checkout -b feat/supplier-attestations
# ... work, commit, push ...
git push -u origin feat/supplier-attestations
```

Push after each commit rather than batching to the end, so the work is never
only on your machine. That is about pushing often, not committing often :
a commit should still be a whole, verified unit of work, not a trail of
"wip" and "fix typo".

When a commit turns out to be wrong, rewrite it (`git commit --amend`, or
`git rebase -i` for an older one on your own branch) and force-push with
`--force-with-lease`. Never `--force` bare; the lease is what refuses to clobber
someone else's push. Stop rewriting once a reviewer has started reading the
commits, because their comments are anchored to what they read: from that point,
a follow-up commit is the honest option.

Never rewrite `main`, and never rewrite a merged commit.

## Commits

Written in English, regardless of the language of the discussion that produced
them. Authored as `Claude <noreply@anthropic.com>` when produced with the
assistant.

Conventional prefixes are used : `feat`, `fix`, `docs`, `refactor`, `test`,
`chore`, with the module in parentheses.

```
feat(incidents): add the evidence chain of custody
fix(compliance): stop the applicability recalculation from clearing manual overrides
docs(sdk): document the dashboard widget extension point
```

## What a change has to carry

These are not optional extras; a change missing one of them is incomplete.

| Requirement | Why |
| --- | --- |
| **An MCP tool** for every new feature | MCP is the primary integration surface. A feature reachable only in the interface is a feature scripts and assistants cannot use |
| **A REST endpoint** for every new feature | Same reason, different caller |
| **French translations** for every new string | The bilingual contract; an empty `msgstr` ships English into a French interface |
| **The specification updated** in the same commit | `docs/specs/` is the contract an auditor reads. A spec that lags the code is worse than no spec |
| **The user guide updated** when the interface changes | `docs/user-guide/` |
| **The reference regenerated** when a registry changes | `python manage.py generate_docs`; CI fails otherwise |
| **The seed updated** when the schema changes | `scripts/seed_demo_data.py` feeds the dashboard, the list views and the screenshots. A schema change with no seed update leaves those surfaces empty |
| **`CHANGELOG.md` updated** | One line per entry, under `## [Unreleased]` |
| **Both themes checked** | Light and dark; a component that only works in one is not done |
| **Mobile checked** | Especially multi-select widgets, sticky bars and form layouts |
| **Tests** | See [testing.md](testing.md) for what they have to cover |

## Changelog entries

Terse, and strictly so:

- **One line per entry.** A sentence. Not a paragraph, not a list of files.
- **One block per category per release.** A version has a single `### Added`,
  a single `### Changed`. Consolidate before tagging.
- **Never a `Changed` or `Fixed` about something `Added` in the same release.**
  A feature that only exists as of this release was never in a prior state to
  change. Fold the detail into the `Added` entry.

## Dependencies

What is installed, everywhere, is `requirements.txt` : every distribution at an
exact version, with its hashes. It is compiled from `requirements.in`, which
lists only what the project depends on directly.

- **To add or remove a dependency**, edit `requirements.in`, add it to the
  registry in `core/dependencies.py`, then recompile :
  `uvx --python 3.14 --from pip-tools pip-compile --generate-hashes --strip-extras --output-file requirements.txt requirements.in`
  (or `pip-compile` with the same options from an environment that has
  `pip-tools`). Existing pins are kept, so the diff shows the new distribution
  and what it brings.
- **Updates arrive by pull request.** Dependabot (`.github/dependabot.yml`)
  recompiles the file every Monday and proposes the result as one pull request,
  labelled `ci:postgres` so the suite also runs on PostgreSQL. It does the same
  for the Python patch releases of the image and for the GitHub Actions. A
  security advisory on a pinned version gets its own pull request without
  waiting for Monday. To take updates by hand, add `--upgrade` to the command
  above.
- **Django stays on its LTS line.** `requirements.in` constrains it to 5.2.x,
  Dependabot is told to ignore anything above, and a test fails if the compiled
  file leaves the line. Moving to the next LTS (6.2) is an upgrade of its own,
  with its release notes read and its deprecations handled.
- **Python.** The image, CI and `mise.toml` name the same version. Change the
  three together.

## Issues and pull requests

Both go through the templates in `.github/`. An issue is filed through
`bug_report.yml` or `feature_request.yml`; a pull request uses
`PULL_REQUEST_TEMPLATE.md`, with the Summary, Related issue and Changes sections
filled and every applicable checklist item ticked. The `gh` CLI does not apply
the template automatically, so build the body from it.

Titles and descriptions are written in English.

When a pull request carries a checklist, comment the progress on it at each
commit and tick the items as they land. That is the standard way of working, not
a courtesy for large changes only.

The PostgreSQL test job does not run on every pull request (it takes about
twelve minutes). Give the pull request the **`ci:postgres`** label, or run the
*Tests* workflow by hand on the branch, when the change touches a migration, a
raw query, or anything that groups, orders or compares in the database. It
always runs on `main`.

## Style

Code is English throughout : names, comments, docstrings. French appears only in
translated user-facing strings and in database values that are already stored in
French.

The em dash character is not used anywhere in the codebase. Use ` : ` or ` - `.

New code should read like the code around it. Match the surrounding comment
density, naming and idiom rather than importing a different house style into one
file.

## Visual changes

Anything visual, typographic, motion-related or component-level follows
[the brand guidelines](../brand/brand-guidelines.md), which are the single source
of truth for the palette, typography, spacing, iconography, motion and
accessibility commitments. If a change cannot be expressed within them, the
guidelines are updated first, with the maintainer's agreement, and then the
change is made.
