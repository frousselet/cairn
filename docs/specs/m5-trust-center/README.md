# Module 5 : Trust Center

## Functional and technical specification

**Version:** 1.0
**Date:** 15 June 2026
**Status:** Draft

Django app: `trust_center/`.

---

## Entities

- [TrustCenterSettings](trust-center-settings.md) : `trust_center.models.settings.TrustCenterSettings` (singleton)
- [TrustCenterCertification](certification.md) : `trust_center.models.certification.TrustCenterCertification`
- [TrustCenterSubprocessor](subprocessor.md) : `trust_center.models.subprocessor.TrustCenterSubprocessor`
- [TrustCenterMeasure](measure.md) : `trust_center.models.measure.TrustCenterMeasure`
- [TrustCenterDocument](document.md) : `trust_center.models.document.TrustCenterDocument`
- [DocumentRequest](document-request.md) : `trust_center.models.document_request.DocumentRequest`

---

## 1. Overview

### 1.1 Purpose

The **Trust Center** is a public, unauthenticated page that advertises the organization's security and compliance posture to prospects, customers, auditors and partners, without requiring them to log in or to sign an NDA up front. It is the externally facing counterpart of the internal GRC work captured in the compliance, assets and reports modules: certifications held, subprocessors used, security measures in place and shareable documents (policies, certificates, audit reports).

The module is built as a **curation layer**, not as a window onto the internal database. Each public item is a small "link" object that references one internal object (a `Framework`, a `Supplier`, a `Report`) through a `PROTECT` foreign key and carries its own public-only fields (a public label, a public description, a curated country, etc.). The curator decides explicitly what becomes public and how it is worded. Internal GRC data (contacts, contracts, criticality, owners, scopes, notes, internal identifiers, raw files) never reaches the public surface.

### 1.2 Functional scope

The module covers:

1. A single public configuration object (the [Trust Center settings](trust-center-settings.md)) with a master publication switch and presentation options.
2. Public **certifications** : a curated view of internal compliance frameworks, optionally showing a rounded compliance percentage.
3. Public **subprocessors** : a curated view of internal suppliers acting as data subprocessors (GDPR Art. 28 transparency).
4. Public **measures** : free-form curator copy describing organizational, technical and physical security measures.
5. Public **documents** : downloadable artifacts sourced either from a generated internal report or from an inline uploaded file, served either openly (public) or behind a request-and-approval flow (gated).
6. **Document requests** : the request, approval and time-limited download workflow for gated documents.

### 1.3 Dependencies on other modules

| Target module | Nature of the dependency |
|---|---|
| Compliance | A [certification](certification.md) references a `compliance.Framework`. Its public compliance percentage is read from `Framework.compliance_level`. The framework's lifecycle state gates publication (see §2.2). |
| Assets (suppliers) | A [subprocessor](subprocessor.md) references an `assets.Supplier`. The supplier's lifecycle state and `status` gate publication. |
| Reports | A [document](document.md) may reference a `reports.Report` as its source. The report's `status` gates publication. |
| Accounts (company settings) | The public page reads the organization name and logo from `accounts.CompanySettings` (the logo is SVG-sanitized before rendering). |
| Governance (lifecycle) | Every curation entity runs the `trust_center_publication` lifecycle workflow (see [governance/workflow.md](../governance/workflow.md)). |

The dependency direction is one-way: the Trust Center reads from the GRC modules; no GRC module depends on the Trust Center. Deleting a Trust Center entry never affects the internal object it references, and the `PROTECT` foreign keys prevent an internal object that is still surfaced from being hard-deleted out from under a public link.

---

## 2. Business rules

### 2.1 General rules

