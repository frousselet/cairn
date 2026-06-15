# DocumentRequest

`trust_center.models.document_request.DocumentRequest`

An external request for a **gated** Trust Center document. A visitor who wants a gated artifact (typically an NDA-restricted audit report or SOC 2 report) submits a short form; a curator reviews it; on approval the system issues a **time-limited, signed download link** so the requester can fetch the document without an account. This keeps sensitive artifacts off the open page while still letting prospects self-serve through an auditable approval step.

File: `trust_center/models/document_request.py`

`BaseModel` subclass : UUID PK, sequential `reference` (prefix **`DREQ`**, e.g. `DREQ-1`), `django-simple-history` audit trail, and the `trust_center_document_request` lifecycle workflow. Its `workflow_state` overrides the `BaseModel` default to start in `pending`.

## Fields

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-generated | Unique identifier |
| `reference` | string | auto `DREQ-N`, unique | Business reference |
| `document` | relation | FK -> `TrustCenterDocument`, `PROTECT`, required | The gated document being requested. `related_name="requests"`. |
| `email` | email | required | Requester email (where the signed link is sent) |
| `requester_name` | string | required, max 255 | Requester name |
| `company` | string | optional, max 255, blank default | Requester organization |
| `reason` | text | optional, blank default | Why access is requested (free text) |
| `nda_accepted` | boolean | required, default `False` | Whether the requester accepted the NDA terms. Required on submission when the document's `requires_nda` is on. |
| `nda_accepted_at` | datetime | optional | When the requester accepted the NDA (stamped on submission if `nda_accepted`). |
| `ip_address` | IP | optional | Requester IP captured at submission (audit / abuse tracing). |
| `user_agent` | text | optional, blank default | Requester user agent captured at submission (truncated). |
| `workflow_state` | string | indexed, default `pending` | Lifecycle state (`trust_center_document_request`) |
| `reviewed_by` | relation | FK -> User, `SET_NULL`, optional | Curator who approved / rejected the request. `related_name="reviewed_document_requests"`. |
| `reviewed_at` | datetime | optional | When the request was approved / rejected |
| `decision_note` | text | optional, blank default | Curator note recorded with the decision (the rejection / revoke comment). |
| `download_token_issued_at` | datetime | optional | When the signed download link was issued (set on approval). |
| `download_link_expires_at` | datetime | optional | Indicative expiry of the issued link (issue time + `TRUST_CENTER_DOWNLOAD_TTL`). The hard expiry is enforced by the signed-token max age, not this field. |
| `download_count` | int | `PositiveIntegerField`, default `0` | How many times the gated link has been used to stream the document. |
| `created_at` / `updated_at` | datetime | auto | Timestamps |

## Lifecycle

Runs the dedicated `trust_center_document_request` workflow (declared from transition constants in `trust_center/constants.py` and registered from `TrustCenterConfig.ready()`):

```
pending ─► approved ─► rejected (revoke access)
   │
   └─► rejected (decline)
```

| State | In reports | Deletable | Branch | Description |
|---|---|---|---|---|
| `pending` (initial) | no | **yes** | no | Submitted, awaiting curator review |
| `approved` | **yes** | no | no | Approved; a signed, time-limited download link has been issued |
| `rejected` (terminal) | no | no | **yes** | Declined by a curator, or a previously approved request whose access was revoked |

There is **no separate `expired` or `revoked` state**. Revoking a granted request reuses the `approved -> rejected` transition, and link expiry is enforced purely by the signed-token max age (`TRUST_CENTER_DOWNLOAD_TTL`), not a workflow state. Badge tones are `warning` (pending), `success` (approved), `danger` (rejected).

| Verb | Transition | Permission action | Comment |
|---|---|---|---|
| Approve | `pending -> approved` | `approve` | optional |
| Reject | `pending -> rejected` | `approve` | **required** (`requires_comment`) |
| Revoke access | `approved -> rejected` | `approve` | **required** (`requires_comment`) |

`is_granted` is a convenience property returning `True` only while the request is in the `approved` state; the gated download view uses it so a revoke (which moves the request back to `rejected`) kills the link immediately, even before the token's TTL elapses.

## Signed download links

The token is a `django.core.signing.TimestampSigner` signature (salt `"trust_center.document_request.download"`) over the request UUID. It is **never stored** : it is recomputed on approval and verified statelessly on each fetch. Helpers on the model:

- `make_download_token()` : sign the request PK and return the token.
- `resolve_token(token, max_age)` (classmethod) : verify signature and age, returning the matching request (or `None`). It propagates `signing.SignatureExpired` / `signing.BadSignature` so the caller can distinguish an expired link from a tampered one.
- `issue_download_link(ttl_seconds)` : stamp `download_token_issued_at` / `download_link_expires_at` and return a fresh signed token.

On approval (via the management stepper or MCP), `issue_download_link(TRUST_CENTER_DOWNLOAD_TTL)` is called and the resulting URL is emailed to the requester, so:

