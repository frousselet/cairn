# Module 0: User Management and Access Control

## Functional and Technical Specifications

**Version:** 1.0
**Date:** 27 February 2026
**Status:** Draft

---

## Entities in this module

- [User](user.md)
- [Group](group.md)
- [Permission](permission.md)
- [SpecialPermission](special-permission.md)
- [Session](session.md)
- [AccessLog](access-log.md)
- [First-run onboarding](onboarding.md)

---

## 1. Overview

### 1.1 Module objective

The **User Management and Access Control** module is the cross-cutting foundation of the Cairn application. It handles user authentication, profile management, and granular access control across all platform features through an RBAC (Role-Based Access Control) model based on permission groups.

This module is fully administrable from the Cairn interface. Access to the Django administration interface is reserved for users holding a specific permission and is not required for day-to-day user management.

### 1.2 Functional scope

The module covers five sub-domains:

1. Authentication (login/password, future SSO)
2. User management (CRUD, profiles, statuses)
3. Group management (logical groupings of permissions)
4. Permission management (granular RBAC per feature and per CRUD action)
5. Logging of access and administration actions

### 1.3 Dependencies on other modules

| Target module | Nature of the dependency |
|---|---|
| All modules | Each module consumes the permissions defined here to control access to its features |
| Context and Organization | GRC roles (Module 1) are distinct from application access groups but can be linked to users |
| Notifications | Notification preferences are attached to the user profile |

### 1.4 Guiding principles

- **Full autonomy through the Cairn interface:** all management of users, groups and permissions is done from the application, without resorting to the Django admin.
- **Restricted Django admin:** access to the Django administration interface is controlled by a dedicated permission, intended exclusively for advanced technical operations (debugging, low-level configuration).
- **Authentication extensibility:** the architecture is designed to integrate SSO mechanisms (SAML 2.0, OIDC) later without a major impact on the data model.
- **Maximum granularity:** each feature of each module has 4 elementary permissions (create, read, update, delete), granted exclusively through groups.

---

## 3. Business rules

### 3.1 Authentication rules

| ID | Rule |
|---|---|
| RA-01 | Authentication is performed using **email + password**. The email is the unique sign-in identifier (case-insensitive). |
| RA-02 | Passwords must comply with a configurable policy. By default: minimum 12 characters, at least one uppercase letter, one lowercase letter, one digit and one special character. |
| RA-03 | Passwords are stored hashed using a robust algorithm (Argon2 recommended, bcrypt acceptable). |
| RA-04 | After **5 consecutive failed login attempts**, the account is locked for **15 minutes**. These thresholds are configurable. |
| RA-05 | A **JWT** token is issued on successful login. The access token has a lifetime of **30 minutes**, the refresh token **7 days**. These durations are configurable. |
| RA-06 | The refresh token is **rotating**: each use issues a new access/refresh pair and invalidates the previous refresh. |
| RA-07 | Explicit sign-out revokes the refresh token server-side (blacklist). |
| RA-08 | A user can view and revoke their **active sessions** from their profile. |
| RA-09 | An administrator can force sign-out of all of a user's sessions. |
| RA-10 | Changing the password invalidates all of the user's active sessions except the current one. |

### 3.2 Password management rules

| ID | Rule |
|---|---|
| RP-01 | The user can change their password from their profile (requires the current password). |
| RP-02 | The **password reset** procedure sends a unique link by email, valid for **1 hour**. |
| RP-03 | The history of the **last 5 passwords** is kept (hashed). The user cannot reuse a recent password. |
| RP-04 | An administrator can force a password reset for a user. The user receives an email with a reset link. The administrator never sees the password in plain text. |
| RP-05 | A **maximum password lifetime** is configurable (default: 90 days). On expiry, the user is prompted to change their password at the next sign-in. |

### 3.3 User management rules

| ID | Rule |
|---|---|
| RU-01 | Creating, modifying and deactivating users is done exclusively from the **Cairn** interface (not from the Django admin). |
| RU-02 | A user cannot be deleted if they are referenced as owner, creator or responsible party in another module. In that case, only **deactivation** (`is_active = false`) is possible. |
| RU-03 | A deactivated user can no longer sign in. Their active sessions are immediately revoked. |
| RU-04 | A user can edit their own profile (last name, first name, phone, avatar, language, time zone, notification preferences) without a specific permission. |
| RU-05 | Only users holding the `system.users.manage` permission can create, modify or deactivate other users. |
| RU-06 | The `is_staff` field (access to the Django admin) can only be modified by a user holding the `system.admin_django.access` permission. |
| RU-07 | At all times there must be at least **one active user** holding the `system.users.manage` permission. The system prevents any deactivation or group removal that would violate this rule. |

