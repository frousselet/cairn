# AccessLog

`accounts.models.access_log.AccessLog`

Enregistre chaque événement d'authentification pour la traçabilité et la détection d'anomalies.

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-généré | Identifiant unique |
| `timestamp` | datetime | auto | Horodatage UTC |
| `user_id` | relation | FK → User, optionnel | Utilisateur (null si login échoué sur un compte inexistant) |
| `email_attempted` | string | requis | Email utilisé pour la tentative |
| `event_type` | enum | requis | `login_success`, `login_failed`, `logout`, `token_refresh`, `password_change`, `password_reset_request`, `password_reset_complete`, `account_locked`, `account_unlocked` |
| `ip_address` | string | requis | Adresse IP |
| `user_agent` | string | optionnel | User-agent |
| `failure_reason` | string | optionnel | Raison de l'échec (ex. `invalid_password`, `account_locked`, `account_inactive`) |
| `metadata` | json | optionnel | Données complémentaires |
