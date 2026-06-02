# ComplianceAssessment

`compliance.models.assessment.ComplianceAssessment`

Campagne d'évaluation de conformité pour un [Framework](framework.md) donné.

## Entité : ComplianceAssessment (Évaluation de conformité)

Représente une campagne d'évaluation de conformité pour un référentiel donné. Permet de conserver l'historique des évaluations successives.

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-généré | Identifiant unique |
| `framework_id` | relation | FK → Framework, requis | Référentiel évalué |
| `name` | string | requis, max 255 | Intitulé de l'évaluation (ex. « Évaluation annuelle 2026 ») |
| `description` | text | optionnel | Contexte et objectif de l'évaluation |
| `assessment_date` | date | requis | Date de réalisation |
| `assessor_id` | relation | FK → User, requis | Évaluateur principal |
| `methodology` | text | optionnel | Méthodologie utilisée |
| `overall_compliance_level` | decimal | calculé, 0-100 | Niveau de conformité global (%) |
| `total_requirements` | integer | calculé | Nombre total d'exigences applicables |
| `compliant_count` | integer | calculé | Nombre d'exigences conformes |
| `partially_compliant_count` | integer | calculé | Nombre d'exigences partiellement conformes |
| `non_compliant_count` | integer | calculé | Nombre d'exigences non conformes |
| `not_assessed_count` | integer | calculé | Nombre d'exigences non évaluées |
| `status` | enum | requis | `draft`, `in_progress`, `completed`, `validated`, `archived` |
| `validated_by` | relation | FK → User, optionnel | Validateur |
| `validated_at` | datetime | optionnel | Date de validation |
| `results` | relation | O2M → AssessmentResult | Résultats par exigence |
| `review_date` | date | optionnel | Prochaine date de revue |
| `created_by` | relation | FK → User | Créateur |
| `created_at` | datetime | auto | Date de création |
| `updated_at` | datetime | auto | Date de dernière modification |

## AssessmentResult

Sous-entité : AssessmentResult (Résultat d'évaluation par exigence)

Représente le résultat d'évaluation d'une exigence dans le cadre d'une campagne d'évaluation.

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-généré | Identifiant unique |
| `assessment_id` | relation | FK → ComplianceAssessment, requis | Évaluation parente |
| `requirement_id` | relation | FK → Requirement, requis | Exigence évaluée |
| `compliance_status` | enum | requis | `not_assessed`, `non_compliant`, `partially_compliant`, `compliant`, `not_applicable` |
| `compliance_level` | integer | optionnel, 0-100 | Niveau de conformité (%) |
| `evidence` | text | optionnel | Preuves constatées |
| `gaps` | text | optionnel | Écarts identifiés |
| `observations` | text | optionnel | Observations complémentaires |
| `assessed_by` | relation | FK → User, requis | Évaluateur |
| `assessed_at` | datetime | requis | Date et heure de l'évaluation |
| `attachments` | relation | O2M → Attachment | Pièces jointes (preuves documentaires) |
| `created_at` | datetime | auto | Date de création |
| `updated_at` | datetime | auto | Date de dernière modification |

> Contrainte d'unicité : le couple (`assessment_id`, `requirement_id`) doit être unique.