### 3.4 Group and permission management rules

| ID | Rule |
|---|---|
| RG-01 | **Permissions are granted exclusively through groups**, never directly to a user. |
| RG-02 | A user can belong to **multiple groups**. Their effective permissions are the **union** of the permissions of all their groups. |
| RG-03 | **System groups** (`is_system = true`) are created at installation and cannot be modified, deleted or renamed. Their permissions can, however, be viewed. |
| RG-04 | Custom (non-system) groups can be created, modified and deleted by users holding the `system.groups.manage` permission. |
| RG-05 | Deleting a group is forbidden if it still contains users. The users must first be removed or reassigned. |
| RG-06 | **Permissions are generated automatically** by the system from the registry of modules and features. They cannot be created or deleted manually. |
| RG-07 | Each feature of each module generates exactly **4 permissions**: `create`, `read`, `update`, `delete`. Special permissions ([SpecialPermission](special-permission.md)) are added manually to the registry. |
| RG-08 | Any change to a group (adding/removing a permission, adding/removing a member) generates an entry in the audit log. |
| RG-09 | The **Django admin** access button is only visible in the interface to users holding the `system.admin_django.access` permission. |

---

## 4. Default system groups

The following groups are created when the application is installed and cannot be deleted.

### 4.1 Super Administrator

| Property | Value |
|---|---|
| Name | `Super Administrateur` |
| `is_system` | true |
| Permissions | **All permissions** (including `system.admin_django.access`) |
| Purpose | Complete technical administration of the platform |

### 4.2 Administrator

| Property | Value |
|---|---|
| Name | `Administrateur` |
| `is_system` | true |
| Permissions | All permissions **except** `system.admin_django.access` |
| Purpose | Complete functional administration |

### 4.3 CISO / DPO

| Property | Value |
|---|---|
| Name | `RSSI / DPO` |
| `is_system` | true |
| Permissions | All `*.read`, `*.create`, `*.update` permissions + `*.export` + `*.audit_trail.read` (no `*.delete` and no `system.config.manage`) |
| Purpose | Steering the GRC programme |

### 4.4 Auditor

| Property | Value |
|---|---|
| Name | `Auditeur` |
| `is_system` | true |
| Permissions | All `*.read` permissions + `*.export` + `*.audit_trail.read` |
| Purpose | Reviewing and auditing the platform |

### 4.5 Contributor

| Property | Value |
|---|---|
| Name | `Contributeur` |
| `is_system` | true |
| Permissions | All `*.read`, `*.create`, `*.update` permissions (no `*.delete` and no system access) |
| Purpose | Contributing to GRC content |

### 4.6 Reader

| Property | Value |
|---|---|
| Name | `Lecteur` |
| `is_system` | true |
| Permissions | All `*.read` permissions only |
| Purpose | Read-only access |

---

## 5. Permission registry

### 5.1 Naming convention

Each permission follows the format: `{module}.{feature}.{action}`

- **module**: module identifier (`context`, `assets`, `risks`, `compliance`, `measures`, `suppliers`, `audits`, `incidents`, `training`, `system`)
- **feature**: feature identifier within the module
- **action**: `create`, `read`, `update`, `delete`

### 5.2 Permissions by module

#### Context and Organization module (`context`)

| Feature | create | read | update | delete |
|---|---|---|---|---|
| `scope` | `context.scope.create` | `context.scope.read` | `context.scope.update` | `context.scope.delete` |
| `scope_approve` | : | : | `context.scope_approve.update` | : |
| `issue` | `context.issue.create` | `context.issue.read` | `context.issue.update` | `context.issue.delete` |
| `stakeholder` | `context.stakeholder.create` | `context.stakeholder.read` | `context.stakeholder.update` | `context.stakeholder.delete` |
| `expectation` | `context.expectation.create` | `context.expectation.read` | `context.expectation.update` | `context.expectation.delete` |
| `objective` | `context.objective.create` | `context.objective.read` | `context.objective.update` | `context.objective.delete` |
| `swot` | `context.swot.create` | `context.swot.read` | `context.swot.update` | `context.swot.delete` |
| `swot_validate` | : | : | `context.swot_validate.update` | : |
| `role` | `context.role.create` | `context.role.read` | `context.role.update` | `context.role.delete` |
| `role_assign` | : | : | `context.role_assign.update` | : |
| `activity` | `context.activity.create` | `context.activity.read` | `context.activity.update` | `context.activity.delete` |
| `config` | : | `context.config.read` | `context.config.update` | : |
| `export` | : | `context.export.read` | : | : |
| `audit_trail` | : | `context.audit_trail.read` | : | : |

