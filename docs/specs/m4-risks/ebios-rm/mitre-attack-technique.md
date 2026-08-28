# MitreAttackTechnique

`risks.models.ebios.mitre_attack.MitreAttackTechnique`

Reference catalog for the MITRE ATT&CK Enterprise Matrix. Seeded via the `risks/fixtures/mitre_attack_v15.json` fixture at installation, updated by the `python manage.py refresh_mitre_attack` command. No internal prefix: the natural key is `mitre_id`.

## 4.4.3 Entity: MitreAttackTechnique (Catalog)

Reference catalog for the MITRE ATT&CK Enterprise Matrix. Seeded via the `risks/fixtures/mitre_attack_v15.json` fixture at installation, updated by the `python manage.py refresh_mitre_attack` command.

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK, auto | Unique identifier |
| `mitre_id` | string | required, unique | MITRE identifier (e.g. T1566, T1566.001) |
| `name` | string | required, max 255 | Name |
| `description` | text | required | Description |
| `tactic` | enum | required | `reconnaissance`, `resource_development`, `initial_access`, `execution`, `persistence`, `privilege_escalation`, `defense_evasion`, `credential_access`, `discovery`, `lateral_movement`, `collection`, `command_and_control`, `exfiltration`, `impact` |
| `parent_technique_id` | relation | FK -> self, optional | Parent technique (sub-techniques) |
| `version` | string | required, max 16 | MITRE version (e.g. 15.1) |
| `url` | string | optional, max 500 | Link to the MITRE entry |
| `is_active` | boolean | required, default true | Can be deactivated if removed from MITRE |
| `created_at`, `updated_at` | - | auto | Standard |
