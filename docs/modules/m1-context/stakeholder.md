# Stakeholder

`context.models.stakeholder.Stakeholder`

Représente toute personne ou organisme pouvant affecter, être affecté ou se sentir affecté par une décision ou une activité.

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-généré | Identifiant unique |
| `scope_id` | relation | FK → Scope, requis | Périmètre rattaché |
| `name` | string | requis, max 255 | Nom de la partie intéressée |
| `type` | enum | requis | `internal`, `external` |
| `category` | enum | requis | Voir liste ci-dessous |
| `description` | text | optionnel | Description |
| `contact_name` | string | optionnel | Nom du contact principal |
| `contact_email` | string | optionnel, format email | Email du contact |
| `contact_phone` | string | optionnel | Téléphone du contact |
| `influence_level` | enum | requis | `low`, `medium`, `high` |
| `interest_level` | enum | requis | `low`, `medium`, `high` |
| `expectations` | relation | O2M → StakeholderExpectation | Attentes et exigences |
| `related_issues` | relation | M2M → Issue | Enjeux associés |
| `status` | enum | requis | `active`, `inactive` |
| `review_date` | date | optionnel | Prochaine date de revue |
| `created_by` | relation | FK → User | Créateur |
| `created_at` | datetime | auto | Date de création |
| `updated_at` | datetime | auto | Date de dernière modification |

**Catégories de parties intéressées (valeurs de `category`) :**

`executive_management`, `employees`, `customers`, `suppliers`, `partners`, `regulators`, `shareholders`, `insurers`, `public`, `competitors`, `unions`, `auditors`, `other`

> Note : Les catégories doivent être paramétrables par l'administrateur.

## StakeholderExpectation

Sous-entité : attente d'une partie intéressée.

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-généré | Identifiant unique |
| `stakeholder_id` | relation | FK → Stakeholder, requis | Partie intéressée parente |
| `description` | text | requis | Description de l'attente ou exigence |
| `type` | enum | requis | `requirement`, `expectation`, `need` |
| `priority` | enum | requis | `low`, `medium`, `high`, `critical` |
| `is_applicable` | boolean | requis, défaut true | Applicable au périmètre |
| `linked_requirements` | relation | M2M → Requirement | Exigences de conformité liées (module Conformité) |
| `created_at` | datetime | auto | Date de création |
| `updated_at` | datetime | auto | Date de dernière modification |
