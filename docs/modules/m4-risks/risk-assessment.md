# RiskAssessment

`risks.models.risk_assessment.RiskAssessment`

Campagne d'appréciation des risques conduite selon l'une ou l'autre méthodologie (ISO 27005 ou EBIOS RM). Entité racine qui regroupe tous les éléments d'analyse.

## 2.1 Entité : RiskAssessment (Appréciation des risques)

Représente une campagne d'appréciation des risques, conduite selon l'une ou l'autre méthodologie. C'est l'entité racine qui regroupe tous les éléments d'analyse.

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-généré | Identifiant unique |
| `scope_id` | relation | FK → Scope, requis | Périmètre rattaché |
| `reference` | string | requis, unique | Code de référence (ex. RA-2026-001) |
| `name` | string | requis, max 255 | Intitulé de l'appréciation |
| `description` | text | optionnel | Description et contexte |
| `methodology` | enum | requis | `iso27005`, `ebios_rm` |
| `assessment_date` | date | requis | Date de réalisation |
| `assessor_id` | relation | FK → User, requis | Responsable de l'appréciation |
| `team_members` | relation | M2M → User | Membres de l'équipe d'appréciation |
| `risk_criteria_id` | relation | FK → RiskCriteria, requis | Critères de risque appliqués |
| `status` | enum | requis | `draft`, `in_progress`, `completed`, `validated`, `archived` |
| `validated_by` | relation | FK → User, optionnel | Validateur |
| `validated_at` | datetime | optionnel | Date de validation |
| `next_review_date` | date | optionnel | Prochaine date de revue |
| `summary` | text | optionnel | Synthèse des résultats |
| `created_by` | relation | FK → User | Créateur |
| `created_at` | datetime | auto | Date de création |
| `updated_at` | datetime | auto | Date de dernière modification |
