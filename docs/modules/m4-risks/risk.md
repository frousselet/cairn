# Risk

`risks.models.risk.Risk`

Risque identifié, quelle que soit la méthodologie d'origine. Entité centrale du registre des risques.

## 2.5 Entité : Risk (Risque)

Représente un risque identifié, quelle que soit la méthodologie d'origine. C'est l'entité centrale du registre des risques.

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-généré | Identifiant unique |
| `assessment_id` | relation | FK → RiskAssessment, requis | Appréciation source |
| `reference` | string | requis, unique | Code de référence (ex. RSK-001) |
| `name` | string | requis, max 255 | Intitulé du risque |
| `description` | text | requis | Description narrative du scénario de risque |
| `risk_source` | enum | requis | `iso27005_analysis`, `ebios_strategic_scenario`, `ebios_operational_scenario`, `incident`, `audit`, `compliance`, `manual` |
| `source_entity_id` | UUID | optionnel | Identifiant de l'entité source (ISO27005Risk, StrategicScenario, etc.) |
| `source_entity_type` | string | optionnel | Type de l'entité source |
| `affected_essential_assets` | relation | M2M → EssentialAsset | Biens essentiels impactés |
| `affected_support_assets` | relation | M2M → SupportAsset | Biens supports concernés |
| `impact_confidentiality` | boolean | requis, défaut false | Impact sur la confidentialité |
| `impact_integrity` | boolean | requis, défaut false | Impact sur l'intégrité |
| `impact_availability` | boolean | requis, défaut false | Impact sur la disponibilité |
| `initial_likelihood` | integer | requis | Vraisemblance initiale (brute) : valeur sur l'échelle |
| `initial_impact` | integer | requis | Impact initial (brut) : valeur sur l'échelle |
| `initial_risk_level` | integer | calculé | Niveau de risque initial (via la matrice) |
| `current_likelihood` | integer | optionnel | Vraisemblance actuelle (après mesures existantes) |
| `current_impact` | integer | optionnel | Impact actuel |
| `current_risk_level` | integer | calculé | Niveau de risque actuel |
| `residual_likelihood` | integer | optionnel | Vraisemblance résiduelle (après traitement planifié) |
| `residual_impact` | integer | optionnel | Impact résiduel |
| `residual_risk_level` | integer | calculé | Niveau de risque résiduel |
| `treatment_decision` | enum | optionnel | `accept`, `mitigate`, `transfer`, `avoid`, `not_decided` |
| `treatment_justification` | text | optionnel | Justification de la décision de traitement |
| `risk_owner_id` | relation | FK → User, requis | Propriétaire du risque (décideur) |
| `linked_measures` | relation | M2M → Measure | Mesures existantes couvrant ce risque |
| `linked_requirements` | relation | M2M → Requirement | Exigences de conformité associées |
| `linked_incidents` | relation | M2M → Incident | Incidents liés |
| `priority` | enum | optionnel | `low`, `medium`, `high`, `critical` |
| `status` | enum | requis | `identified`, `analyzed`, `evaluated`, `treatment_planned`, `treatment_in_progress`, `treated`, `accepted`, `closed`, `monitoring` |
| `review_date` | date | optionnel | Prochaine date de revue |
| `created_by` | relation | FK → User | Créateur |
| `created_at` | datetime | auto | Date de création |
| `updated_at` | datetime | auto | Date de dernière modification |
