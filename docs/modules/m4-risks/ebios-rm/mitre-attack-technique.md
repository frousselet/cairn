# MitreAttackTechnique

`risks.models.ebios.mitre_attack.MitreAttackTechnique`

Catalogue référentiel MITRE ATT&CK Enterprise Matrix. Seedé via fixture `risks/fixtures/mitre_attack_v15.json` lors de l'installation, mis à jour par la commande `python manage.py refresh_mitre_attack`. Pas de préfixe interne : la clé naturelle est `mitre_id`.

## 4.4.3 Entité : MitreAttackTechnique (Catalogue)

Catalogue référentiel MITRE ATT&CK Enterprise Matrix. Seedé via fixture `risks/fixtures/mitre_attack_v15.json` lors de l'installation, mis à jour par la commande `python manage.py refresh_mitre_attack`.

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| `id` | UUID | PK, auto | Identifiant unique |
| `mitre_id` | string | requis, unique | Identifiant MITRE (ex. T1566, T1566.001) |
| `name` | string | requis, max 255 | Nom |
| `description` | text | requis | Description |
| `tactic` | enum | requis | `reconnaissance`, `resource_development`, `initial_access`, `execution`, `persistence`, `privilege_escalation`, `defense_evasion`, `credential_access`, `discovery`, `lateral_movement`, `collection`, `command_and_control`, `exfiltration`, `impact` |
| `parent_technique_id` | relation | FK -> self, optionnel | Technique parente (sous-techniques) |
| `version` | string | requis, max 16 | Version MITRE (ex. 15.1) |
| `url` | string | optionnel, max 500 | Lien vers la fiche MITRE |
| `is_active` | boolean | requis, défaut true | Désactivable si retirée de MITRE |
| `created_at`, `updated_at` | - | auto | Standards |
