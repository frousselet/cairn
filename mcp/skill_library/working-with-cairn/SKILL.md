---
name: working-with-cairn
description: How to read and change records in Cairn, the GRC platform, through its MCP tools. Use it before the first write in a session, and whenever a call is refused, to follow the lifecycles, the permissions and the scopes the platform enforces.
---

# Working with Cairn

Cairn holds the organization's governance, risk and compliance records. Every
tool runs as the person who authorized the connection : it sees and changes
what they may, within their scopes, and nothing else.

## Before writing

1. Call `help` once, then `help(topic="...")` for the module you work on : it
   lists the writable fields of each entity and their accepted values.
2. Call `get_glossary` when the user uses a word the product does not : speak
   the names the user sees on screen.
3. Read before you write : `list_{entity}s` with `search`, then
   `get_{entity}` for the record you will change.

## Changing a record

- **Create short, complete on the record.** `create_{entity}` takes the few
  fields that identify the record; `update_{entity}` completes it.
- **A status is never written.** A record moves through its lifecycle with
  `transition_{entity}(id, target_state, comment)`. Call
  `{entity}_allowed_transitions(id)` first : it lists the steps this person
  may move to, and whether a comment is required.
- **A record is only reportable once validated.** Draft and pending records
  do not count in reports and cannot be linked.
- **Batch with care.** `batch_create_{entity}s(items, match_on)` takes up to
  500 items and is not atomic : read the status of each item in the answer.
  Pass `match_on` (for example `["name"]`) so a replay updates instead of
  duplicating.

## When the platform refuses

- *Permission denied* : this person lacks the permission. Say so; do not try
  another tool to get around it.
- *Not found* : the record does not exist or lies outside this person's
  scopes. Both read the same, on purpose.
- A deletion or a transition may ask the user to confirm or to write a
  comment. Never answer for them.
