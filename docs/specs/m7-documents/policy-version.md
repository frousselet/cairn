# PolicyVersion

`documents.models.policy_version.PolicyVersion`

One version of a [Policy](policy.md) : its content as rich text and / or a PDF, what changed since the previous version, and who approved it and when. A version is **frozen** once submitted (RG-DOC-02), so the text that was approved is the text that stays on record; at most one version of a document is **in force** (RG-DOC-01), and the others are drafts in progress or superseded records kept for clause 7.5.3.

File: `documents/models/policy_version.py`

`BaseModel` subclass : UUID PK, sequential `reference` (prefix **`PLVR`**, e.g. `PLVR-1`), `tags`, `version` (the row's edit counter, distinct from `version_label`), `created_by`, `django-simple-history` audit trail with `excluded_fields=["file_content"]`. `LIFECYCLE_NAME = "policy_version"` (see [README §3.2](README.md#32-policy_version)). `workflow_perm_namespace = "documents.policy"` : versions are governed by the permissions of their document. Scopes are inherited through `policy__scopes` (RG-DOC-22).

## Fields

| Field | Type | Constraints | Description |
| --- | --- | --- | --- |
| `id` | UUID | PK, auto-generated | Unique identifier |
| `reference` | string | auto-generated `PLVR-N`, unique | Business reference |
| `policy` | relation | FK -> [Policy](policy.md), `CASCADE` | The document. Reverse accessor `versions`. |
| `version_label` | string | required, max 20, unique per `policy` | The published label, e.g. `1.0`, `2.3` (RG-DOC-05) |
| `content` | text | optional, HTML | The policy text, sanitized with `clean_html` on save |
| `file_content` | binary | optional, `editable=False` | The attached PDF bytes (RG-DOC-04). Never serialized, excluded from history. |
| `file_name` | string | optional, max 255 | Original PDF file name |
| `file_sha256` | string | optional, 64 hex chars, not editable | SHA-256 of `file_content`, set on upload |
| `change_summary` | text | optional; required to submit from the second version (RG-DOC-06) | What changed and why |
| `approved_by` | relation | FK -> User, `SET_NULL`, optional, not editable | Stamped by the `in_review -> in_force` transition (RG-DOC-07) |
| `approved_at` | datetime | optional, not editable | Stamped by the same transition |
| `effective_from` | date | optional; defaults to the approval date; never in the future | Date the version entered into force |
| `superseded_at` | datetime | optional, not editable | Stamped when the version leaves `in_force` (the `archived` step, labelled *Superseded*) |
| `superseded_by` | relation | FK -> self, `SET_NULL`, optional, not editable | The version that replaced it |
| `workflow_state` | string | indexed, default `draft` | `policy_version` lifecycle step |
| `tags`, `version`, `created_by`, `created_at`, `updated_at` | | | From `BaseModel` |

### Meta

- `ordering = ["policy", "-created_at"]`
- `UniqueConstraint(fields=["policy", "version_label"])`
- A partial `UniqueConstraint(fields=["policy"], condition=Q(workflow_state="in_force"), name="one_version_in_force_per_policy")` backs RG-DOC-01 at the database level.

## Computed properties and methods

- `has_pdf` : a PDF is attached.
- `get_file_bytes()` : the PDF bytes, or `None`.
- `render_pdf()` : the attached PDF, or the rich text rendered through the reports WeasyPrint pipeline (title, reference, version label, approval line, page numbers). Used by the Trust Center download and the version export.
- `is_frozen` : the step is not `draft` (RG-DOC-02).
- `previous_version` : the version this one superseded, if any.

## Validation

- `clean()` refuses any change to `content`, `file_content`, `version_label` or `change_summary` when the stored row is frozen (RG-DOC-02). The form, the serializer and the MCP update handler call it.
- Submitting (`draft -> in_review`) is refused without content (RG-DOC-03) and, from the second version, without `change_summary` (RG-DOC-06).
- `effective_from` cannot be in the future (RG-DOC-07).
- The PDF upload follows RG-DOC-04 (extension, magic bytes, 25 MB).

## Transitions

`PolicyVersion.transition_to()` is the single entry point for every version transition (the generic stepper endpoint, REST, MCP). Inside one `transaction.atomic()` block it locks the document row (`select_for_update`), checks the gates (raising `DomainRefusalError`, which every surface shows), performs the transition, and applies the side effects of [README §3.2](README.md#32-policy_version) : approval stamps, supersession of the previous version with its own recorded transition, activation of a draft document, review date recomputation, closure of the campaigns targeting the superseded version (RG-DOC-18), and the `POLICY_VERSION_IN_FORCE` notification on commit.

## Deletion

Only a `draft` version is deletable. A version that was ever submitted stays on record.

## References

- ISO/IEC 27001:2022 clause 7.5.2 (creating and updating : identification, review and approval), clause 7.5.3 (control of documented information : versions, retention of obsolete versions)
- [Policy](policy.md), [AcknowledgementCampaign](acknowledgement-campaign.md), [README.md](README.md)
- [Contract](../m2-assets/contract.md) : the PDF storage rules this entity reuses
