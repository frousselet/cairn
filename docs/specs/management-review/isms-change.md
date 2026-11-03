# IsmsChange

`reports.models.management_review.IsmsChange`

Formalised ISMS change decided during a management review (ISO 27001:2022 clause 9.3.3 requirement on "any need for changes to the ISMS").

Clause 9.3.3 requirement : "any need for changes to the ISMS". Formalisation of the changes decided during a review.

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK | |
| `reference` | string | auto (prefix `ICHG`), unique | e.g. `ICHG-1` |
| `review` | FK → ManagementReview | required, CASCADE | Originating review |
| `change_type` | enum | required | `scope`, `policy`, `control`, `organization`, `resource`, `process`, `other` |
| `title` | string | required, max 255 | Title |
| `description` | text | required | Description of the change |
| `impact_analysis` | text | optional | Impact analysis (interested parties, risks, assets) |
| `affected_scopes` | M2M → Scope | optional | Affected scopes |
| `affected_frameworks` | M2M → Framework | optional | Affected frameworks |
| `affected_policies` | text | optional | Free-text list of policies to revise. Kept for the changes recorded before the documents register; new changes use `affected_documents`. |
| `affected_documents` | relation | M2M -> [`documents.Policy`](../m7-documents/policy.md), optional, `related_name="isms_changes"` | The governed documents this change requires to revise. The form picker offers `linkable_or_linked()` documents (active, plus the ones already linked); the REST serializer (`affected_document_ids`) and the MCP `create_isms_change` tool refuse a new link to a document that is not active (RG-DOC-20). |
| `status` | enum | required | `proposed`, `approved`, `in_progress`, `implemented`, `rejected` |
| `owner` | FK → User | required | Person responsible for implementation |
| `target_date` | date | optional | Target date |
| `implemented_at` | date | optional | Actual implementation date |
| `created_at`, `updated_at` | datetime | auto | |

**History** : `HistoricalRecords`.
