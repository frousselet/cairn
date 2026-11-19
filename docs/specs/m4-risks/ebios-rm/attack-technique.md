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

## Creation and edition

An attack technique is a row of its operational scenario, on the page of workshop 4 (see [README, 8.7](README.md)).

- **Creation** asks for five fields on one screen : the MITRE technique, listed under its tactic among the active entries of the catalogue, or a custom name when none fits (one of the two, rule RE-13), the description, the targeted support asset, among those the scenario aims at, and the difficulty. The scenario is known from the address. `order` is not asked : a new technique comes last (`RankedInParent.come_last_when_unranked`, used by the form and by `create_ebios_attack_technique`).
- **Edition** adds the detection difficulty and the rank. The uniqueness of `(scenario, order)` is checked by the form, which says so.
- Saving a technique that names a MITRE entry records the version of the catalogue on its scenario when it has none (`mitre_version`).