| ID | Rule |
|---|---|
| RG-TC-01 | The Trust Center is a **curation layer**. A public entity references at most one internal object and exposes only its own public-only fields plus a hardcoded projection of that source. Internal serializers are never reused on the public surface (see §6). |
| RG-TC-02 | The references to internal objects use `on_delete=PROTECT`. An internal `Framework`, `Supplier` or `Report` that is still referenced by a Trust Center entry cannot be hard-deleted; it must be archived / unpublished first. |
| RG-TC-03 | Each curation entity (`TrustCenterCertification`, `TrustCenterSubprocessor`, `TrustCenterMeasure`, `TrustCenterDocument`) is a `BaseModel` subclass : UUID PK, sequential `reference`, `django-simple-history` audit trail, and the lifecycle workflow described in §2.2. |
| RG-TC-04 | The `created_at` and `updated_at` fields are managed automatically by the system. |
| RG-TC-05 | `display_order` (a `PositiveIntegerField`, default `0`) controls the rendering order within each section, then the entity falls back to its own natural ordering (label / name / title). |
| RG-TC-06 | The settings object ([TrustCenterSettings](trust-center-settings.md)) is a **singleton**, like `accounts.CompanySettings`. It is accessed via `TrustCenterSettings.get()` and its `save()` override enforces a single row. |

### 2.2 Publication lifecycle and the dual gate

Going live is governed by **two independent conditions plus a global switch**. This is the core safety property of the module.

