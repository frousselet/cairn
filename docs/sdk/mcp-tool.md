# Adding an MCP tool

MCP is Cairn's primary integration surface : it is how assistants and scripts
work with GRC data. Every feature is expected to be exposed as a tool, with an
accurate description and accurate parameter descriptions, because those strings
are the only thing a model has to decide with. A vague description is not a
documentation problem, it is a wrong tool call.

The complete registry is
[reference/generated/mcp-tools.md](../reference/generated/mcp-tools.md), with
per-module parameter tables.

## How registration works

`mcp/tools.py` holds one `_register_<module>_tools(server)` function per module,
all called from `register_all_tools(server)`. A tool is a name, a description, a
JSON Schema and a handler:

```python
server.register_tool(
    "list_supplier_attestations",
    "List supplier attestations with their framework and expiry date. "
    "Filter by supplier_id, framework_id or workflow_state.",
    _list_schema({
        "supplier_id": {"type": "string", "description": "Filter by supplier ID"},
        "framework_id": {"type": "string", "description": "Filter by framework ID"},
    }),
    require_perm("assets.supplier_attestation.read")(list_handler),
)
```

`server.iter_tools()` is what the documentation generator reads, and
`require_perm` records its codename on the handler so the generated page can
state the permission per tool. Both exist so the reference is derived rather
than maintained.

## The generic handlers

Do not write CRUD by hand. `mcp/tools.py` provides factories that already
implement scope filtering, field coercion, pagination and the error shape:

| Factory | Produces |
| --- | --- |
| `_list_handler(model, fields, search_fields, filters, scope_filtered)` | A paginated, filterable list |
| `_get_handler(model, fields, scope_filtered)` | A single record by id |
| `_create_handler(model, writable_fields, m2m_fields, ...)` | Creation |
| `_batch_create_handler(...)` | Batch creation, with `match_on` for idempotent upsert |
| `_update_handler(model, writable_fields, m2m_fields, ...)` | Partial update |
| `_delete_handler(model, scope_filtered)` | Deletion, honouring the lifecycle's deletable steps |
| `_transition_handler(model, perm_namespace, ...)` | A lifecycle transition |
| `_allowed_transitions_handler(...)` | What this record can do next, for this caller |
| `_history_handler(model, scope_filtered)` | The change trail |

Most entities get the full set, which is why the platform registers several
hundred tools rather than a curated few. That is the point : an assistant should
be able to reach anything its caller can reach.

`_list_schema()`, `_id_schema()` and `_obj_schema()` build the matching JSON
Schemas, so a filter you declare in the handler and a parameter you declare in
the schema stay in step.

## Permissions are not optional

Wrap every handler:

```python
require_perm("assets.supplier_attestation.read")(handler)
```

The check runs as the calling user and returns a refusal rather than raising.
Scope filtering is applied on top by the generic handlers, and the two are
independent : holding the permission does not widen the perimeter.

A tool with no permission wrapper is only correct when it reveals nothing by
itself. `ask_assistant` is the one such case in the codebase, and the reason is
written next to it : the routing model reveals nothing, and every data access
inside its loop goes back through the regular read tools with the caller's own
permissions.

## Writing the description

This is the part that is easy to do badly. The description and the parameter
descriptions are the model's entire interface to your tool.

- **Say what it returns, not what it is.** "List supplier attestations with
  their framework and expiry date" beats "Supplier attestation listing tool".
- **Name the filters** the caller can use, by parameter name.
- **Reproduce the enum values** for a status or type parameter, verbatim. A
  model that has to guess `in_progress` versus `in-progress` will guess wrong.
- **State the preconditions.** "Requires the optional AI assistant to be
  enabled" saves a failed call.
- **Point at the specification** when the semantics are non-obvious, the way the
  compliance tools point at the requirement spec for the eleven-value status
  enum.

## Lifecycle tools

Never expose a tool that writes `workflow_state`. Expose the transition instead:

```python
server.register_tool(
    "supplier_attestation_transition",
    "Move a supplier attestation to a target lifecycle state. Use "
    "supplier_attestation_allowed_transitions first to see what is possible "
    "for the current user and state.",
    ...,
    _transition_handler(SupplierAttestation, "assets.supplier_attestation"),
)
```

Pair it with the `allowed_transitions` tool. Without it a model has to try a
transition to discover it is not permitted, which turns a governance gate into
a guessing game.

## Registering

Add the tool to its module's `_register_<module>_tools(server)`. If the module
is new, add the function and call it from `register_all_tools`. A tool that is
defined but never registered fails silently : it simply does not exist, and
nothing tells you.

## Regenerate and test

```bash
python manage.py generate_docs
```

Tests belong in `mcp/tests/`. Cover: the tool is registered under the expected
name; a caller without the permission is refused; a caller outside the scope
gets nothing; and, for a transition tool, that the gate is enforced rather than
reported.

```python
def test_tool_is_registered():
    server = McpServer()
    register_all_tools(server)
    assert server.get_tool("list_supplier_attestations") is not None
```

## Checklist

- [ ] Registered in the module's `_register_*_tools`, which is called from `register_all_tools`
- [ ] Built on a generic handler rather than hand-rolled CRUD
- [ ] Wrapped in `require_perm`, or the exemption justified in a comment
- [ ] Scope filtering on, or the exemption stated
- [ ] Description says what it returns and names its filters
- [ ] Enum values reproduced verbatim in the parameter descriptions
- [ ] Transition exposed as a transition, with its `allowed_transitions` companion
- [ ] Matching [REST endpoint](rest-endpoint.md) added
- [ ] `generate_docs` re-run and committed
- [ ] Tests cover registration, permission and tenancy
