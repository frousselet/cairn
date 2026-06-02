# Session

`accounts.models.session.Session`

Représente une session active d'un utilisateur authentifié.

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-généré | Identifiant unique |
| `user_id` | relation | FK → User, requis | Utilisateur |
| `token_jti` | string | requis, unique | Identifiant unique du JWT (JTI claim) |
| `ip_address` | string | requis | Adresse IP de connexion |
| `user_agent` | string | optionnel | User-agent du navigateur/client |
| `created_at` | datetime | auto | Date de création (connexion) |
| `expires_at` | datetime | requis | Date d'expiration |
| `revoked_at` | datetime | optionnel | Date de révocation (déconnexion explicite) |
| `is_active` | boolean | requis, défaut true | Session active |
