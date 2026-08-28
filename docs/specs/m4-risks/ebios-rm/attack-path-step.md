# AttackPathStep

`risks.models.ebios.attack_path_step.AttackPathStep`

Individual step of the attack path of a strategic scenario. Reference prefix: `EAPS`.

## 4.3.3 Entity: AttackPathStep (Attack path step)

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK, auto | Unique identifier |
| `scenario_id` | relation | FK -> [StrategicScenario](strategic-scenario.md), required | Parent scenario |
| `reference` | string | required, unique, prefix EAPS | Code (e.g. EAPS-1) |
| `order` | integer | required | Position in the path (1 = first step) |
| `stakeholder_id` | relation | FK -> [EcosystemStakeholder](ecosystem-stakeholder.md), optional | Stakeholder involved |
| `description` | text | required | Description |
| `action_type` | enum | required | `initial_access`, `reconnaissance`, `lateral_movement`, `privilege_escalation`, `data_exfiltration`, `disruption`, `manipulation`, `persistence`, `other` |
| `difficulty` | enum | optional | `trivial`, `easy`, `moderate`, `difficult`, `very_difficult` |
| `created_at`, `updated_at` | - | auto | Standard |
