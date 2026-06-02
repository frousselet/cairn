# SpecialPermission

`accounts.models.permission.SpecialPermission`

Certaines permissions ne suivent pas le modèle CRUD standard et couvrent des actions transversales ou spécifiques.

| Codename | Description |
|---|---|
| `system.admin_django.access` | Afficher le bouton d'accès et accéder à l'interface d'administration Django |
| `system.users.manage` | Gérer les utilisateurs (créer, modifier, désactiver) |
| `system.groups.manage` | Gérer les groupes et affecter des permissions |
| `system.audit_trail.read` | Consulter le journal d'audit global |
| `system.config.manage` | Accéder à la configuration globale de l'application |
| `system.webhooks.manage` | Gérer les webhooks |
| `system.notifications.manage` | Gérer les modèles de notifications |

> Ces permissions spéciales sont créées en tant qu'enregistrements `Permission` avec `module = system` et sont traitées de la même manière que les permissions CRUD par le moteur d'autorisation.
