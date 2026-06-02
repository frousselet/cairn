# Objective

`context.models.objective.Objective`

Représente un objectif de sécurité de l'information ou de conformité.

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-généré | Identifiant unique |
| `scope_id` | relation | FK → Scope, requis | Périmètre rattaché |
| `reference` | string | requis, unique | Code de référence (ex. OBJ-001) |
| `name` | string | requis, max 255 | Intitulé de l'objectif |
| `description` | text | optionnel | Description détaillée |
| `category` | enum | requis | `confidentiality`, `integrity`, `availability`, `compliance`, `operational`, `strategic` |
| `type` | enum | requis | `security`, `compliance`, `business`, `other` |
| `target_value` | string | optionnel | Valeur cible mesurable |
| `current_value` | string | optionnel | Valeur actuelle |
| `unit` | string | optionnel | Unité de mesure |
| `measurement_method` | text | optionnel | Méthode de mesure |
| `measurement_frequency` | enum | optionnel | `monthly`, `quarterly`, `semi_annual`, `annual` |
| `target_date` | date | optionnel | Date cible d'atteinte |
| `owner_id` | relation | FK → User, requis | Responsable de l'objectif |
| `status` | enum | requis | `draft`, `active`, `achieved`, `not_achieved`, `cancelled` |
| `progress_percentage` | integer | optionnel, 0-100 | Pourcentage d'avancement |
| `related_issues` | relation | M2M → Issue | Enjeux adressés |
| `related_stakeholders` | relation | M2M → Stakeholder | Parties intéressées concernées |
| `parent_objective_id` | relation | FK → Objective, optionnel | Objectif parent (hiérarchie) |
| `linked_measures` | relation | M2M → Measure | Mesures contribuant à l'objectif (module Mesures) |
| `review_date` | date | optionnel | Prochaine date de revue |
| `created_by` | relation | FK → User | Créateur |
| `created_at` | datetime | auto | Date de création |
| `updated_at` | datetime | auto | Date de dernière modification |
