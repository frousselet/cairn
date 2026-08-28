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
`DOCKERHUB_TOKEN`. The wiki needs `WIKI_DEPLOY_KEY`, and the choice of
credential there is worth understanding rather than copying.

### Why the wiki needs its own credential

A wiki is a **separate git repository** (`<repo>.wiki.git`) that GitHub gates
differently from the code. `GITHUB_TOKEN`, the credential a workflow gets for
free, generally cannot write to it, and **fine-grained** personal access tokens
have no wiki permission at all, so they cannot either, however they are
configured.

That leaves two options, and they are not equivalent:

| Credential | Reach |
| --- | --- |
| Classic PAT with the `repo` scope | Write access to **every repository the account owns** |
| Deploy key with write access | This repository alone, wiki included |

A classic PAT stored as a repository secret is a standing grant over your whole
account, readable by any workflow that runs in this repository. Publishing
documentation does not warrant that. **Use a deploy key.**

### Installing the deploy key

```bash
ssh-keygen -t ed25519 -N '' -C cairn-wiki -f /tmp/cairn-wiki
gh repo deploy-key add /tmp/cairn-wiki.pub --title 'Wiki publication' --allow-write
gh secret set WIKI_DEPLOY_KEY < /tmp/cairn-wiki
shred -u /tmp/cairn-wiki /tmp/cairn-wiki.pub
```

The private key goes into the secret and is then destroyed locally; it is never
displayed. Through the web interface the same two halves are
**Settings -> Deploy keys -> Add deploy key** (tick *Allow write access*, paste
the `.pub`) and **Settings -> Secrets and variables -> Actions** (name it
`WIKI_DEPLOY_KEY`, paste the private key).

A deploy key has no expiry. Rotate it by deleting the old key and repeating the
four commands.

The wiki also has to have been initialised once, by creating any page in the web
interface, before a workflow can clone it.

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
