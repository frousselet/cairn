# Activity

`context.models.activity.Activity`

Représente une activité ou un processus métier de l'organisme.

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-généré | Identifiant unique |
| `scope_id` | relation | FK → Scope, requis | Périmètre rattaché |
| `reference` | string | requis, unique | Code de référence (ex. ACT-001) |
| `name` | string | requis, max 255 | Nom de l'activité |
| `description` | text | optionnel | Description détaillée |
| `type` | enum | requis | `core_business`, `support`, `management` |
| `criticality` | enum | requis | `low`, `medium`, `high`, `critical` |
| `owner_id` | relation | FK → User, requis | Responsable de l'activité |
| `parent_activity_id` | relation | FK → Activity, optionnel | Activité parente (hiérarchie) |
| `related_stakeholders` | relation | M2M → Stakeholder | Parties intéressées impliquées |
| `related_objectives` | relation | M2M → Objective | Objectifs contributifs |
| `linked_assets` | relation | M2M → EssentialAsset | Biens essentiels supportant l'activité (module Actifs) |
| `status` | enum | requis | `active`, `inactive`, `planned` |
| `created_by` | relation | FK → User | Créateur |
| `created_at` | datetime | auto | Date de création |
| `updated_at` | datetime | auto | Date de dernière modification |