- the document bytes are still streamed through a view (never exposed under `/media/`),
- the link stops working after the TTL (`resolve_token` raises `SignatureExpired`, and the gated download view renders a 410 "link expired" page),
- a curator can revoke access before expiry (the `approved -> rejected` transition flips `is_granted` to false, and the view 404s the link).

## Request and download flow

1. A visitor opens the public request form at `/trust/documents/<uuid>/request/` (`DocumentRequestCreateView` + `PublicDocumentRequestForm`). The form has a honeypot field, requires NDA acceptance when the document's `requires_nda` is on, and the view applies a cache-based per-IP rate limit and de-duplicates pending requests per `(email, document)` (returning the same confirmation either way, so it never leaks which emails already requested access).
2. On submit, a `pending` `DocumentRequest` is created, the IP and user agent are captured, and `accounts.notifications.notify_document_requested` fires an in-app notification plus an email (`NotificationType.TRUST_DOCUMENT_REQUESTED`) to the holders of `trust_center.document_request.approve`.
3. A curator reviews the request on the 2-column detail page at `/trust-center/manage/requests/<uuid>/` and acts through the **generic workflow stepper**. The bespoke transition endpoint (`trust_center_manage:request-transition`) stamps `reviewed_by` / `reviewed_at` (and `decision_note` from the comment); on approve it calls `issue_download_link` and emails the requester via `trust_center/notifications.py` `send_gated_link_email`.
4. The requester fetches the document at `/trust/documents/download/<token>/` (`TrustCenterGatedDownloadView`): the view validates the `TimestampSigner` token (404 on `BadSignature`, a 410 "link expired" page on `SignatureExpired`), requires the request to still be in the `approved` state (so a revoke kills the link even before expiry), increments `download_count`, and streams the bytes.

## Business rules

| ID | Rule |
|---|---|
| RG-TC-22 | A `DocumentRequest` may only target a document whose `access = gated`. Public documents are downloaded directly and need no request (the public request form 404s a non-gated document). |
| RG-TC-23 | When the target document's `requires_nda` is on, NDA acceptance is required to submit the request (`nda_accepted` is stamped with `nda_accepted_at`). |
| RG-TC-24 | Approval issues a signed, time-limited link (`TRUST_CENTER_DOWNLOAD_TTL`); the bytes are streamed through a view, never via `/media/`. Expiry is enforced by the signed-token max age; revocation reuses `approved -> rejected`. |
| RG-TC-25 | A new request submission notifies the holders of `trust_center.document_request.approve` (in-app + email); an approval emails the requester the signed link. |

## Endpoints

### Public

- `GET/POST /trust/documents/<uuid>/request/` : the public request form for a gated document (`DocumentRequestCreateView`, unauthenticated, honeypot + per-IP rate limiting + pending dedupe; 404s when the global switch is off or the document is not gated).
- `GET /trust/documents/download/<token>/` : fetch an approved gated document via the signed link (`TrustCenterGatedDownloadView`; signature + TTL verified, `approved` state required, `download_count` incremented).

### REST (management, authenticated, `/api/v1/trust-center/`)

There is no management REST viewset for requests : review happens through the curation UI (the workflow stepper) and through MCP. The detail / transition surface lives under `/trust-center/manage/requests/<uuid>/` (web UI).

### MCP

- `list_trust_center_document_requests` : list requests (optional `workflow_state` filter). Requires `trust_center.document_request.read`.
- `get_trust_center_document_request` : read one request. Requires `trust_center.document_request.read`.
- `approve_trust_center_document_request` : approve a request : issues the time-limited signed link and emails it to the requester. Requires `trust_center.document_request.approve`.
- `reject_trust_center_document_request` : reject a pending request, or revoke access for an approved one (comment required). Requires `trust_center.document_request.approve`.

There is **no create / update / delete via MCP** : requests originate from the public form, not from authenticated clients.

## Permissions

| Codename | Description |
|---|---|
| `trust_center.document_request.read` | List / read gated-document requests |
| `trust_center.document_request.approve` | Approve / reject / revoke a request |
| `trust_center.document_request.delete` | Delete a request |

These three actions are present in `PERMISSION_REGISTRY` and are assigned to Super Admin / Admin (all), RSSI/DPO and Contributeur (read; approve for RSSI/DPO), Auditeur / Lecteur (read only), per `accounts/migrations/0042_add_trust_center_permissions.py`. There is **no `create`** action : requests are created by anonymous visitors through the public form, not by authenticated users.

## References

- [TrustCenterDocument](document.md) : the gated source of a request (`access = gated`, `requires_nda`).
- [README.md](README.md) : §6.3 (no raw file exposure), §8 (notifications), §9.2 (`TRUST_CENTER_DOWNLOAD_TTL`).
- [governance/workflow.md](../governance/workflow.md) : the lifecycle framework this workflow plugs into.
