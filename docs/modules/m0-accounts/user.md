# User

`accounts.models.user.User`

Represents a user of the Cairn platform.

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-generated | Unique identifier |
| `email` | string | required, unique, email format | Email address (sign-in identifier) |
| `first_name` | string | required, max 150 | First name |
| `last_name` | string | required, max 150 | Last name |
| `display_name` | string | computed or overridden, max 255 | Display name (`first_name last_name` by default) |
| `job_title` | string | optional, max 255 | Job title / position |
| `department` | string | optional, max 255 | Division / department |
| `phone` | string | optional, max 50 | Phone number |
| `avatar` | image | optional | Profile picture |
| `password` | string | required, hashed | Password (bcrypt/argon2) |
| `is_active` | boolean | required, default true | Active account |
| `is_staff` | boolean | required, default false | Access to the Django administration interface |
| `groups` | relation | M2M → Group | Membership groups |
| `language` | enum | required, default `fr` | Preferred interface language (`fr`, `en`) |
| `timezone` | string | required, default `Europe/Paris` | Time zone |
| `theme_preference` | enum | required, default `system` | Preferred display theme (`light`, `dark`, `system`). `system` follows the operating system preference via `prefers-color-scheme` and reacts to its changes in real time. The preference is rendered server-side (`data-theme-preference` attribute on `<html>`) to avoid any incorrect theme flash on load, with a `localStorage` fallback then `prefers-color-scheme` for unauthenticated pages (login, OAuth authorize) |
| `notification_preferences` | json | optional | Notification preferences (email, in-app) |
| `last_login` | datetime | auto | Last sign-in date |
| `password_changed_at` | datetime | auto | Date of the last password change |
| `failed_login_attempts` | integer | auto, default 0 | Number of consecutive failed login attempts |
| `locked_until` | datetime | optional | Account lock end date |
| `created_by` | relation | FK → User, optional | Account creator (null if self-registration) |
| `created_at` | datetime | auto | Creation date |
| `updated_at` | datetime | auto | Last modification date |

> Note: The `email` field is the unique sign-in identifier. It replaces Django's default `username` field.
