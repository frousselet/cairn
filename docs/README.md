# Cairn documentation

Everything written about Cairn lives in this directory. It is the source : the
[GitHub wiki](https://github.com/frousselet/cairn/wiki) is a rendering of these
files, republished by CI on every release.

The set is split by the question you arrived with.

| I want to | Read |
| --- | --- |
| Use the platform | [User guide](user-guide/README.md) |
| Install, configure and operate it | [Technical documentation](technical/README.md) |
| Extend it : a widget, an entity, a tool | [SDK](sdk/README.md) |
| Look up an endpoint, a tool, a permission | [Reference](reference/README.md) |
| Know what a module is contractually meant to do | [Specifications](specs/README.md) |
| Change how it looks | [Brand guidelines](brand/brand-guidelines.md) |

## The four kinds of page, and why they are separate

Cairn is a compliance platform, so its documentation carries the same burden as
its data : a reader has to be able to tell what is a promise, what is a fact,
and what is advice. The four sections answer four different questions and are
never merged.

**The user guide** is written for the person doing GRC work, in the vocabulary
of the job rather than of the code. It says which screen to open and what the
platform will do in response. It is illustrated, because a screenshot settles an
ambiguity that three paragraphs cannot.

**The technical documentation** is written for whoever installs, configures,
secures and operates the deployment. It stops at the boundary of the code : how
to run it, not how to change it.

**The SDK** is written for whoever changes the code. Each page walks one
extension point end to end, from the registry entry to the test, in the order
you actually touch the files.

**The reference** is the exhaustive, mechanical listing : every endpoint, every
MCP tool, every permission, every lifecycle step. Most of it is
[generated from the code](reference/README.md#generated-pages) and is therefore correct by
construction rather than by diligence.

**The specifications** sit apart from all four. They are the contract each
module is held to : business rules, field-level constraints, lifecycle
governance. They are what an auditor reads, and what a change has to be measured
against before it ships.

## How this stays true

Documentation that drifts is worse than none, because it is trusted. Three
mechanisms keep this set honest, in decreasing order of strength.

1. **Generation.** The pages under [reference/generated/](reference/README.md#generated-pages)
   are rendered from the registries that the running code itself reads : the
   permission registry, the lifecycle registry, the widget registry, the MCP
   tool registry, the URL resolver, the model registry, `.env.example`. They
   cannot describe a system that does not exist.
2. **A CI gate.** `python manage.py generate_docs --check` runs on every push
   and every pull request. Add a permission, a widget, a lifecycle step, an MCP
   tool or an endpoint without regenerating, and the build fails. The same job
   validates every internal link in this directory.
3. **A rule.** Prose that cannot be generated is covered by the project
   convention that a feature change updates its documentation in the same
   commit. This is the weakest of the three, which is why the first two carry as
   much of the load as they can.

The mechanics are described in
[technical/documentation.md](technical/documentation.md).

## Layout

```
docs/
├── user-guide/         For the people doing GRC work, with screenshots
├── technical/          Install, configure, secure, operate, contribute
├── sdk/                Extend the platform : one page per extension point
├── reference/          Exhaustive listings; reference/generated/ is code-derived
├── specs/              The per-module contract : business rules, entity fields
├── brand/              Palette, typography, components, motion, accessibility
├── screenshots/        Shared image set (2560x1440), used by the guide and the README
└── qa/                 Historical test campaign reports, not part of the published set
```
