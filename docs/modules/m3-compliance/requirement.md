# Requirement

`compliance.models.requirement.Requirement`

Exigence individuelle extraite d'un [Framework](framework.md), unité élémentaire d'évaluation de la conformité.

## Entité : Requirement (Exigence)

Représente une exigence individuelle extraite d'un référentiel. C'est l'unité élémentaire d'évaluation de la conformité.

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-généré | Identifiant unique |
| `framework_id` | relation | FK → Framework, requis | Référentiel parent |
| `section_id` | relation | FK → Section, optionnel | Section de rattachement |
| `reference` | string | requis | Numéro de l'exigence (ex. « A.5.1.1 », « Art. 32.1.a ») |
| `name` | string | requis, max 500 | Intitulé court de l'exigence |
| `description` | text | requis | Texte complet de l'exigence |
| `guidance` | text | optionnel | Recommandations de mise en œuvre / notes d'interprétation |
| `type` | enum | requis | `mandatory`, `recommended`, `optional` |
| `category` | enum | optionnel | `organizational`, `technical`, `physical`, `legal`, `human`, `other` |
| `is_applicable` | boolean | requis, défaut true | Applicable au périmètre |
| `applicability_justification` | text | optionnel | Justification de la non-applicabilité (DdA) |
| `compliance_status` | enum | requis | `not_assessed`, `non_compliant`, `partially_compliant`, `compliant`, `not_applicable` |
| `compliance_level` | integer | optionnel, 0-100 | Niveau de conformité (%) |
| `compliance_evidence` | text | optionnel | Preuves / éléments de conformité |
| `compliance_gaps` | text | optionnel | Écarts constatés |
| `last_assessment_date` | date | optionnel | Date de la dernière évaluation |
| `last_assessed_by` | relation | FK → User, optionnel | Dernier évaluateur |
| `owner_id` | relation | FK → User, optionnel | Responsable de la mise en conformité |
| `priority` | enum | optionnel | `low`, `medium`, `high`, `critical` |
| `target_date` | date | optionnel | Date cible de mise en conformité |
| `linked_measures` | relation | M2M → Measure | Mesures contribuant à la conformité (Module Mesures) |
| `linked_assets` | relation | M2M → EssentialAsset | Biens essentiels concernés (Module Actifs) |
| `linked_risks` | relation | M2M → Risk | Risques associés (Module Risques) |
| `linked_stakeholder_expectations` | relation | M2M → StakeholderExpectation | Attentes de PI associées (Module Contexte) |
| `mapped_requirements` | relation | M2M → Requirement (via RequirementMapping) | Exigences d'autres référentiels mappées |
| `order` | integer | requis | Ordre d'affichage au sein de la section |
| `status` | enum | requis | `active`, `deprecated`, `superseded` |
| `created_by` | relation | FK → User | Créateur |
| `created_at` | datetime | auto | Date de création |
| `updated_at` | datetime | auto | Date de dernière modification |

> Contrainte : la combinaison (`framework_id`, `reference`) doit être unique.
