# Module specifications

This directory is the single source of truth for what each Cairn module does and how it is structured. It replaces the historical `features_spec/M0-M4` monolithic files: each entity now lives in its own file so a feature change touches a focused doc instead of grepping a 60 KB markdown.

## Modules

| Module | Covers |
| --- | --- |
| [Module 0 : accounts](m0-accounts/README.md) | Users, groups, permissions, authentication, onboarding |
| [Module 1 : context](m1-context/README.md) | Scopes, issues, stakeholders, objectives, SWOT, roles, activities, indicators |
| [Module 2 : assets](m2-assets/README.md) | Essential and support assets, groups, sites, suppliers, contracts, certificates |
| [Module 3 : compliance](m3-compliance/README.md) | Frameworks, sections, requirements, assessments, findings, mappings, action plans |
| [Module 4 : risks](m4-risks/README.md) | Risk assessment, threats, vulnerabilities, risks, treatment, acceptance |
| [Module 4 bis : EBIOS RM](m4-risks/ebios-rm/README.md) | The ANSSI v1.5 workshops, W0 to W5 |
| [Module 5 : Trust Center](m5-trust-center/README.md) | The public curation layer : certifications, subprocessors, measures, documents |
| [Module 6 : incidents](m6-incidents/README.md) | Events, incidents, evidence and custody, notification obligations and filings, breaches, post-incident reviews |
| [Management review](management-review/README.md) | The ISO 27001 clause 9.3 entities |
| [Assistant](assistant/README.md) | Ask Cairn : the optional question mode and its pluggable provider |

## Cross-cutting specifications

These are not a module. They specify the platform-wide behaviours every module
inherits, which is why a change to one of them is a change to all of them.

| Specification | Covers |
| --- | --- |
| [Lifecycle governance](governance/workflow.md) | The governance contract : steps, transitions, what a step decides |
| [Lifecycle engine](governance/lifecycle.md) | The engine internals behind that contract |
| [Dashboard](governance/dashboard.md) | The configurable widget dashboard |
| [History](governance/history.md) | The audit-trail framework |
| [Kanban](governance/kanban.md) | The unified tasks board |

Each module directory contains:

- a `README.md` : module overview, business rules (`RG-*`, `RS-*`), API base path, permission codenames, cross-cutting concerns (notifications, UI principles);
- one `<entity>.md` per domain entity : model fields, validation, lifecycle, references back to the module's business rules.

## Conventions

- File names are **kebab-case** of the entity name (`essential-asset.md`, not `EssentialAsset.md`).
- Entity headers are H1; field tables follow the convention `| Field | Type | Constraints | Description |`.
- Cross-references between entities use relative links: `[Objective](objective.md)`.
- Business rules keep their original identifier (`RG-01`, `RS-04`, etc.) so legacy commit messages and code comments stay searchable. Rules retired by a later decision are kept as struck-through entries with a reason : see `m1-context/README.md` for an example.
- Enums and choice lists are reproduced verbatim from the model so the doc is grep-able against the code.

## Relationship with the code

The doc references models by their Django class name (e.g. `Indicator`, `ComplianceAssessment`) and points at the importable path (`context.models.indicator.Indicator`) at the top of each entity file. The doc is updated in the same commit as the model change : there is no separate "spec PR" step.

When the implementation diverges from a documented intent, the doc is updated rather than the code being rolled back, unless the divergence is a bug. Document the rationale in the doc itself or in `CHANGELOG.md`.
