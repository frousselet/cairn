# SpecialPermission

`accounts.models.permission.SpecialPermission`

Some permissions do not follow the standard CRUD model and cover cross-cutting or specific actions.

| Codename | Description |
|---|---|
| `system.admin_django.access` | Show the access button and access the Django administration interface |
| `system.users.manage` | Manage users (create, modify, deactivate) |
| `system.groups.manage` | Manage groups and assign permissions |
| `system.audit_trail.read` | View the global audit log |
| `system.config.manage` | Access the application's global configuration |
| `system.webhooks.manage` | Manage webhooks |
| `system.notifications.manage` | Manage notification templates |

> These special permissions are created as `Permission` records with `module = system` and are handled in the same way as CRUD permissions by the authorization engine.
