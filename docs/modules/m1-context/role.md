# Role

`context.models.role.Role`

Représente un rôle au sein du dispositif GRC.

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-généré | Identifiant unique |
| `scope_id` | relation | FK → Scope, requis | Périmètre rattaché |
| `name` | string | requis, max 255 | Intitulé du rôle |
| `description` | text | optionnel | Description du rôle |
| `type` | enum | requis | `governance`, `operational`, `support`, `control` |
| `responsibilities` | relation | O2M → Responsibility | Responsabilités associées |
| `assigned_users` | relation | M2M → User | Utilisateurs affectés |
| `is_mandatory` | boolean | requis, défaut false | Rôle obligatoire (exigé par un référentiel) |
| `source_standard` | string | optionnel | Référentiel d'origine (ex. "ISO 27001 - §5.3") |
| `status` | enum | requis | `active`, `inactive` |
| `created_by` | relation | FK → User | Créateur |
| `created_at` | datetime | auto | Date de création |
| `updated_at` | datetime | auto | Date de dernière modification |

Les responsabilités se gèrent directement depuis la page de détail du rôle :
ajout, modification et suppression via un tiroir (drawer) HTMX, la section se
rafraîchissant sans rechargement de page. Les actions sont protégées par la
permission `context.role.update`.

Toute création, modification ou suppression d'une responsabilité **repasse le
rôle à l'état initial (brouillon)** : l'approbation est réinitialisée, la version
est incrémentée et la rétrogradation est tracée dans l'historique du rôle, afin
qu'il soit revalidé. Ce comportement s'applique aussi bien depuis l'interface que
via l'API REST (`Role.send_back_to_draft()`, source unique). Les rôles dans un
état terminal (archivé / annulé) ne sont pas affectés.

L'historique du rôle **fusionne l'historique de ses responsabilités** (chaque
responsabilité possède son propre suivi `HistoricalRecords`) : ajout,
modification et suppression d'une responsabilité apparaissent ainsi sur la
chronologie du rôle. Une suppression affiche les valeurs de la responsabilité
retirée et porte un libellé « Responsabilité ».

## Responsibility

Sous-entité : responsabilité associée à un rôle.

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-généré | Identifiant unique |
| `role_id` | relation | FK → Role, requis | Rôle parent |
| `description` | text | requis | Description de la responsabilité |
| `raci_type` | enum | requis | `responsible`, `accountable`, `consulted`, `informed` |
| `related_activity_id` | relation | FK → Activity, optionnel | Activité associée |
| `created_at` | datetime | auto | Date de création |
| `updated_at` | datetime | auto | Date de dernière modification |
