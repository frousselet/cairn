# User

`accounts.models.user.User`

Représente un utilisateur de la plateforme Cairn.

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-généré | Identifiant unique |
| `email` | string | requis, unique, format email | Adresse email (identifiant de connexion) |
| `first_name` | string | requis, max 150 | Prénom |
| `last_name` | string | requis, max 150 | Nom de famille |
| `display_name` | string | calculé ou surchargé, max 255 | Nom d'affichage (`first_name last_name` par défaut) |
| `job_title` | string | optionnel, max 255 | Fonction / poste |
| `department` | string | optionnel, max 255 | Direction / service |
| `phone` | string | optionnel, max 50 | Numéro de téléphone |
| `avatar` | image | optionnel | Photo de profil |
| `password` | string | requis, hashé | Mot de passe (bcrypt/argon2) |
| `is_active` | boolean | requis, défaut true | Compte actif |
| `is_staff` | boolean | requis, défaut false | Accès à l'interface d'administration Django |
| `groups` | relation | M2M → Group | Groupes d'appartenance |
| `language` | enum | requis, défaut `fr` | Langue d'interface préférée (`fr`, `en`) |
| `timezone` | string | requis, défaut `Europe/Paris` | Fuseau horaire |
| `theme_preference` | enum | requis, défaut `system` | Thème d'affichage préféré (`light`, `dark`, `system`). `system` suit la préférence du système d'exploitation via `prefers-color-scheme` et réagit à ses changements en temps réel. La préférence est rendue côté serveur (attribut `data-theme-preference` sur `<html>`) pour éviter tout flash de thème incorrect au chargement, avec repli `localStorage` puis `prefers-color-scheme` pour les pages non authentifiées (login, OAuth authorize) |
| `notification_preferences` | json | optionnel | Préférences de notification (email, in-app) |
| `last_login` | datetime | auto | Date de dernière connexion |
| `password_changed_at` | datetime | auto | Date du dernier changement de mot de passe |
| `failed_login_attempts` | integer | auto, défaut 0 | Nombre de tentatives de connexion échouées consécutives |
| `locked_until` | datetime | optionnel | Date de fin de verrouillage du compte |
| `created_by` | relation | FK → User, optionnel | Créateur du compte (null si auto-inscription) |
| `created_at` | datetime | auto | Date de création |
| `updated_at` | datetime | auto | Date de dernière modification |

> Note : Le champ `email` est l'identifiant unique de connexion. Il remplace le champ `username` par défaut de Django.
