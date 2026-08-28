# User guide

For the people doing the work : running an ISMS, preparing an audit, handling an
incident, keeping a risk register honest. It is written in the vocabulary of the
job rather than of the code, and it says which screen to open and what the
platform will do in response.

If you are looking for how to install it, that is the
[technical documentation](../technical/README.md). If you are looking for the
exact rules an entity is held to, that is the
[specifications](../specs/README.md).

## Start here

| Page | What it covers |
| --- | --- |
| [Getting started](getting-started.md) | First run, signing in, and the shape of the interface |
| [Finding your way](finding-your-way.md) | Navigation, search, the command palette, the tasks board, the calendar, saved filters |
| [The dashboard](dashboard.md) | Reading it, and rearranging it into the one you want |
| [How records move](lifecycles.md) | Draft, validation, archive : the governance every record runs |

## The modules

| Page | What it covers |
| --- | --- |
| [Organisational context](organisational-context.md) | Scopes, issues, stakeholders, objectives, SWOT, roles, activities, indicators |
| [Assets and suppliers](assets.md) | Essential and support assets, CIA valuation, dependencies, SPOF, suppliers, contracts, certificates |
| [Compliance](compliance.md) | Frameworks, requirements, assessments, findings, nonconformities, action plans |
| [Risks](risks.md) | ISO 27005 and EBIOS RM assessments, the register, treatment, acceptance |
| [Incidents](incidents.md) | Events, incidents, evidence, statutory notifications, breaches, post-incident reviews |
| [Trust Center](trust-center.md) | Publishing your security posture, and handling document requests |
| [Reports and management review](reports.md) | Deliverables, and the ISO 27001 clause 9.3 review |
| [Ask Cairn](ask-cairn.md) | The optional natural-language assistant |
| [Administration](administration.md) | Users, groups, permissions, company settings, lifecycles, imports |

## A note on what you will see

Cairn is bilingual, and every screen adapts to your language. The screenshots in
this guide are of the English interface, populated with **Voltara Energy**, the
fictional renewable-energy operator that ships as the demo dataset. If you loaded
the sample data at first run, your instance looks like these pictures. If you
started from scratch, it will look emptier and fill up as you work.

Two things shape what *you* see, and they are worth knowing before you conclude
something is missing.

**Your permissions.** A menu entry you do not have permission to read is not
greyed out, it is absent. If a colleague describes a screen you cannot find, ask
what group they are in before assuming a bug.

**Your scopes.** Cairn filters records to the organisational perimeters you are
assigned. Two people looking at the same risk register can honestly see
different numbers, and neither is wrong. [Scopes](organisational-context.md#scopes)
explains the mechanism.