#### Asset Management module (`assets`)

| Feature | create | read | update | delete |
|---|---|---|---|---|
| `essential_asset` | `assets.essential_asset.create` | `assets.essential_asset.read` | `assets.essential_asset.update` | `assets.essential_asset.delete` |
| `essential_asset_evaluate` | : | : | `assets.essential_asset_evaluate.update` | : |
| `support_asset` | `assets.support_asset.create` | `assets.support_asset.read` | `assets.support_asset.update` | `assets.support_asset.delete` |
| `dependency` | `assets.dependency.create` | `assets.dependency.read` | `assets.dependency.update` | `assets.dependency.delete` |
| `group` | `assets.group.create` | `assets.group.read` | `assets.group.update` | `assets.group.delete` |
| `import` | `assets.import.create` | : | : | : |
| `config` | : | `assets.config.read` | `assets.config.update` | : |
| `export` | : | `assets.export.read` | : | : |
| `audit_trail` | : | `assets.audit_trail.read` | : | : |

> Note: The Risks, Compliance, Measures, Suppliers, Audits, Incidents and Training modules will follow the same convention. The complete registry will be established when each module is specified.

#### System permissions (`system`)

| Feature | Permissions |
|---|---|
| `admin_django` | `system.admin_django.access` |
| `users` | `system.users.create`, `system.users.read`, `system.users.update`, `system.users.delete` |
| `groups` | `system.groups.create`, `system.groups.read`, `system.groups.update`, `system.groups.delete` |
| `audit_trail` | `system.audit_trail.read` |
| `config` | `system.config.read`, `system.config.update` |
| `webhooks` | `system.webhooks.create`, `system.webhooks.read`, `system.webhooks.update`, `system.webhooks.delete` |
| `notifications` | `system.notifications.read`, `system.notifications.update` |

---

## 6. REST API specifications

### 6.1 General conventions

- **Base URL:** `/api/v1/`
- Conventions identical to the other modules (pagination, sorting, filtering, response format).

### 6.2 Endpoints: Authentication

| Method | Endpoint | Description | Authentication required |
|---|---|---|---|
| `POST` | `/auth/login` | Sign in (email + password) → returns access + refresh tokens | No |
| `POST` | `/auth/refresh` | Refresh the access token via the refresh token | No (refresh token required) |
| `POST` | `/auth/logout` | Sign out (revokes the refresh token) | Yes |
| `POST` | `/auth/password/change` | Change your password | Yes |
| `POST` | `/auth/password/reset-request` | Request a password reset | No |
| `POST` | `/auth/password/reset-confirm` | Confirm the reset (token + new password) | No (reset token) |
| `GET` | `/auth/me` | Profile of the signed-in user with effective permissions | Yes |
| `PATCH` | `/auth/me` | Edit your own profile | Yes |
| `GET` | `/auth/me/sessions` | List your active sessions | Yes |
| `DELETE` | `/auth/me/sessions/{session_id}` | Revoke a specific session | Yes |
| `DELETE` | `/auth/me/sessions` | Revoke all your sessions (except the current one) | Yes |

**Sign-in payload:**

```json
{
  "email": "user@example.com",
  "password": "SecureP@ssw0rd!"
}
```

**Successful sign-in response:**

```json
{
  "status": "success",
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
    "access_token_expires_at": "2026-02-27T15:00:00Z",
    "refresh_token_expires_at": "2026-03-06T14:30:00Z",
    "user": {
      "id": "uuid-xxx",
      "email": "user@example.com",
      "display_name": "Jean Dupont",
      "language": "fr",
      "permissions": ["context.scope.read", "context.scope.create", "..."]
    }
  }
}
```

**Sign-in error response:**

```json
{
  "status": "error",
  "error": {
    "code": "AUTHENTICATION_FAILED",
    "message": "Invalid email or password.",
    "details": {
      "remaining_attempts": 3
    }
  }
}
```

