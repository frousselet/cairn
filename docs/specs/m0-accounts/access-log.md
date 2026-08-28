# AccessLog

`accounts.models.access_log.AccessLog`

Records every authentication event for traceability and anomaly detection.

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-generated | Unique identifier |
| `timestamp` | datetime | auto | UTC timestamp |
| `user_id` | relation | FK → User, optional | User (null if the sign-in failed on a non-existent account) |
| `email_attempted` | string | required | Email used for the attempt |
| `event_type` | enum | required | `login_success`, `login_failed`, `logout`, `token_refresh`, `password_change`, `password_reset_request`, `password_reset_complete`, `account_locked`, `account_unlocked` |
| `ip_address` | string | required | IP address |
| `user_agent` | string | optional | User-agent |
| `failure_reason` | string | optional | Reason for the failure (e.g. `invalid_password`, `account_locked`, `account_inactive`) |
| `metadata` | json | optional | Additional data |
