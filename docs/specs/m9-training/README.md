# Module 9 : Training and awareness

## Functional and technical specification

The register of the organisation's **competence and awareness** obligations (ISO/IEC 27001:2022 clause 7.2 competence, clause 7.3 awareness, Annex A.6.3 information security awareness, education and training; NIS2 article 20.2 management body training and article 21.2 g basic cyber hygiene and training). It answers the questions an auditor asks of clause 7.2 and 7.3 : *what competence does each role need, who has it, who was trained on what and when, who is out of date, and how do you know.*

**Status : proposed for v0.37.0.**

## Entities

| Entity | Class | Reference prefix | Lifecycle |
| --- | --- | --- | --- |
| [TrainingCourse](training-course.md) | `training.models.course.TrainingCourse` | `CRSE` | `training_course` |
| [Competency](competency.md) | `training.models.competency.Competency` | `CMPT` | `competency` |
| [TrainingCampaign](training-campaign.md) | `training.models.campaign.TrainingCampaign` | `TRCA` | `training_campaign` |
| [TrainingEnrolment](training-enrolment.md) | `training.models.enrolment.TrainingEnrolment` | none | none (write-once record) |
| [Audience engine](audience-engine.md) | `core.audience.AudienceCampaign` / `core.audience.AudienceRow` | n/a | abstract, shared with module 7 |

---

## 1. Overview

### 1.1 Purpose

Clause 7.2 asks the organisation to *determine the necessary competence* of the people doing work that affects information security, *ensure they are competent* on the basis of education, training or experience, *take actions to acquire it* and *retain documented evidence*. Clause 7.3 asks that people be aware of the policy, their contribution and the implications of not conforming. Today Cairn records who acknowledged a policy (module 7), but not who was trained, on what, whether it is still valid, nor what each role requires.

This module adds :

- a **course catalogue** : awareness modules, phishing simulations, technical and regulatory trainings, with their delivery mode, duration, provider and **validity** (how long a completion counts before renewal);
- **competencies** : what a role requires (for instance *"Secure development"* for the developer role, *"Incident handling"* for the on-call role, *"Annual security awareness"* for everyone), each satisfied by completing one of several courses;
- **training campaigns** : one course delivered to a defined audience (users, groups, roles) by a due date, with one **enrolment** row per person, resolved once at launch; completions recorded by the trainer, self-attested when the course allows it, or **imported** from an external platform (LMS, phishing simulation tool) as CSV;
- the **competency matrix** : for every person in scope, each required competency is *up to date*, *expiring*, *expired* or *missing*, derived from their completions and the courses' validity;
- reminders, a personal *My trainings* page, KPIs, and the management review figures.

The audience mechanics (audience resolved once at launch into write-once evidence rows, newcomers added on demand, completion rate, reminders) are those of the documents module's acknowledgement campaigns. They are extracted into a shared **audience engine** used by both modules (see [audience-engine.md](audience-engine.md)), with no behaviour change for module 7.

### 1.2 Functional scope

| Area | In v0.37.0 |
| --- | --- |
| Course catalogue : type, delivery mode, duration, provider, validity, self-attestation flag, pass mark, linked requirements and policies | yes |
| Competencies : required for roles and groups, satisfied by one of several courses | yes |
| Training campaigns over users, groups and roles; enrolments; trainer recording; self-attestation; excuse with reason; reminders; completion rate | yes |
| CSV import of completions (email, completion date, score, result) into a campaign, with a dry-run report | yes |
| Competency matrix (per person, per role, per competency) with up to date / expiring / expired / missing | yes |
| *My trainings* page : my pending enrolments, my competencies and their validity | yes |
| Shared audience engine, adopted by the documents acknowledgement campaigns | yes |
| Management review : awareness figures (completion rate, competency coverage, overdue renewals) | yes |
| REST API, MCP tools, global search, calendar, dashboard widget, kanban, predefined indicators, help banners, demo seed | yes |
| Hosting course content (videos, quizzes, SCORM packages) | no (see §11) |
| Live integration with an LMS or a phishing platform (API pull) | no (see §11) |
| Individual training plans and budgets | no (see §11) |

