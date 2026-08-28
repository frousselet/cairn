# Release process

## Before tagging

1. `pytest` passes, `ruff check .` is clean.
2. `python manage.py generate_docs` has been run and its output committed.
3. `python manage.py migrate` has been run against a **scratch PostgreSQL
   database**. The test suite disables migrations, so it cannot catch a broken
   one; see [testing.md](testing.md#why-it-starts-fast-and-what-that-costs).
4. `CHANGELOG.md` entries under `## [Unreleased]` are consolidated : one line
   per entry, one block per category, and no `Changed` or `Fixed` describing
   something `Added` in the same release.

## Tagging

The changelog promotion is the one commit that goes directly on `main`, with
exactly this message:

```bash
git commit -m 'Bump version `v0.36.0`'
git tag v0.36.0
git push origin main --tags
```

Promoting means moving the `## [Unreleased]` entries under a new
`## [0.36.0] - YYYY-MM-DD` heading and adding the comparison link at the bottom
of the file.

## What the tag triggers

| Workflow | Result |
| --- | --- |
| `docker-publish.yml` | Builds and pushes `frousselet/cairn` to Docker Hub with semver tags (`0.36.0`, `0.36`, `0`) and `latest`. `APP_VERSION` is baked into `/etc/app-version`, which is what the interface footer shows |
| `docs.yml` | Builds the wiki from `docs/` and pushes it to the wiki repository |

Both need repository secrets. The image needs `DOCKERHUB_USERNAME` and
`DOCKERHUB_TOKEN`. The wiki needs `WIKI_TOKEN`, and that one has a catch worth
knowing before release day.

A wiki is a **separate git repository** (`<repo>.wiki.git`) that GitHub gates
differently from the code:

- `GITHUB_TOKEN`, the credential a workflow gets for free, generally cannot
  write to it;
- **fine-grained** personal access tokens have no wiki permission at all, so
  they cannot either, however they are configured.

`WIKI_TOKEN` must therefore be a **classic** personal access token carrying the
`repo` scope.

1. Create it at
   [github.com/settings/tokens/new](https://github.com/settings/tokens/new?scopes=repo&description=Cairn+wiki+publication)
   (the link preselects the scope). Copy the value; GitHub shows it once.
2. Add it at
   [the repository's Actions secrets](https://github.com/frousselet/cairn/settings/secrets/actions/new),
   named exactly `WIKI_TOKEN`.

The wiki also has to have been initialised once, by creating any page in the
web interface, before a workflow can clone it.

Without the secret the workflow prints these steps and fails rather than dying
on an opaque git error, and the documentation can still be published by hand:

```bash
python scripts/build_wiki.py --out build/wiki --version v0.36.0
```

## The GitHub release

Always create it, immediately after pushing the tag. The notes are that
version's `CHANGELOG.md` section, ending with the full comparison link.

```bash
gh release create v0.36.0 --title "v0.36.0" --notes "$(cat <<'NOTES'
### Added
...

**Full changelog**: https://github.com/frousselet/cairn/compare/v0.35.0...v0.36.0
NOTES
)"
```

## After

Check that the wiki actually updated : the workflow reports what it pushed, and
the [Home page](https://github.com/frousselet/cairn/wiki) footer carries the
version it was built from. A wiki still showing the previous version means the
publication step failed, and it fails silently from a reader's point of view.
