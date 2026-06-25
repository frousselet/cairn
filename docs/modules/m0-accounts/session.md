# Session

`accounts.models.session.Session`

Represents an active session of an authenticated user.

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-generated | Unique identifier |
| `user_id` | relation | FK → User, required | User |
| `token_jti` | string | required, unique | Unique JWT identifier (JTI claim) |
| `ip_address` | string | required | Sign-in IP address |
| `user_agent` | string | optional | Browser/client user-agent |
| `created_at` | datetime | auto | Creation date (sign-in) |
| `expires_at` | datetime | required | Expiration date |
| `revoked_at` | datetime | optional | Revocation date (explicit sign-out) |
| `is_active` | boolean | required, default true | Active session |
