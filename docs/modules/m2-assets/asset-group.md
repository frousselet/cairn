# AssetGroup

`assets.models.group.AssetGroup`

Regroupement de biens supports par lot logique (ex. « Serveurs de production ») pour faciliter la gestion et l'appréciation des risques.

Permet de regrouper des biens supports par lot logique (ex. « Serveurs de production », « Postes de travail site Paris ») pour faciliter la gestion et l'appréciation des risques.

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-généré | Identifiant unique |
| `scope_id` | relation | FK → Scope, requis | Périmètre rattaché |
| `name` | string | requis, max 255 | Nom du groupe |
| `description` | text | optionnel | Description du groupe |
| `type` | enum | requis | Même typologie que SupportAsset.type |
| `members` | relation | M2M → SupportAsset | Biens supports membres |
| `owner_id` | relation | FK → User, optionnel | Responsable du groupe |
| `status` | enum | requis | `active`, `inactive` |
| `created_by` | relation | FK → User | Créateur |
| `created_at` | datetime | auto | Date de création |
| `updated_at` | datetime | auto | Date de dernière modification |
