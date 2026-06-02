# AttackPathStep

`risks.models.ebios.attack_path_step.AttackPathStep`

Étape unitaire du chemin d'attaque d'un scénario stratégique. Préfixe de référence : `EAPS`.

## 4.3.3 Entité : AttackPathStep (Étape du chemin d'attaque)

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| `id` | UUID | PK, auto | Identifiant unique |
| `scenario_id` | relation | FK -> [StrategicScenario](strategic-scenario.md), requis | Scénario parent |
| `reference` | string | requis, unique, préfixe EAPS | Code (ex. EAPS-1) |
| `order` | integer | requis | Position dans le chemin (1 = première étape) |
| `stakeholder_id` | relation | FK -> [EcosystemStakeholder](ecosystem-stakeholder.md), optionnel | Partie prenante impliquée |
| `description` | text | requis | Description |
| `action_type` | enum | requis | `initial_access`, `reconnaissance`, `lateral_movement`, `privilege_escalation`, `data_exfiltration`, `disruption`, `manipulation`, `persistence`, `other` |
| `difficulty` | enum | optionnel | `trivial`, `easy`, `moderate`, `difficult`, `very_difficult` |
| `created_at`, `updated_at` | - | auto | Standards |
