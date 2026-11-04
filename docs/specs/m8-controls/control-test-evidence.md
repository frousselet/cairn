# ControlTestEvidence

`controls.models.evidence.ControlTestEvidence`

A file attached to a [test run](control-test-run.md) as evidence : an export, a screenshot, a signed review sheet. A write-once record once its run has left `draft` (RG-CTL-13), in the same family as `documents.PolicyAcknowledgement` : not a governed domain element, so it runs no lifecycle and carries no reference.

File: `controls/models/evidence.py`

Plain `models.Model` with a UUID PK and `django-simple-history` (`excluded_fields=["file"]`). Scopes are inherited through `run__test__control__scopes`.

## Fields

| Field | Type | Constraints | Description |
| --- | --- | --- | --- |
| `id` | UUID | PK, auto-generated | Unique identifier |
| `run` | relation | FK -> [ControlTestRun](control-test-run.md), `PROTECT` | Reverse accessor `evidence` |
| `file` | file | required, allowed extensions, max 25 MB | Stored under `control_evidence/<run id>/` |
| `original_filename` | string | max 255 | As uploaded |
| `size` | integer | | Bytes |
| `sha256` | string | 64 hex chars, not editable | Computed at upload |
| `description` | string | optional, max 255 | What the file shows |
| `uploaded_by` | relation | FK -> User, `SET_NULL` | |
| `uploaded_at` | datetime | auto | |

## Rules

- Added or deleted only while the run is in `draft`; `save()` and `delete()` refuse otherwise.
- Served only through the download view (`controls.test.read` and the control's scopes), as an attachment.
- Never serialized : the API lists `file_name`, `size`, `sha256` and `download_url`.

## References

- [ControlTestRun](control-test-run.md), [README.md](README.md) : RG-CTL-13
