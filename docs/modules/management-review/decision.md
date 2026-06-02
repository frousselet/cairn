# ManagementReviewDecision

`reports.models.management_review.ManagementReviewDecision`

Structured decision output required by ISO 27001:2022 clause 9.3.3, feeding the review minutes and seeding downstream action plans.

Capture structurée des décisions exigées par la clause 9.3.3. Sert à produire le bloc « Décisions » du compte rendu et alimente automatiquement les plans d'actions.

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| `id` | UUID | PK | |
| `reference` | string | auto (préfixe `DECS`), unique | ex. `DECS-1` |
| `review` | FK → ManagementReview | requis, CASCADE | Revue d'origine |
| `category` | enum | requis | `improvement`, `isms_change`, `resource_allocation`, `risk_acceptance`, `objective_adjustment`, `policy_update`, `other` |
| `input_clause` | enum | optionnel | Entrée 9.3.2 à laquelle se rattache la décision (`a`–`g`) |
| `title` | string | requis, max 255 | Intitulé synthétique |
| `description` | text | requis | Texte complet de la décision |
| `rationale` | text | optionnel | Justification, éléments de contexte |
| `owner` | FK → User | requis | Responsable de la mise en œuvre |
| `due_date` | date | requis | Échéance |
| `priority` | enum | requis | `low`, `medium`, `high`, `critical` |
| `status` | enum | requis | `pending`, `in_progress`, `implemented`, `cancelled` |
| `implemented_at` | date | optionnel | Date de mise en œuvre effective |
| `implementation_evidence` | text | optionnel | Preuve (lien vers document, URL) |
| `linked_action_plan` | FK → ComplianceActionPlan | optionnel, SET_NULL | Plan d'action généré depuis cette décision |
| `linked_treatment_plan` | FK → RiskTreatmentPlan | optionnel, SET_NULL | Plan de traitement généré |
| `linked_objective` | FK → Objective | optionnel, SET_NULL | Objectif SSI créé/ajusté |
| `linked_isms_change` | FK → IsmsChange | optionnel, SET_NULL | Changement SMSI associé |
| `created_at`, `updated_at` | datetime | auto | |

**Historique** : `HistoricalRecords`.

**Règles de gestion** :

- Une revue ne peut passer en `closed` que si **toutes ses décisions** ont `owner` ET `due_date` renseignés.
- Lorsqu'une décision passe à `implemented`, si `linked_action_plan` est renseigné, son statut doit être `CLOSED` ou `VALIDATED` (garde-fou métier, avertissement UI non bloquant).
- Une action « Créer un plan d'action depuis cette décision » génère un `ComplianceActionPlan` pré-rempli et renseigne `linked_action_plan` + `originating_review` (cf. [README.md](README.md#modifications-de-modèles-existants)).
