# AttackTechnique

`risks.models.ebios.attack_technique.AttackTechnique`

Technique d'attaque utilisée dans un scénario opérationnel, optionnellement reliée au catalogue MITRE ATT&CK. Préfixe de référence : `EATT`.

## 4.4.2 Entité : AttackTechnique (Technique d'attaque)

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| `id` | UUID | PK, auto | Identifiant unique |
| `scenario_id` | relation | FK -> [OperationalScenario](operational-scenario.md), requis | Scénario parent |
| `reference` | string | requis, unique, préfixe EATT | Code (ex. EATT-1) |
| `order` | integer | requis | Position dans la séquence |
| `mitre_technique_id` | relation | FK -> [MitreAttackTechnique](mitre-attack-technique.md), optionnel | Technique MITRE référencée |
| `custom_name` | string | optionnel, max 255 | Nom libre si pas de mapping MITRE |
| `description` | text | requis | Description |
| `targeted_support_asset_id` | relation | FK -> SupportAsset, optionnel | Bien support ciblé |
| `difficulty` | enum | optionnel | `trivial`, `easy`, `moderate`, `difficult`, `very_difficult` |
| `detection_difficulty` | enum | optionnel | `trivial`, `easy`, `moderate`, `difficult`, `very_difficult` |
| `created_at`, `updated_at` | - | auto | Standards |

> Au moins un des deux champs `mitre_technique_id` ou `custom_name` est requis (contrainte applicative).
