# Stakeholder feedback

`context.models.stakeholder_feedback.StakeholderFeedback`

What a stakeholder tells you about your security : a survey answer, a complaint, a remark in a meeting, a finding of its own audit. Distinct from a [stakeholder](stakeholder.md) expectation, which is a lasting requirement : a feedback is one message, received on a date. The management review looks at the feedback received and how it was handled (ISO 27001:2022 clause 9.3.2.e).

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-generated | Unique identifier |
| `reference` | string | auto, prefix FBCK | Reference (e.g. FBCK-1) |
| `stakeholder_id` | relation | FK → Stakeholder, required | The stakeholder it comes from |
| `channel` | enum | required | `survey`, `meeting`, `complaint`, `email`, `audit`, `incident`, `other` |
| `received_date` | date | required | When it was received |
| `subject` | string | required, max 255 | Subject |
| `content` | text | required | What the stakeholder said or wrote |
| `sentiment` | enum | optional | `positive`, `neutral`, `negative`, `mixed` |
| `severity` | enum | optional | `low`, `medium`, `high`, `critical` |
| `status` | enum | required, default `new` | The handling : `new`, `under_review`, `addressed`, `closed`. Not the lifecycle step : it only filters the register |
| `response` | text | optional | What was answered or done |
| `linked_issues` | relation | M2M → Issue | The issues it raises or illustrates |
| `linked_expectations` | relation | M2M → StakeholderExpectation | The expectations it is about |
| `scopes` | relation | M2M → Scope | Scopes it is filed under |
| `tags` | relation | M2M → Tag | Tags |
| `workflow_state` | enum | required, default `draft` | The default lifecycle : `draft` → `pending` → `validated` → `archived` |
| `created_by`, `created_at`, `updated_at` | - | auto | Standard |

## Creation, completion, completeness

A feedback follows the [usability standard](../../sdk/usability-standard.md) : it is created short, then completed on its page.

**Creation** asks for the stakeholder, the channel, the received date, the subject, the content and the scopes (not asked with a single scope). Opened from the page of a stakeholder (`?stakeholder=<id>`), the stakeholder is not asked (rule F2); a stakeholder out of the user's scopes is not taken as the answer. The channel is a decision : the form opens on no answer (rule F8). A feedback is a fact received : nobody answers for it, the form has no owner. The user lands on the page of the new feedback.

**The page** lists what would make the record useful, then shows one card per section of its form, each with its own *Edit* : feedback (stakeholder, channel, received date, subject, content, scopes, tags), assessment (sentiment, severity) and handling (status, response, linked issues, linked expectations). The page of its stakeholder lists its feedback in a *Feedback* card, with *New feedback*.

| Requirement | Met when | Blocking |
| --- | --- | --- |
| Assess the severity | `severity` is set | no |
| Write the response | `response` is set, for a feedback whose status is `addressed` or `closed` | no |

Nothing holds its lifecycle back. The REST API returns the list in `completeness` on a single record, and the MCP `get_stakeholder_feedback` tool as well.

## Register

`/context/feedback/` lists the feedback with its reference, subject (with the stakeholder and the channel), received date, severity, handling and lifecycle step, most recent first; it is filtered by handling, channel and severity. It is a view of the *Stakeholders* entry of the *Governance* menu, beside the register of the stakeholders (a switcher leads from one to the other).

## Permissions

`context.stakeholder_feedback.read`, `.create`, `.update`, `.delete` and `.approve`. Submitting asks for `update`, validating and archiving for `approve` (held by the RSSI / DPO and the administrators, not by a contributor). Only a draft feedback can be deleted.

## REST API and MCP

- `GET|POST /api/v1/context/stakeholder-feedback/`, `GET|PATCH|DELETE /api/v1/context/stakeholder-feedback/{id}/` (a single record carries `completeness` and the read-only `workflow_state`).
- MCP : `list_stakeholder_feedback`, `get_stakeholder_feedback`, `create_stakeholder_feedback`, `update_stakeholder_feedback`, `delete_stakeholder_feedback`, `transition_stakeholder_feedback`.