| ID | Rule |
|---|---|
| RG-TC-07 | **Per-item state.** Each curation entity runs the `trust_center_publication` workflow : `draft` (initial) -> `published` <-> `unpublished` -> `archived` (terminal branch). Only the `published` state has `counts_in_reports = True`, which here means "live on the public page". See [governance/workflow.md](../governance/workflow.md) and §2.3 below. |
| RG-TC-08 | **Source validity (the second gate).** Beyond being `published`, the entry is only shown when its **source object is still valid** : the framework must be in a reportable lifecycle state; the supplier must be in a reportable lifecycle state AND have `status = active`; a report-backed document's report must be `completed` (an inline-file document has no report, so this clause is satisfied). Implemented in `trust_center/managers.py` via the `published()` queryset, which the public views and serializers use exclusively. |
| RG-TC-09 | Because of RG-TC-08, **un-validating, archiving or deactivating a source object automatically removes the corresponding entry from the public page** without any edit to the Trust Center entity. Re-validating the source restores it (the entry's own state is unchanged). |
| RG-TC-10 | **Global kill switch.** `TrustCenterSettings.is_published` is the master switch. When it is `False`, the entire public surface (the page, every public API endpoint, every public document download) returns **HTTP 404** for everyone. This is enforced at the view / serializer layer (`require_published()`), separately from the per-entity dual gate, so the managers stay pure and testable. |
| RG-TC-11 | Publishing or unpublishing an entry (the `draft -> published`, `published -> unpublished`, `unpublished -> published`, `published -> archived` transitions) requires the **`approve`** permission action : only roles allowed to publish (RSSI/DPO, Admin, Super Admin) can make an item live or take it down. Archiving an entry that is still a draft / unpublished is a plain **`update`**. |

The dual gate means the public surface is correct by construction: an item appears only when a curator has explicitly published it AND the underlying internal evidence is still valid AND the whole center is switched on. No single mistake (a stale link, a deactivated supplier, a forgotten kill switch) can leak data.

### 2.3 The `trust_center_publication` workflow

Shared by certifications, subprocessors, measures and documents. Declared from transition constants (single source of truth) in `trust_center/constants.py` and registered from `TrustCenterConfig.ready()`.

| State | In reports (= live) | Linkable | Deletable | Branch | Initial | Terminal |
|---|---|---|---|---|---|---|
| `draft` | no | no | **yes** | no | **yes** | yes |
| `published` | **yes** | no | no | no | no | no |
| `unpublished` | no | no | **yes** | no | no | no |
| `archived` | no | no | no | **yes** | no | **yes** |

| Verb | Transition | Permission action |
|---|---|---|
| Publish | `draft -> published` | `approve` |
| Archive | `draft -> archived` | `update` |
| Unpublish | `published -> unpublished` | `approve` |
| Archive | `published -> archived` | `approve` |
| Publish | `unpublished -> published` | `approve` |
| Archive | `unpublished -> archived` | `update` |

Notes:

- `draft` and `archived` are both terminal-capable in the workflow declaration (a draft can be archived directly, and `archived` is the permanent off-ramp). The live state is `published` only.
- The workflow does **not** subsume the approval axis : these entities are pure publication objects. The visual badge tones are `secondary` (draft), `success` (published), `warning` (unpublished) and `dark` (archived).
- Curation entities are never `linkable` targets : nothing inside the GRC platform links *to* a Trust Center entry, so no state is marked linkable.

### 2.4 Certification rules

| ID | Rule |
|---|---|
| RG-TC-12 | A certification's public compliance percentage (`public_compliance_level`) is shown only when **both** toggles are on : the per-item `show_percentage` AND the global `TrustCenterSettings.show_compliance_percentages`. Otherwise the property returns `None` and no number is rendered. |
| RG-TC-13 | The percentage is the rounded integer of `Framework.compliance_level`. A non-numeric or missing value yields `None` (no number rendered), never an error. |

### 2.5 Subprocessor rules

| ID | Rule |
|---|---|
| RG-TC-14 | A subprocessor is shown publicly only when its supplier is in a reportable lifecycle state **and** `Supplier.status = active` (RG-TC-08). A suspended, under-evaluation or archived supplier disappears from the public list automatically. |
| RG-TC-15 | The subprocessor exposes only `public_name`, `purpose`, `public_country`, `public_website` and the supplier logo. Internal supplier fields (contacts, contracts, criticality, owner, notes, internal references) are never exposed. |

### 2.6 Measure rules

| ID | Rule |
|---|---|
| RG-TC-16 | A measure is free-form curator copy with **no link to internal data**, so nothing sensitive can leak through it. Only the base publication gate (state `published`) plus the global switch apply. |
| RG-TC-17 | `icon` must be a Bootstrap Icons name (validated against `^bi-[a-z0-9-]+$`), consistent with the brand iconography rule. `category` is one of `organizational`, `technical`, `physical`. |

### 2.7 Document rules

| ID | Rule |
|---|---|
| RG-TC-18 | A document's source is **exactly one** of : a linked `reports.Report`, or inline bytes (`file_content` + `file_name` + `content_type`). Providing both or neither is rejected in `clean()`. |
| RG-TC-19 | `access` is `public` or `gated`. A **public** document downloads directly through a streaming view. A **gated** document is not downloadable directly; it requires a [document request](document-request.md) and curator approval. |
| RG-TC-20 | Files are never exposed under `/media/`. Bytes are streamed through `TrustCenterPublicDocumentDownloadView` (public docs) or, for gated docs, through a signed, time-limited link issued after approval and served by `TrustCenterGatedDownloadView`. `file_content` is excluded from the history records and is never serialized. |
| RG-TC-21 | A report-backed document is shown publicly only when its report is `completed` (RG-TC-08). `requires_nda` only has meaning for gated documents. |

---

## 3. Multi-domain exposure

The Trust Center is the one place where several internal domains are deliberately surfaced together on a single public page. The exposure is always indirect and curated:

| Public section | Internal domain | Internal object | What is exposed | What is never exposed |
|---|---|---|---|---|
| Certifications | Compliance | `Framework` | Public label, public description, rounded compliance % (if both toggles on), framework logo (sanitized) | Internal name, requirements, assessments, owner, scopes, raw `compliance_level` when toggled off |
| Subprocessors | Assets | `Supplier` | Public name, purpose, country, website, supplier logo (sanitized) | Contacts, contracts, criticality, owner, notes, internal reference |
| Measures | (none) | (none) | Curator title, description, icon, category | n/a (no internal link) |
| Documents | Reports / inline | `Report` or inline bytes | Title, description, access level, NDA flag, the file bytes (download only) | The report's internal metadata, `/media/` paths, internal identifiers other than the download id |
| Header | Accounts | `CompanySettings` | Organization name, logo (sanitized) | Everything else on `CompanySettings` |

The aggregate public payload (`GET /trust/api/`) composes all of these sections in one response, each rendered through its dedicated public serializer (§6). This is the only endpoint that crosses domains, and it does so through the same whitelisted projections used by the granular endpoints, so adding a domain to the page cannot widen the field set of any existing one.

---

## 4. API specification

Two strictly separated API families.

### 4.1 Public API (unauthenticated)

Mounted under `/trust/` (web) and `/trust/api/` (data). All endpoints are `AllowAny`, send no authentication, throttle anonymous callers (`AnonRateThrottle`), and read exclusively from the `published()` querysets and the `Public*` serializers. Every one of them first calls `require_published()` and returns **404** when the global switch is off.

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/trust/` | Server-rendered public landing page (HTML). |
| `GET` | `/trust/api/` | Aggregate JSON payload : settings, company header, certifications, subprocessors, measures, documents. |
| `GET` | `/trust/api/certifications/` | Published certifications (list, no pagination). |
| `GET` | `/trust/api/subprocessors/` | Published subprocessors. |
| `GET` | `/trust/api/measures/` | Published measures. |
| `GET` | `/trust/api/documents/` | Published documents (metadata only; bytes are fetched via the download endpoint). |
| `GET` | `/trust/documents/<uuid>/download/` | Stream a **public** document's bytes (`Content-Disposition: attachment`). Gated documents are not served here (they 404). |

The public document download is the deliberate, scoped exception to "no internal ids on the public surface" : the document UUID is the only identifier the public document serializer exposes, because it is the handle the download URL needs. It maps to nothing sensitive on its own and is still subject to the dual gate plus the `access = public` filter.

### 4.2 Management API (authenticated)

Mounted under `/api/v1/trust-center/`. All endpoints require `IsAuthenticated` + `ModulePermission` (module `trust_center`), with the per-feature permission resolved per action.

| Method | Endpoint | Description | Feature |
|---|---|---|---|
| `GET` | `/settings/` | Read the settings singleton. | `settings` (read) |
| `PUT` | `/settings/` | Update the settings singleton (partial update under the hood). | `settings` (update) |
| `GET/POST` | `/certifications/` | List / create certifications. | `certification` |
| `GET/PUT/PATCH/DELETE` | `/certifications/{id}/` | Retrieve / update / delete a certification. | `certification` |
| `POST` | `/certifications/{id}/transition/` | Run a publication-workflow transition (`target_state`, optional `comment`). | `certification` (action mapped to the transition's permission) |
| `GET/POST`, `GET/PUT/PATCH/DELETE`, `POST .../transition/` | `/subprocessors/...` | Same shape as certifications. | `subprocessor` |
| `GET/POST`, `GET/PUT/PATCH/DELETE`, `POST .../transition/` | `/measures/...` | Same shape. | `measure` |
| `GET/POST`, `GET/PUT/PATCH/DELETE`, `POST .../transition/` | `/documents/...` | Same shape. | `document` |

Conventions:

- List endpoints support search (`?search=`) and ordering (`?ordering=`) on the documented fields, and lifecycle filtering via `?workflow_state=a,b` (see [governance/workflow.md](../governance/workflow.md)).
- The `transition` action delegates to `BaseModel.transition_to(..., enforce_permission=True)` : a forbidden transition returns **403**, an invalid one **400**.
- Creating a document via the management API requires a **source report** : inline file upload is a UI-only path, so `DocumentSerializer.validate()` rejects an API create without `report` (it still honours the model's one-of invariant).
- The management serializers never expose `file_content`.

---

## 5. Permissions and access control

### 5.1 RBAC model

Module `trust_center` in `accounts/constants.py` `PERMISSION_REGISTRY`. Codenames follow the platform convention `module.feature.action`.

| Codename | Description |
|---|---|
| `trust_center.settings.read` | Read the Trust Center settings. |
| `trust_center.settings.update` | Update the Trust Center settings (including the global publish switch). |
| `trust_center.certification.create` / `.read` / `.update` / `.delete` / `.approve` | Manage certifications (`approve` = publish / unpublish / archive a published item). |
| `trust_center.subprocessor.create` / `.read` / `.update` / `.delete` / `.approve` | Manage subprocessors. |
| `trust_center.measure.create` / `.read` / `.update` / `.delete` / `.approve` | Manage measures. |
| `trust_center.document.create` / `.read` / `.update` / `.delete` / `.approve` | Manage documents. |
| `trust_center.document_request.read` / `.approve` / `.delete` | Review and approve gated-document requests. |

The public surface requires **no permission** : it is open to anonymous users by design, gated only by the global switch and the dual publication gate.

### 5.2 System group assignments

Assigned by `accounts/migrations/0042_add_trust_center_permissions.py`, mirroring the `SYSTEM_GROUPS` registry rules:

| Role | Trust Center permissions |
|---|---|
| **Super Administrateur** | All. |
| **Administrateur** | All. |
| **RSSI / DPO** | `read` + `create` + `update` + `approve` on every feature (**no `delete`**). They curate and publish, but archive rather than hard-delete (audit-grade traceability). |
| **Contributeur** | `read` + `create` + `update` (**no `approve`, no `delete`**). They prepare entries; a publisher takes them live. |
| **Auditeur** | `read` only. |
| **Lecteur** | `read` only. |

The `approve` / `delete` split encodes the editorial gate : a contributor drafts, an RSSI/DPO (or admin) publishes, and only admins can hard-delete. Combined with RG-TC-11, this means no contributor can put anything on the public internet on their own.

---

## 6. Data-leakage safety model

This is the module's most important non-functional property. The public surface is anonymous and indexable, so every layer is deny-by-default.

### 6.1 Dedicated public serializers (field whitelist)

`trust_center/api/serializers.py` keeps two strictly separated families:

- **`Public*Serializer`** (`PublicCertificationSerializer`, `PublicSubprocessorSerializer`, `PublicMeasureSerializer`, `PublicDocumentSerializer`) are plain `serializers.Serializer` subclasses that **hardcode a tiny whitelist of read-only fields**. They never use `ModelSerializer` with `fields = "__all__"` / `exclude`, and they are never reused for internal data. Adding a field to a public serializer is an explicit, reviewable act.
- **Management serializers** are the internal `ModelSerializer`s used behind authentication. They are never served on the public surface.

The whitelists, verbatim:

- Certification : `label`, `description`, `compliance_level` (nullable), `logo`.
- Subprocessor : `name`, `purpose`, `country`, `website`, `logo`.
- Measure : `title`, `description`, `icon`, `category` (display label).
- Document : `id` (download handle only), `title`, `description`, `access`, `requires_nda`.

Fields that are **never** exposed publicly include: `contact_email`, `contract_reference`, `contract_*` dates, `notes`, `criticality`, `owner` / `owners`, `scopes`, internal references and UUIDs (except the document download id), and `file_content`.

### 6.2 SVG sanitization for logos

Framework, supplier and company logos are stored as **raw SVG markup** in `TextField`s and rendered into authenticated pages today. On the public, unauthenticated page raw SVG is an XSS sink (`<script>`, `on*` handlers, `<foreignObject>`, external references). `trust_center/sanitizers.py` `clean_svg()` reconstructs the markup from a strict **allowlist** of presentation-only elements and attributes using the stdlib HTML parser (no `bleach` / `nh3` / `lxml` dependency) :

- Allowed elements are geometry / presentation only (`svg`, `g`, `path`, `rect`, gradients, `text`, etc.). Anything not listed is dropped.
- `script`, `style`, `foreignObject`, `animate*`, `set`, `image`, `iframe` and `a` are **suppressed with their entire content**.
- `on*` event attributes are stripped; `style` is dropped if it contains `url(`, `expression(`, `javascript:` or `@import`; `href` / `xlink:href` are kept only when they point inside the document (`#id`), never to an external URL.
- Output is empty unless a real `<svg>` root was seen, so a stray `<script>` with no SVG renders as the empty string.

The sanitized markup is rendered through the `{{ logo|safe_svg }}` template filter (`trust_center/templatetags/trust_center_tags.py`) and through `clean_svg()` in the public serializers / aggregate view.

### 6.3 No raw file exposure

Documents are never published under `/media/`. Public document bytes are streamed through a view that re-checks the dual gate and the `access = public` filter on every request; gated documents are only reachable through the request-and-approval flow with a signed, expiring link (`TrustCenterGatedDownloadView`, see [document-request.md](document-request.md)), which re-checks the request is still in the `approved` state on every fetch. `file_content` is excluded from `HistoricalRecords` and from every serializer.

### 6.4 Anonymous throttling and the kill switch

Public endpoints carry `AnonRateThrottle`, and the global `is_published` switch 404s the whole surface instantly. These two controls bound abuse and give the operator a single, immediate "take it all down" lever.

### 6.5 Host isolation

Optionally, the public surface can be served on a **separate domain** via the `TRUST_CENTER_HOST` environment variable plus the `TrustCenterHostMiddleware` host-isolation middleware (`trust_center/middleware.py`), wired into `MIDDLEWARE` right after `LocaleMiddleware`. When `TRUST_CENTER_HOST` is set and the request host matches it, only `/trust/`, the static URL, `/i18n/` and `/.well-known/` are reachable (the domain root `/` is rewritten to `/trust/`); everything else (the authenticated app, `/admin/`, the internal API, MCP) returns 404. When the variable is empty the middleware is a no-op and the public surface lives under `/trust/` on the main host. See §9.

---

## 7. User interface

### 7.1 Public page

- Server-rendered (`trust_center/templates/trust_center/public_landing.html`), no authentication, mobile-first, light/dark compatible per the brand guidelines.
- Header : organization name and sanitized logo (from `CompanySettings`), the configured `headline` and `intro`, the accent colour (`theme_accent`, validated hex, default navy `#1E3A8A`).
- Sections, each ordered by `display_order` : Certifications (badge grid with optional percentages), Subprocessors (table / cards with purpose and country), Measures (icon + title + description, grouped by category), Documents (list with a download button for public docs and a "request access" affordance for gated docs).
- A security contact (`contact_email`) and the NDA notice where relevant.
- When `is_published` is off, the page 404s : there is no half-published state.

### 7.2 Administration (authenticated)

- A "Trust Center" sidebar entry leads to the curation surfaces : a settings form (the singleton) and list / detail pages for certifications, subprocessors, measures and documents.
- Detail pages follow the platform 2-column card layout (content left, metadata sidebar right) and render the **generic workflow stepper** (`includes/workflow_stepper.html`) for the publication transitions; state badges use `{% workflow_badge obj %}`. Never use ad-hoc buttons or a status select for transitions.
- A **live preview** of how an entry will appear publicly helps curators write the public label / description before publishing.

---

## 8. Notifications

The publication workflow uses the generic lifecycle notification machinery (see [governance/workflow.md](../governance/workflow.md)); the publication transitions carry no `notify_owner` effect by default, so the module is quiet on routine publish / unpublish. Module-specific notifications:

| Event | Recipients | Channel |
|---|---|---|
| New gated-document request submitted (`NotificationType.TRUST_DOCUMENT_REQUESTED`, via `accounts.notifications.notify_document_requested`) | Holders of `trust_center.document_request.approve` (RSSI/DPO, Admin) | In-app, email |
| Gated-document request approved (signed download link, via `trust_center/notifications.py` `send_gated_link_email`) | The requester (external email) | Email |
| A published entry's source object was un-validated / deactivated (so the entry silently left the public page) | Optional operator alert to the entry's curator / RSSI | In-app |

---

## 9. Technical considerations

### 9.1 Architecture

- Dedicated `trust_center` Django app. Models in `trust_center/models/`, public web views in `trust_center/views.py` and public API in `trust_center/api/public_views.py`, management API in `trust_center/api/views.py`, the curation / request-review UI in `trust_center/admin_views.py` (+ `admin_urls.py`), the dual-gate querysets in `trust_center/managers.py`, the publication and document-request workflows in `trust_center/workflows.py` (+ `constants.py`), the host-isolation middleware in `trust_center/middleware.py`, the external-requester emails in `trust_center/notifications.py`, SVG sanitization in `trust_center/sanitizers.py`.
- Mounted in the root URL conf : `/trust/` (`trust_center.urls`, which includes `/trust/api/`) and `/api/v1/trust-center/` (`trust_center.api.urls`).
- The workflow is registered from `TrustCenterConfig.ready()` so it resolves before any model is used.

### 9.2 Environment variables

| Variable | Default | Purpose |
|---|---|---|
| `TRUST_CENTER_HOST` | `""` (empty = dedicated-domain mode off) | When set to the public host, the `TrustCenterHostMiddleware` restricts the public surface to that host. Defined in `core/settings.py`. |
| `TRUST_CENTER_DOWNLOAD_TTL` | `604800` (7 days, in seconds) | Lifetime of a signed gated-document download link. Defined in `core/settings.py`. |

Both variables are read in `core/settings.py`, and the middleware is wired into `MIDDLEWARE` right after `LocaleMiddleware`. As a defensive default, `core/settings.py` appends a non-empty `TRUST_CENTER_HOST` to `ALLOWED_HOSTS`; the operator must still add the host and its https origin to `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS`.

### 9.3 Singleton settings

`TrustCenterSettings` mirrors `accounts.CompanySettings` : a single row accessed via `TrustCenterSettings.get()`, with `save()` forcing reuse of the existing PK. There is no list / create of settings; only read and update.

### 9.4 History and audit trail

Every curation entity records `django-simple-history` history. `TrustCenterDocument` excludes `file_content` from its history records (large binary, never auditable as text). `TrustCenterSettings` is a plain singleton (no history).

### 9.5 Internationalization

All user-facing strings are wrapped for translation with a matching French entry in `locale/fr/LC_MESSAGES/django.po`. Several Trust Center labels (`Public`, `Published`, `Settings`, `Documents`) collide with strings used elsewhere and are disambiguated with the `trust center` `msgctxt` (`pgettext_lazy`). The public page renders in the visitor's language where content allows; curator-authored public copy is shown as entered (no machine translation).

### 9.6 Performance

- Public list endpoints are unpaginated but bounded by the dual gate and the curated nature of the data (tens of items, not thousands). They `select_related` the source object to avoid N+1 on the logo / percentage.
- The aggregate `/trust/api/` payload is a candidate for short-TTL caching keyed on the settings `updated_at` plus the latest entity change.

---

## 10. Acceptance criteria

### 10.1 Functional

- [ ] CRUD on certifications, subprocessors, measures and documents through the management API and UI.
- [ ] The publication workflow (draft / published / unpublished / archived) is enforced with the documented permission actions.
- [ ] The dual gate works : an entry is public only when `published` AND its source is valid AND the global switch is on.
- [ ] Un-validating / deactivating / archiving a source object removes the entry from the public page automatically.
- [ ] The global `is_published` switch 404s the entire public surface when off.
- [ ] Compliance percentages obey both the per-item and global toggles.
- [ ] Public documents download through the streaming view; gated documents are not directly downloadable.

### 10.2 API

- [ ] Public endpoints are `AllowAny` + throttled and use only the `Public*` serializers and `published()` querysets.
- [ ] Management endpoints enforce `ModulePermission` per feature and action.
- [ ] The transition action enforces the per-transition permission (403 / 400 on failure).

### 10.3 Security (data-leakage)

- [ ] No public serializer uses `__all__` / `exclude`; every public field is whitelisted.
- [ ] No internal-only field (`contact_email`, `contract_*`, `notes`, `criticality`, owners, scopes, internal ids, `file_content`) is reachable on the public surface.
- [ ] All logos are sanitized through `clean_svg()` / `safe_svg`; script / handler / external-ref vectors are stripped.
- [ ] No document is exposed under `/media/`; bytes are streamed through the view, re-checking the gate on every request.
- [ ] Anonymous throttling is applied to every public endpoint.

---

*End of Module 5 : Trust Center*
