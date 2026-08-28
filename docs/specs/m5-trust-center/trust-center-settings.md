# TrustCenterSettings

`trust_center.models.settings.TrustCenterSettings`

Singleton holding the public Trust Center configuration : the master publication switch and the presentation options for the public page. Mirrors `accounts.CompanySettings` : a single row, accessed via `TrustCenterSettings.get()`, with the `save()` override enforcing the singleton invariant.

File: `trust_center/models/settings.py`

## Fields

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-generated | Unique identifier |
| `is_published` | boolean | required, default `False` | **Master kill switch.** When off, the entire public Trust Center (page, public API, public downloads) returns HTTP 404 for everyone. |
| `headline` | string | optional, max 255, blank default | Public page headline |
| `intro` | text | optional, blank default | Public page introduction / lead paragraph |
| `contact_email` | email | optional, blank default | Security contact shown on the public page. Curator-chosen value; never the internal owner's email. |
| `show_compliance_percentages` | boolean | required, default `True` | Global toggle for numeric compliance percentages on certifications. A certification shows a number only when this AND its own `show_percentage` are on. |
| `theme_accent` | string | max 7, optional, default `#1E3A8A` | Accent colour, validated as a hex colour (`^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$`). Defaults to the brand navy. |
| `custom_domain` | string | optional, max 255, blank default | Informational only. Actual routing on a separate domain is configured via the `TRUST_CENTER_HOST` environment variable and the host-isolation middleware, not this field. |
| `updated_at` | datetime | auto (`auto_now`) | Last modification timestamp |

## Singleton behaviour

- `TrustCenterSettings.get()` returns the single instance, creating it on first access.
- `save()` is overridden to always reuse the existing row's PK, so a second instance can never be created.
- There is no history (`HistoricalRecords`) on this model and no sequential `reference` : it is a configuration singleton, not a `BaseModel` domain entity.

## Business rules

| ID | Rule |
|---|---|
| RG-TC-06 | Singleton : exactly one row, accessed via `get()`, enforced in `save()`. |
| RG-TC-10 | `is_published` is the global kill switch. The public view layer (`require_published()` in `trust_center/api/public_views.py` and the web views) 404s the whole surface when it is `False`. This is independent of, and additional to, each entity's dual publication gate. |
| RG-TC-12 | `show_compliance_percentages` is the global half of the two-toggle rule for certification percentages (the other half is the per-item `show_percentage`). |
| RG-TC-13 | `theme_accent` must be a valid hex colour; the default is the brand navy `#1E3A8A`. |

## Endpoints

### REST (management, authenticated)

- `GET /api/v1/trust-center/settings/` : read the singleton. Requires `trust_center.settings.read`.
- `PUT /api/v1/trust-center/settings/` : update the singleton (applied as a partial update server-side). Requires `trust_center.settings.update`.

There is no create / delete : the object always exists.

### Public

The public page and aggregate payload (`GET /trust/api/`) read a **whitelisted projection** of the settings (`headline`, `intro`, `contact_email`, `theme_accent`, `show_compliance_percentages`) plus the company name and sanitized logo. `is_published` and `custom_domain` are not echoed to the public client; `is_published` simply governs whether the surface responds at all.

### MCP

- `get_trust_center_settings` : read the singleton. Requires `trust_center.settings.read`.
- `update_trust_center_settings` : update the singleton. Requires `trust_center.settings.update`.

## Permissions

| Codename | Description |
|---|---|
| `trust_center.settings.read` | Read the Trust Center settings |
| `trust_center.settings.update` | Update the Trust Center settings (including the global publish switch) |

## References

- `accounts.CompanySettings` : the sibling singleton pattern this model mirrors; the public header reads the company name and logo from it.
- [README.md](README.md) : §2.2 (the dual gate and the global switch), §6 (data-leakage safety).
- [Certification](certification.md) : `show_compliance_percentages` gates the percentage together with the certification's own `show_percentage`.