### 1.3 Dependencies on other modules

| Target module | Nature of the dependency |
| --- | --- |
| Accounts | `User` (addressees, trainers, owners), `Group` (audience, competency holders), `accounts.Notification`, `PERMISSION_REGISTRY`. |
| Context | `ScopedModel`, `Scope`, `Tag`, `Role` (`Role.assigned_users`) as audience and as competency holder. |
| Compliance | `Requirement` through `TrainingCourse.requirements` (A.6.3, clause 7.2 / 7.3, NIS2 article 20.2). |
| Documents | `Policy` through `TrainingCourse.policies` (the charter or policy a course teaches); the acknowledgement campaigns adopt the shared audience engine. |
| Assets | `Supplier` through `TrainingCourse.provider_supplier` (an external training provider). |
| Management review | A *Training and awareness* card on the review (RG-TRN-20). |

---

## 2. Business rules : the RG-TRN register

### 2.1 Catalogue and competencies

| ID | Rule |
| --- | --- |
| RG-TRN-01 | A [course](training-course.md) is offered (campaigns can be launched for it) only when `active`. Retiring a course requires a comment; its campaigns and completions stay readable and keep counting until their validity ends. |
| RG-TRN-02 | `validity_months` (optional, 1 to 60) is how long a completion of the course satisfies a competency. Empty means the completion never expires (an onboarding course taken once). |
| RG-TRN-03 | A [competency](competency.md) is **required** for the union of its roles' assigned users and its groups' members (active users only). It is **satisfied** by a completed enrolment, in any campaign, of any of its `satisfied_by` courses. A competency with no satisfying course cannot be activated. |
| RG-TRN-04 | A course may be deleted only while `draft` and without campaigns; a competency only while `draft`. |

### 2.2 Campaigns and enrolments

