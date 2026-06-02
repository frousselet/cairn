# RequirementMapping

`compliance.models.mapping.RequirementMapping`

Correspondance entre deux [Requirements](requirement.md) de référentiels différents.

## Entité : RequirementMapping (Mapping inter-référentiels)

Représente une correspondance entre deux exigences de référentiels différents. Permet de mutualiser les efforts de conformité et de visualiser les recouvrements.

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-généré | Identifiant unique |
| `source_requirement_id` | relation | FK → Requirement, requis | Exigence source |
| `target_requirement_id` | relation | FK → Requirement, requis | Exigence cible |
| `mapping_type` | enum | requis | `equivalent`, `partial_overlap`, `includes`, `included_by`, `related` |
| `coverage_level` | enum | optionnel | `full`, `partial`, `minimal` |
| `description` | text | optionnel | Description de la correspondance |
| `justification` | text | optionnel | Justification du mapping |
| `created_by` | relation | FK → User | Créateur |
| `created_at` | datetime | auto | Date de création |
| `updated_at` | datetime | auto | Date de dernière modification |

> Contrainte d'unicité : le couple (`source_requirement_id`, `target_requirement_id`) doit être unique.
> Contrainte : `source_requirement_id` et `target_requirement_id` doivent appartenir à des référentiels différents.

**Types de mapping :**

| Type | Description |
|---|---|
| `equivalent` | Les deux exigences sont équivalentes (couverture mutuelle) |
| `partial_overlap` | Les exigences se recouvrent partiellement |
| `includes` | L'exigence source inclut / couvre l'exigence cible |
| `included_by` | L'exigence source est incluse / couverte par l'exigence cible |
| `related` | Les exigences sont liées sans recouvrement direct |