**Locked account response:**

```json
{
  "status": "error",
  "error": {
    "code": "ACCOUNT_LOCKED",
    "message": "Account is temporarily locked due to multiple failed login attempts.",
    "details": {
      "locked_until": "2026-02-27T14:45:00Z"
    }
  }
}
```

### 6.3 Endpoints: Users

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/users` | List users (filterable, paginated) |
| `POST` | `/users` | Create a user |
| `GET` | `/users/{id}` | User detail |
| `PUT` | `/users/{id}` | Full update |
| `PATCH` | `/users/{id}` | Partial update |
| `DELETE` | `/users/{id}` | Deactivate a user (soft delete) |
| `POST` | `/users/{id}/activate` | Reactivate a user |
| `POST` | `/users/{id}/force-password-reset` | Force a password reset |
| `POST` | `/users/{id}/revoke-sessions` | Revoke all of the user's sessions |
| `GET` | `/users/{id}/groups` | List a user's groups |
| `POST` | `/users/{id}/groups` | Add the user to one or more groups |
| `DELETE` | `/users/{id}/groups/{group_id}` | Remove the user from a group |
| `GET` | `/users/{id}/permissions` | List effective permissions (union of groups) |
| `GET` | `/users/{id}/access-log` | The user's access log |

**Filtering parameters:**

- `?is_active=true|false`
- `?group_id={uuid}`
- `?search=term` (search on email, last name, first name)
- `?department=DSI`
- `?has_permission={codename}` (users holding a specific permission)

### 6.4 Endpoints: Groups

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/groups` | List groups |
| `POST` | `/groups` | Create a group |
| `GET` | `/groups/{id}` | Group detail |
| `PUT` | `/groups/{id}` | Full update |
| `PATCH` | `/groups/{id}` | Partial update |
| `DELETE` | `/groups/{id}` | Delete a group (if empty and non-system) |
| `GET` | `/groups/{id}/permissions` | List the group's permissions |
| `POST` | `/groups/{id}/permissions` | Add permissions to the group |
| `DELETE` | `/groups/{id}/permissions/{permission_id}` | Remove a permission from the group |
| `PUT` | `/groups/{id}/permissions` | Replace all of the group's permissions |
| `GET` | `/groups/{id}/users` | List the group's users |
| `POST` | `/groups/{id}/users` | Add users to the group |
| `DELETE` | `/groups/{id}/users/{user_id}` | Remove a user from the group |

### 6.5 Endpoints: Permissions

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/permissions` | List all permissions (filterable by module, feature, action) |
| `GET` | `/permissions/{id}` | Permission detail |
| `GET` | `/permissions/by-module` | Permissions grouped by module then by feature |

**Filtering parameters:**

- `?module=context`
- `?feature=scope`
- `?action=create`
- `?search=term`

### 6.6 Endpoints: Access log

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/access-logs` | Global access log (filterable) |
| `GET` | `/access-logs/statistics` | Access statistics (logins per day, failures, etc.) |

**Filtering parameters:**

- `?user_id={uuid}`
- `?event_type=login_success|login_failed`
- `?date_from={date}&date_to={date}`
- `?ip_address={ip}`

---

## 7. User interface specifications

### 7.1 Navigation

User management is accessible via an "Administration" navigation item in the main menu, which breaks down into sub-menus: Users, Groups, Access log. This menu is only visible to users holding at least one `system.*` permission.

The Django admin access button is displayed **only** if the user holds the `system.admin_django.access` permission. It is positioned distinctly (e.g. an icon at the foot of the menu or in an "Advanced" sub-menu) to avoid any confusion with the Cairn administration.

### 7.2 Login page

- Email + password form.
- "Forgot password?" link leading to the reset procedure.
- Generic error message on failure (do not reveal whether the email exists or not).
- Display of a remaining-attempts counter after the 3rd failure.
- Lock message with remaining duration if the account is locked.
- Area reserved for future SSO buttons (hidden until configured).

### 7.3 "My profile" view

- Display and editing of personal information (last name, first name, phone, avatar, language, time zone).
- "Security" section: password change, list of active sessions with the ability to revoke them.
- "Notification preferences" section: choice of channels (email, in-app) by event type.
- Read-only display of membership groups and effective permissions.

### 7.4 "Users" view

