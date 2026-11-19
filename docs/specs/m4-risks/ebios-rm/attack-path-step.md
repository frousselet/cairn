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

## Creation and edition

A step is a row of its strategic scenario, on the page of workshop 3 (see [README, 8.6](README.md)).

- **Creation** asks for four fields on one screen : the action type (a decision, the select opens on *Choose...*), the difficulty, the ecosystem stakeholder the attacker passes through, among those of the same study, and the description. The scenario is known from the address. `order` is not asked : a new step comes last (`AttackPathStep.come_last_when_unranked`, used by the form and by `create_ebios_attack_path_step`).
- **Edition** adds the rank. The uniqueness of `(scenario, order)` is checked by the form, which says so : it used to be refused by the database, as a server error.

