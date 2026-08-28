# SDK

For whoever changes Cairn's code. Each page walks one extension point from end
to end, in the order you actually touch the files, and finishes with what the
change has to prove before it ships.

| Page | Extension point |
| --- | --- |
| [Dashboard widget](dashboard-widget.md) | Add a tile to the home dashboard |
| [Entity](entity.md) | Add a domain entity, end to end : model, lifecycle, interface, API, MCP tool, seed, spec |
| [Lifecycle](lifecycle.md) | Declare or change a governance lifecycle |
| [REST endpoint](rest-endpoint.md) | Expose a resource on `/api/v1/` |
| [MCP tool](mcp-tool.md) | Expose a capability to assistants and scripts |
| [Report](report.md) | Generate a PDF, DOCX, PPTX or XLSX deliverable |
| [Assistant provider](assistant-provider.md) | Plug a different LLM backend into Ask Cairn |
| [Interface conventions](ui-conventions.md) | The patterns a new screen is expected to follow |

## The idea to hold on to

Almost nothing in Cairn is wired by hand. A widget, a lifecycle, a permission,
an MCP tool and a URL route are all **declared in a registry** and discovered
from it. That is why adding one is short, and why forgetting to declare one is
the failure mode rather than forgetting to call it.

It is also why the [reference](../reference/README.md) can be generated : the
same registries the application reads at runtime are what the documentation
reads at build time. A registry entry you add shows up in the documentation
without you writing a line of it, and CI fails until you regenerate.

## Three rules that are not negotiable

They come up on every page, so they are stated once here.

**Every feature gets an MCP tool and a REST endpoint.** Not eventually. A
capability that exists only in the interface is one that scripts, integrations
and assistants cannot reach, and it quietly makes the API a partial view of the
platform.

**Every user-facing string is translated.** Wrapped with `_()` or `{% trans %}`,
with a French entry added in the same change. See
[internationalisation](../technical/internationalization.md).

**Governance is never bypassed.** State changes go through a lifecycle
transition, permissions are checked with the declared codename, scope filtering
is applied, and history is left intact. A shortcut here is not a shortcut, it is
an audit finding.

## Before you start

Read [the architecture](../technical/architecture.md) for the cross-cutting
patterns every module inherits, and get the application running with the demo
dataset ([installation](../technical/installation.md)) : most of these pages
assume you can see what you changed.
