# Group

`accounts.models.group.Group`

Représente un groupe de permissions. Les droits d'accès sont attribués exclusivement via les groupes, jamais directement à un utilisateur.

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-généré | Identifiant unique |
| `name` | string | requis, unique, max 255 | Nom du groupe |
| `description` | text | optionnel | Description du groupe et de sa vocation |
| `is_system` | boolean | requis, défaut false | Groupe système (non modifiable, non supprimable) |
| `permissions` | relation | M2M → Permission | Permissions associées |
| `users` | relation | M2M → User | Utilisateurs membres |
| `created_by` | relation | FK → User | Créateur |
| `created_at` | datetime | auto | Date de création |
| `updated_at` | datetime | auto | Date de dernière modification |
