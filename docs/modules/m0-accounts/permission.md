# Permission

`accounts.models.permission.Permission`

Représente une permission élémentaire sur une feature d'un module. Les permissions sont générées par le système et ne sont pas créées manuellement.

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-généré | Identifiant unique |
| `codename` | string | requis, unique, max 255 | Code technique (ex. `context.scope.create`) |
| `name` | string | requis, max 255 | Libellé lisible (ex. « Créer un périmètre ») |
| `module` | string | requis, max 100 | Module d'appartenance (ex. `context`, `assets`) |
| `feature` | string | requis, max 100 | Feature concernée (ex. `scope`, `essential_asset`) |
| `action` | enum | requis | `create`, `read`, `update`, `delete` |
| `description` | text | optionnel | Description détaillée de la permission |
| `is_system` | boolean | requis, défaut true | Permission système (non supprimable) |

> Note : Le format du `codename` suit la convention `{module}.{feature}.{action}`. Les permissions sont auto-générées à partir du registre des modules.
