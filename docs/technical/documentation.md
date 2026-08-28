# The documentation system

How this documentation set is written, kept true and published. If you are
looking for the documentation itself, start at [docs/README.md](../README.md).

## Where it lives

`docs/` is the source, and the only source. The
[GitHub wiki](https://github.com/frousselet/cairn/wiki) is a rendering of it,
rebuilt by CI. **Never edit the wiki directly** : the next release overwrites
it, and your change is gone without a trace because the wiki keeps no pull
request to point at.

```
docs/
├── README.md         the index; becomes the wiki Home page
├── user-guide/       for the people doing GRC work
├── technical/        install, configure, secure, operate, contribute
├── sdk/              extend the platform
├── reference/        exhaustive listings
│   └── generated/    written by a command, never by hand
├── specs/            the per-module contract
├── brand/            the visual system
├── screenshots/      shared images, 2560x1440
└── qa/               historical test campaigns, excluded from publication
```

## Generated pages

Everything under `docs/reference/generated/` is rendered from the registries the
running code itself reads.

| Page | Source of truth |
| --- | --- |
| `permissions.md` | `accounts/constants.py` : `PERMISSION_REGISTRY`, `SYSTEM_GROUPS` |
| `lifecycles.md` | `core/lifecycle.py` and each app's `lifecycles.py` |
| `dashboard-widgets.md` | `core/dashboard.py` : `DASHBOARD_WIDGETS` |
| `mcp-tools.md` and `mcp-tools-<module>.md` | The MCP tool registry |
| `rest-endpoints.md` | Django's URL resolver |
| `models.md` | The Django model registry |
| `settings.md` | The settings modules, parsed, cross-checked against `.env.example` |
| `management-commands.md` | The management-command registry |

```bash
python manage.py generate_docs                  # rewrite them
python manage.py generate_docs --check          # verify, write nothing, fail if stale
```

Do not edit these files. Every one carries a do-not-edit banner naming its
source, and an edit is reverted by the next run. Change the code and regenerate.

Two properties are worth knowing about the generator. It is **deterministic** :
the same code produces byte-identical output, which is what makes `--check`
meaningful rather than flaky. And it **removes orphans** : a page a generator no
longer produces is deleted rather than left to be published for ever.

## The CI gate

`.github/workflows/docs.yml` runs on every push and pull request and does three
things.

1. `generate_docs --check`. Add a permission, a lifecycle step, a widget, an MCP
   tool or an endpoint without regenerating, and the build fails with a diff.
2. **Link validation.** Every relative link and image in `docs/` must resolve to
   a file that exists. A link to a directory fails too, because the wiki has no
   directories to link to.
3. **A wiki build dry run**, so a page-name collision or a broken rewrite is
   caught before release day rather than on it.

## Publication to the wiki

On a version tag, the same workflow builds the wiki and pushes it.

GitHub wikis are a git repository with one hard constraint : **directories have
no effect on a page's URL**. A page is addressed by its filename alone, so page
names have to be globally unique and the tree has to be flattened. The build
does that mechanically.

| Source | Wiki page |
| --- | --- |
| `docs/README.md` | `Home` |
| `docs/technical/README.md` | `Technical` |
| `docs/technical/security.md` | `Technical-Security` |
| `docs/sdk/dashboard-widget.md` | `SDK-Dashboard-Widget` |
| `docs/reference/generated/mcp-tools.md` | `Reference-Generated-MCP-Tools` |
| `docs/specs/m4-risks/ebios-rm/feared-event.md` | `Specs-M4-Risks-EBIOS-RM-Feared-Event` |

The build also:

- rewrites every relative link to the flattened page name, preserving `#anchors`;
- rewrites links that point outside `docs/` (`../LICENSE`, `../mise.toml`) to
  absolute URLs on the repository, since those files are not in the wiki;
- copies `docs/screenshots/` into the wiki and rewrites image links to absolute
  raw wiki URLs, which resolve from any page regardless of nesting;
- generates `_Sidebar.md` (the navigation, grouped by section) and `_Footer.md`
  (the version and a link back to the source file);
- fails on a page-name collision rather than silently overwriting a page.

```bash
python scripts/build_wiki.py --out build/wiki      # build locally
python scripts/build_wiki.py --check               # validate links only
```

## Writing rules

**Point at files, never at directories.** `[Testing](testing.md)`, not
`[Technical](technical/)`. The second cannot become a wiki page.

**Use relative links within `docs/`.** The build rewrites them. An absolute
`https://github.com/.../blob/main/docs/...` link survives the build but sends the
reader out of the wiki and into the repository.

**Reference images from `docs/screenshots/`** with a relative path. They are
captured at 2560x1440 so the whole set stays visually consistent.

**Write in English.** French is for translated interface strings, not for
documentation.

**No em dash.** Use ` : ` or ` - `, in prose as in code.

**Keep a page answering one question.** The sidebar is flat, so a page that
covers three topics is a page nobody finds twice.

## Which section does a change belong in

| The change | Update |
| --- | --- |
| The interface behaves differently | `docs/user-guide/` |
| A deployment knob, a service, a security property | `docs/technical/` |
| A new extension point, or one that changed shape | `docs/sdk/` |
| An entity's fields, rules or lifecycle | `docs/specs/` |
| A registry entry (permission, widget, tool, route) | Nothing by hand : regenerate |
