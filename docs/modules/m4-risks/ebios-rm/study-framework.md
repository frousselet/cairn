# StudyFramework

`risks.models.ebios.study_framework.StudyFramework`

Formalise les pré-requis exigés par ANSSI avant l'atelier 1 : participants, référentiels, hypothèses, contraintes. Préfixe de référence : `EFRA`.

## 4.0.1 Entité : StudyFramework (Cadre de l'étude)

Formalise les pré-requis exigés par ANSSI avant l'atelier 1 : participants, référentiels, hypothèses, contraintes.

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| `id` | UUID | PK, auto | Identifiant unique |
| `assessment_id` | relation | FK -> [RiskAssessment](../risk-assessment.md), requis, unique | Appréciation parente (1 framework par appréciation) |
| `reference` | string | requis, unique, préfixe EFRA | Code (ex. EFRA-1) |
| `mission_statement` | text | requis | Description de la mission étudiée |
| `business_perimeter` | text | requis | Périmètre métier (activités, processus) |
| `technical_perimeter` | text | requis | Périmètre technique (biens supports, infrastructures) |
| `temporal_perimeter` | text | requis | Horizon temporel (date de début / fin d'étude) |
| `financial_envelope` | decimal | optionnel | Enveloppe budgétaire allouée |
| `participants` | M2M -> User | optionnel | Participants à l'étude |
| `participants_external` | json | optionnel | Liste de participants externes (nom, rôle, organisation) |
| `applicable_frameworks` | M2M -> Framework | optionnel | Référentiels applicables (ISO 27001, NIS2, RGPD, etc.) |
| `assumptions` | text | optionnel | Hypothèses retenues |
| `constraints` | text | optionnel | Contraintes (organisationnelles, techniques, légales) |
| `expected_deliverables` | text | optionnel | Livrables attendus |
| `status` | enum | requis | `draft`, `validated` |
| `created_by`, `created_at`, `updated_at` | - | auto | Standards `BaseModel` |
