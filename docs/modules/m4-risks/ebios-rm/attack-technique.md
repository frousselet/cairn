# AttackTechnique

`risks.models.ebios.attack_technique.AttackTechnique`

Attack technique used in an operational scenario, optionally linked to the MITRE ATT&CK catalog. Reference prefix: `EATT`.

## 4.4.2 Entity: AttackTechnique (Attack technique)

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK, auto | Unique identifier |
| `scenario_id` | relation | FK -> [OperationalScenario](operational-scenario.md), required | Parent scenario |
| `reference` | string | required, unique, prefix EATT | Code (e.g. EATT-1) |
| `order` | integer | required | Position in the sequence |
| `mitre_technique_id` | relation | FK -> [MitreAttackTechnique](mitre-attack-technique.md), optional | Referenced MITRE technique |
| `custom_name` | string | optional, max 255 | Free-text name when there is no MITRE mapping |
| `description` | text | required | Description |
| `targeted_support_asset_id` | relation | FK -> SupportAsset, optional | Targeted support asset |
| `difficulty` | enum | optional | `trivial`, `easy`, `moderate`, `difficult`, `very_difficult` |
| `detection_difficulty` | enum | optional | `trivial`, `easy`, `moderate`, `difficult`, `very_difficult` |
| `created_at`, `updated_at` | - | auto | Standard |

> At least one of the two fields `mitre_technique_id` or `custom_name` is required (application-level constraint).