- **List:** Table with columns (Name, Email, Job title, Department, Groups, Status, Last sign-in). Filters on status (active/inactive), group, department. Text search.
- **Detail / Editing:** Form with tabs:
  - *Information:* identity, contact details, job title, department.
  - *Groups:* list of groups with the ability to add/remove.
  - *Effective permissions:* consolidated view (union of groups) organized by module, read-only.
  - *Sessions:* active sessions with the ability to revoke them.
  - *Access log:* history of sign-ins and authentication actions.
- **Actions:** Create, Edit, Deactivate/Reactivate, Force password reset, Revoke sessions.
- **Indicators:** Status badge (active/inactive/locked), warning if no group is assigned.

### 7.5 "Groups" view

- **List:** Table with columns (Name, Description, System, Number of users, Number of permissions). "System" badge for non-editable groups.
- **Detail / Editing:** Form with tabs:
  - *Information:* name, description.
  - *Permissions:* interactive matrix organized by module → feature → action (create/read/update/delete). Each cell is a checkbox. Ability to check/uncheck by row (feature) or by column (action). For system groups, the matrix is read-only.
  - *Users:* list of members with the ability to add/remove.
- **Actions:** Create, Edit, Delete (if empty and non-system).

### 7.6 "Permission matrix" view

- Cross-cutting view presenting a complete grid: **Groups (columns) × Permissions (rows)** grouped by module/feature.
- Allows the distribution of rights across groups to be seen at a glance.
- Read-only mode (editing is done from each group's detail).

### 7.7 "Access log" view

- **List:** Chronological table of authentication events with columns (Date, User, Event type, IP, Result). Filters by user, event type, period, IP.
- **Statistics:** Charts of logins per day, failure rate, locked accounts over the period.

---

## 8. Security rules

### 8.1 Protection against attacks

| Measure | Description |
|---|---|
| Rate limiting | Limiting of login attempts: max 10 requests per minute per IP on `/auth/login` |
| Account lockout | Temporary lockout after N consecutive failures ([RA-04](#31-authentication-rules)) |
| CSRF protection | CSRF token on forms (session mode); not applicable in pure JWT mode |
| XSS protection | Escaping of user data, strict Content-Security-Policy |
| Secure transport | HTTPS mandatory in production |
| Secure cookies | `HttpOnly`, `Secure`, `SameSite=Strict` flags on session/refresh cookies |
| Token rotation | Rotating refresh token with invalidation of the previous one ([RA-06](#31-authentication-rules)) |

### 8.2 Default password policy

| Parameter | Default value | Configurable |
|---|---|---|
| Minimum length | 12 characters | Yes |
| Uppercase required | Yes | Yes |
| Lowercase required | Yes | Yes |
| Digit required | Yes | Yes |
| Special character required | Yes | Yes |
| History (non-reuse) | Last 5 passwords | Yes |
| Maximum lifetime | 90 days | Yes |
| Attempts before lockout | 5 | Yes |
| Lockout duration | 15 minutes | Yes |

### 8.3 Preparation for SSO (future)

The architecture is designed to integrate external identity providers later:

| Protocol | Intended use |
|---|---|
| **SAML 2.0** | Integration with enterprise IdPs (ADFS, Azure AD, Okta) |
| **OpenID Connect (OIDC)** | Integration with OAuth2/OIDC providers (Google, Azure AD, Keycloak) |

Points to watch for the future:

- The `User` model provides for an extensible field to store the external identifier (`external_id`, `identity_provider`).
- The authentication flow is decoupled via an abstraction layer (Django authentication backend) allowing SSO backends to be added without modifying the user model.
- The login page provides for an area dedicated to SSO buttons.
- Automatic user provisioning (JIT provisioning) and group mapping from SAML/OIDC claims will be specified in a later version.

---

## 9. Logging and traceability

### 9.1 Audit Trail

The following administration actions are tracked in the global audit log:

| Action | Description |
|---|---|
| `user.create` | Creation of a user |
| `user.update` | Modification of a user profile |
| `user.deactivate` | Deactivation of a user |
| `user.activate` | Reactivation of a user |
| `user.force_password_reset` | Forced password reset |
| `user.revoke_sessions` | Revocation of a user's sessions |
| `group.create` | Creation of a group |
| `group.update` | Modification of a group |
| `group.delete` | Deletion of a group |
| `group.permission_add` | Addition of permission(s) to a group |
| `group.permission_remove` | Removal of permission(s) from a group |
| `group.user_add` | Addition of a user to a group |
| `group.user_remove` | Removal of a user from a group |

### 9.2 Access log

The access log ([AccessLog](access-log.md)) is distinct from the audit log and focuses on authentication events. Its retention is configurable (default: 2 years).

### 9.3 Retention

- Audit log of administration actions: 7 years (configurable).
- Access log (authentication): 2 years (configurable).

---

## 10. Notifications

| Event | Recipients | Channel |
|---|---|---|
| Account created | User concerned | Email |
| Password reset (by an administrator) | User concerned | Email |
| Account deactivated | User concerned | Email |
| Account reactivated | User concerned | Email |
| Password expiring (7 days before) | User concerned | In-app, email |
| Account locked after failed attempts | User concerned + Administrators | In-app (admin), email (user) |
| Sign-in from a new IP address | User concerned | Email (optional, configurable) |
| Addition/removal of a group | User concerned | In-app |

---

## 11. Technical considerations

### 11.1 Django authentication backend

The module relies on Django's authentication system with the following adaptations:

- **Custom User Model**: the `User` model extends `AbstractBaseUser` with `email` as the identifier instead of `username`.
- **Authentication Backend**: a custom backend handles email/password authentication and allows SSO backends to be added in the future.
- **Permission Backend**: a custom backend resolves permissions through groups (and not through Django's direct `user_permissions`).

### 11.2 JWT token management

- Recommended library: `djangorestframework-simplejwt`.
- The access token contains the claims: `user_id`, `email`, `exp`, `iat`, `jti`.
- The access token **does not contain** the permissions (they are too large and can change between two issuances). Permissions are checked server-side on every request.
- The refresh token is stored in the database (`Session` table) to allow revocation.

### 11.3 Multi-tenant

Each user is attached to a tenant (`tenant_id`). A user can only see and manage the users and groups of their own tenant. System groups are duplicated per tenant at initialization.

### 11.4 Performance

- The resolution of a user's effective permissions (union of groups) is cached with a TTL of **5 minutes**, invalidated on any change to a group or membership.
- The permission check on each API request must execute in less than **5 ms** (read from cache).
- The login page must respond in less than **500 ms** including the password hash.

### 11.5 Webhooks

Specific events:

- `system.user.created`, `updated`, `deactivated`, `activated`
- `system.group.created`, `updated`, `deleted`
- `system.group.permissions_changed`
- `system.group.members_changed`
- `system.auth.login_success`, `login_failed`, `account_locked`

---

## 12. Acceptance criteria

### 12.1 Authentication

- [ ] Sign-in by email + password works and returns a JWT access/refresh pair
- [ ] Token refresh works with rotation of the refresh token
- [ ] Sign-out effectively revokes the refresh token
- [ ] Account lockout is triggered after N consecutive failures
- [ ] Automatic unlock works after the configured duration
- [ ] Password reset by email works (request + confirmation)
- [ ] Changing the password invalidates the other sessions
- [ ] Password history prevents reuse

### 12.2 User management

- [ ] Full user CRUD works from the Cairn interface
- [ ] Deactivating a user revokes their sessions and prevents sign-in
- [ ] A user can edit their own profile
- [ ] The constraint of at least one active administrator is enforced
- [ ] The Django admin is not required for day-to-day management

### 12.3 Groups and permissions

- [ ] Permissions are granted exclusively through groups
- [ ] A user's effective permissions are the union of their groups
- [ ] System groups are not editable or deletable
- [ ] Custom groups support full CRUD
- [ ] The permission matrix can be viewed and permissions edited via the interface
- [ ] Each feature has 4 working CRUD permissions
- [ ] Access control is effective on every API endpoint and every view

### 12.4 Django admin

- [ ] The Django admin access button is only visible to users with `system.admin_django.access`
- [ ] The `is_staff` field can only be modified by a user holding `system.admin_django.access`
- [ ] Access to the `/admin/` URL is blocked for users without the permission

### 12.5 Security

- [ ] Passwords comply with the defined policy
- [ ] Rate limiting is active on the authentication endpoints
- [ ] Tokens are revocable (sessions, sign-out)
- [ ] The access log records all authentication events
- [ ] The audit log records all administration actions

### 12.6 Performance

- [ ] The permission check executes in less than 5 ms (cache)
- [ ] Effective permission resolution is correctly cached and invalidated

---

*End of the specifications for Module 0: User Management and Access Control*