| ID | Rule |
| --- | --- |
| RG-TRN-05 | A [campaign](training-campaign.md) delivers **one course**, which must be `active` at launch. Its audience is resolved **once, at launch**, into one [enrolment](training-enrolment.md) per person (the audience engine, [audience-engine.md](audience-engine.md)). "Add newcomers" re-resolves it on demand. The audience is editable only in `draft`. |
| RG-TRN-06 | A campaign has a `due_date`, and optionally a `session_date` / `session_end` and a `location` (room or meeting link) for a scheduled session. Launch is refused when the due date is past or the audience is empty. |
| RG-TRN-07 | An enrolment leaves `pending` along one of the one-way paths, each stamped and irreversible : **completed** (with `completed_on`, optional `score`), **failed** (attended but below the course's pass mark), **excused** (with a mandatory reason), **expired** (the campaign closed while pending). Once it has left `pending`, nothing about the row changes on any surface (write-once, as RG-DOC-16). |
| RG-TRN-08 | Who can complete a row : a holder of `training.campaign.update` (the trainer or campaign manager) records completions for anyone, with `recorded_by` stamped and the channel `trainer`; the addressee themselves can **self-attest** only when the course has `allows_self_attestation`, by confirming a statement snapshotted on the row (channel `self`). An administrator cannot self-attest on someone's behalf. |
| RG-TRN-09 | When the course has a `pass_mark`, a recorded `score` below it makes the row `failed`; a failed person can be enrolled again in a later campaign. Without a pass mark the score is informative. |
| RG-TRN-10 | `completed_on` cannot be in the future, nor more than `PRIOR_COMPLETION_DAYS` (90) before the campaign's launch : a campaign may record a completion achieved shortly before it was launched, typically through an import, but not an old one. |
| RG-TRN-11 | Closing a campaign expires its pending rows and freezes its completion rate : completed / (all - excused). Failed rows count in the denominator. |

### 2.3 Import

| ID | Rule |
| --- | --- |
| RG-TRN-12 | Completions can be **imported** from a CSV (columns `email`, `completed_on`, optional `score`, optional `result` `completed` / `failed`) into a **running** campaign, by a holder of `training.campaign.update`. A dry run lists, for every line, the row it matches and the outcome (complete, fail, already done, unknown person, not in the audience, invalid date). Only the confirmation applies it. |
| RG-TRN-13 | An import completes or fails **pending rows only**, with the channel `import`, `recorded_by` the importer and the source file name and its SHA-256 recorded on each row. A person outside the audience is reported, never added implicitly; "Add newcomers" or the audience is how they are brought in. |

### 2.4 Competency matrix

| ID | Rule |
| --- | --- |
| RG-TRN-14 | For a person and a required competency, the status is **derived** : `up_to_date` when their latest completion of a satisfying course is still valid (completed_on + validity_months > today, or no validity), `expiring` when it becomes invalid within 60 days, `expired` when it is no longer valid, `missing` when they have none. Never stored, never edited. |
| RG-TRN-15 | Coverage of a competency = up to date or expiring persons / required persons. The matrix can be read per competency, per role, per person, and filtered by scope : a person is in a scope's matrix when they are a member of a role or group assigned to that scope's competencies (competencies are `ScopedModel`s). |
| RG-TRN-16 | Each person sees their own competencies, enrolments and validity on *My trainings*, whatever their permissions (as with *To acknowledge*). |

### 2.5 Integration

| ID | Rule |
| --- | --- |
| RG-TRN-17 | Every report, KPI, calendar feed and picker filters through `reportable()` / `linkable()` / `linkable_or_linked()`. |
| RG-TRN-18 | `TrainingCourse`, `Competency` and `TrainingCampaign` are `ScopedModel`s (a campaign defaults to its course's scopes); enrolments inherit through `campaign__scopes`. A user's own enrolments are visible to them regardless of scopes. |
| RG-TRN-19 | The renewal reminder (RG-TRN-14 `expiring`) notifies the person and suggests the running campaigns of a satisfying course, if any. |
| RG-TRN-20 | The management review detail page gains a *Training and awareness* card : campaigns closed in the review period with their completion rate, competency coverage, persons with expired competencies. The figures are read live. |

---

## 3. Lifecycles

Generated from the transition constants in `training/constants.py`, registered in `training/lifecycles.py`, imported from `TrainingConfig.ready()`. Exit steps keep the platform code `archived` with a domain label.

### 3.1 `training_course` and `competency`

| Code | Label | Kind | In reports | Linkable | Deletable | Tone |
| --- | --- | --- | --- | --- | --- | --- |
| `draft` | Draft | DRAFT | no | no | **yes** | neutral |
| `active` | Active | INTERMEDIATE | **yes** | **yes** | no | success |
| `archived` | Retired | ARCHIVED | no | no | no | muted |

| Verb | Transition | `permission_action` | `requires_comment` | Gate |
| --- | --- | --- | --- | --- |
| Activate | `draft -> active` | `approve` | no | competency : at least one satisfying course (RG-TRN-03) |
| Retire | `active -> archived` | `approve` | **yes** | |
| Retire | `draft -> archived` | `update` | **yes** | |

### 3.2 `training_campaign`

Same steps and transitions as `acknowledgement_campaign` (module 7 §3.3) : `draft` (Draft), `running` (Running, reportable), `closed` (Closed, reportable), `archived` (Archived). Launch (`approve`) resolves the audience and notifies the addressees; Close (`update`) expires pending rows; Archive (`approve`, comment).

---

## 4. Permissions and access control

`PERMISSION_REGISTRY` gains a `training` module (`MODULE_LABELS["training"] = _("Training")`) with three features, each with `create`, `read`, `update`, `delete`, `approve` :

| Feature | Covers |
| --- | --- |
| `training.course` | The catalogue : create, edit, activate / retire, delete a draft course |
| `training.competency` | Competencies and the matrix (`read` gives the matrix) |
| `training.campaign` | Campaigns, enrolments, recording completions, imports, excusing (`update`); launch and archive (`approve`) |

Self-attestation on one's own row needs no permission (RG-TRN-08). System groups follow the platform filters (Super Administrateur / Administrateur : all; RSSI / DPO : all but delete; Contributeur : read, create, update; Auditeur / Lecteur : read).

---

## 5. API

Base path `/api/v1/training/`. House pattern.

| Method | Path | Description |
| --- | --- | --- |
| `GET` / `POST` | `courses/` | List (filters `status`, `course_type`, `delivery`, `scope_id`) / create |
| `GET` / `PUT` / `PATCH` / `DELETE` | `courses/{id}/` | |
| `GET` / `POST` | `courses/{id}/transition/` | |
| `GET` / `POST` | `competencies/` | List (filters `status`, `role_id`, `group_id`, `scope_id`) / create |
| `GET` / `PUT` / `PATCH` / `DELETE` | `competencies/{id}/` | |
| `GET` / `POST` | `competencies/{id}/transition/` | |
| `GET` | `competencies/{id}/matrix/` | Per required person : status, latest completion, valid until |
| `GET` | `matrix/` | Whole matrix (filters `scope_id`, `role_id`, `user_id`, `status`) |
| `GET` / `POST` | `campaigns/` | List (filters `status`, `course_id`, `due_before`) / create |
| `GET` / `PATCH` / `DELETE` | `campaigns/{id}/` | Edit / delete a draft |
| `GET` / `POST` | `campaigns/{id}/transition/` | Launch, close, archive |
| `POST` | `campaigns/{id}/add-newcomers/` | RG-TRN-05 |
| `POST` | `campaigns/{id}/import/` | RG-TRN-12 : multipart CSV, `dry_run=true|false` |
| `GET` | `enrolments/` | Rows the caller may read, plus their own |
| `GET` | `enrolments/mine/` | The caller's rows, pending first |
| `POST` | `enrolments/{id}/complete/` | Trainer recording (`completed_on`, `score`) |
| `POST` | `enrolments/{id}/self-attest/` | Addressee, when the course allows it |
| `POST` | `enrolments/{id}/excuse/` | With a reason |

---

## 6. MCP tools

`_register_training_tools()`, a `TOPIC_TRAINING` help topic, the `CRSE` / `CMPT` / `TRCA` prefixes in `HELP_TEXT`.

- `_register_crud` for `training_course`, `competency`, `training_campaign` (with `m2m_fields` for scopes, requirements, policies, roles, groups, satisfying courses and the audience).
- `record_training_completion(enrolment_id, completed_on, score=None)`, `excuse_enrolment(enrolment_id, reason)`, `add_campaign_newcomers(campaign_id)`.
- `import_training_completions(campaign_id, csv_text, dry_run=True)` (RG-TRN-12; CSV as text).
- `get_competency_matrix(scope_id=None, role_id=None, user_id=None, status=None)`, `get_campaign_progress(campaign_id)` (shared name space : `get_training_campaign_progress`).
- `list_my_trainings()` and `self_attest_training(enrolment_id)`.

Assistant catalogue : read-only entries for the catalogue, the matrix and campaign progress.

---

## 7. Notifications

| Event | Recipients | Channel |
| --- | --- | --- |
| `TRAINING_REQUESTED` : launch, or newcomer added | The addressee | In-app, email |
| `TRAINING_REMINDER` : daily sweep, 7 days before `due_date` and the day after it | Addressees with a pending row | In-app, email |
| `COMPETENCY_EXPIRING` : daily sweep, a competency of the person turns `expiring` (once per completion) | The person, and the owner of the competency | In-app, email |

---

## 8. User interface

- **Sidebar** : a new **Training** section after Documents : *Courses*, *Competencies*, *Campaigns*, *Matrix*. Everyone sees *My trainings* in the user menu, with a count badge of pending enrolments.
- **Course list / detail** : type, delivery, duration, validity, provider, the competencies it satisfies, its campaigns, linked requirements and policies.
- **Competency list / detail** : required for (roles, groups), satisfied by (courses), validity, coverage KPI, the per-person table (status badge, latest completion, valid until).
- **Campaign list / detail** : the documents campaign anatomy (stepper, rail : audience, completed, pending, rate), the enrolment table with filters, *Record completions* (a drawer listing pending rows with a date and score per row, bulk), *Import CSV* (upload, dry-run table, confirm), *Add newcomers*, *Excuse*.
- **Matrix** (`/training/matrix/`) : rows = persons, columns = competencies, cells = status badge; filters on scope, role, status; CSV export.
- **My trainings** : my pending enrolments (with *I have completed this training* when self-attestation is allowed), my competencies with their validity, my history.

Platform surfaces : global search, calendar (`training` category : campaign due dates and session dates), dashboard widget *Training* (running campaigns with rate, competency coverage, expired competencies), kanban (my pending enrolments in *To do*), predefined indicators `training_completion_rate` and `competency_coverage`, help banners, the management review card (RG-TRN-20).

---

## 9. Technical considerations

### 9.1 App wiring checklist

- [ ] The audience engine in `core/audience.py`, adopted by `documents.AcknowledgementCampaign` / `PolicyAcknowledgement` with no behaviour change (the module 7 tests pass unchanged) and a documents migration limited to related-name changes.
- [ ] `INSTALLED_APPS` gains `"training"`; lifecycles imported in `ready()`; models, admin, migrations; permission migration; notification types.
- [ ] Navigation, module accent, sidebar, user menu entry.
- [ ] Calendar, dashboard widget, kanban, search, indicators, management review card.
- [ ] REST, MCP, assistant catalogue; generated reference.
- [ ] `training_sweep` (reminders, expiring competencies) scheduled with the other sweeps.
- [ ] Seed : a Voltara catalogue (annual awareness, phishing simulation, secure development, incident handling, NIS2 management training), competencies on the seed roles, two closed campaigns, one running with mixed rows, one import, expired and expiring competencies.
- [ ] Translations, help banners, user guide, README, CHANGELOG.

### 9.2 Security and audit

- The CSV import parses with the standard `csv` module, rejects files over 2 MB or 10 000 lines, never evaluates formulas, and records the file's SHA-256 on every row it changed.
- Enrolment rows are write-once (RG-TRN-07), history-tracked, never deletable while the campaign exists.
- The matrix CSV export escapes cells starting with `=`, `+`, `-`, `@` (formula injection).

---

## 10. Acceptance criteria

- [ ] Launching a campaign creates exactly one row per resolved addressee; rows are immutable once completed, failed, excused or expired.
- [ ] A self-attestation is refused when the course does not allow it, and from anyone but the addressee.
- [ ] A score below the pass mark fails the row.
- [ ] An import dry run changes nothing; its confirmation completes only pending rows of persons in the audience, and reports the rest.
- [ ] The matrix status follows the latest valid completion of any satisfying course and the course validity.
- [ ] The documents acknowledgement campaigns behave exactly as before on the shared engine.
- [ ] Scope tenancy, light / dark, desktop / mobile, translations, generated reference.

---

## 11. Out of scope for v0.37.0

- Hosting course content (videos, quizzes, SCORM / xAPI packages) : Cairn records that training happened, it does not deliver it.
- Pulling completions from an LMS or a phishing platform through their APIs (the CSV import covers the exchange).
- Individual development plans, training budgets and costs.
- Experience and education records as alternative evidence of competence (clause 7.2 b) beyond training; a later *competence evidence* entity can add them.
