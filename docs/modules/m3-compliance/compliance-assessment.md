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

`compliance.models.assessment.AssessmentResult`

Résultat d'évaluation d'une exigence dans le cadre d'une campagne. Un résultat par couple `(assessment, requirement)` ; la contrainte d'unicité est encodée au niveau base.

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-généré | Identifiant unique |
| `assessment_id` | relation | FK -> ComplianceAssessment, requis, cascade | Évaluation parente |
| `requirement_id` | relation | FK -> Requirement, requis, cascade | Exigence évaluée |
| `compliance_status` | enum | requis, défaut `not_assessed` | Voir « Statuts de conformité » ci-dessous |
| `compliance_level` | integer | défaut 0, 0-100 | Niveau de conformité (%) |
| `finding` | text | optionnel, HTML | Constat d'audit. Remplace le couple `gaps` / `observations` de la spec d'origine ; la fusion correspond à l'usage réel : un évaluateur écrit un seul bloc qui décrit à la fois les écarts et les observations contextuelles. |
| `auditor_recommendations` | text | optionnel, HTML | Recommandations formulées par l'auditeur. Champ ajouté par l'implémentation pour capturer les pistes d'amélioration sans dupliquer la `compliance_finding` de la `Requirement`. |
| `evidence` | text | optionnel, HTML | Preuves constatées (citations de documents, captures, etc.) |
| `assessed_by` | relation | FK -> User, requis, PROTECT | Évaluateur |
| `assessed_at` | datetime | requis | Date et heure de l'évaluation |
| `attachments` | reverse FK | O2M -> [AssessmentResultAttachment](attachment.md) | Pièces jointes (preuves documentaires) |
| `created_at` / `updated_at` | datetime | auto | |

> Contrainte d'unicité : le couple (`assessment_id`, `requirement_id`) doit être unique.

### Statuts de conformité

`AssessmentResult.compliance_status` partage **exactement la même énumération à 11 valeurs** que `Requirement.compliance_status` : `compliance.constants.ComplianceStatus`. Voir [requirement.md § Statuts de conformité](requirement.md#statuts-de-conformité) pour la table complète et le mapping des statuts d'audit (`major_non_conformity`, `minor_non_conformity`, `observation`, `improvement_opportunity`, `strength`, `evaluated`) vers les valeurs de conformance utilisées par les agrégats RC-01 et RC-02.

La cohérence entre les deux énumérations est intentionnelle : un audit produit un résultat dont le `compliance_status` est directement reportable sur l'exigence cible sans table de mapping intermédiaire (voir RC-06 ci-dessous).

### Écarts par rapport à la spec d'origine

La spécification M3 §2.5 listait `gaps` (écarts) et `observations` (observations) comme deux champs distincts, plus un `compliance_status` réduit à 5 valeurs (`not_assessed`, `non_compliant`, `partially_compliant`, `compliant`, `not_applicable`). L'implémentation a évolué pour aligner le résultat sur le vocabulaire d'audit ISO 19011 et sur le module Audits :

- `gaps` + `observations` sont fusionnés en un seul champ `finding` (mêmes raisons que `Requirement.compliance_finding`, voir #39).
- Un champ `auditor_recommendations` est ajouté pour capter les recommandations distinctement du constat (le `finding` décrit ce qui est, les `auditor_recommendations` ce qu'il faudrait faire).
- `compliance_status` est étendu aux 6 valeurs d'audit (`evaluated`, `major_non_conformity`, `minor_non_conformity`, `observation`, `improvement_opportunity`, `strength`) en plus des 5 valeurs de conformance.

Le choix d'aligner ces écarts a été acté avec la résolution de #44 : la spec suit désormais l'implémentation.

### RC-06 (carry-over résultat -> exigence)

À la clôture / validation d'une `ComplianceAssessment`, `recalculate_counts()` propage chaque `AssessmentResult` vers l'exigence ciblée :

1. Si `result.compliance_status` vaut `not_assessed`, l'exigence cible n'est **pas** modifiée (préservation des évaluations antérieures, issue #45 résolue).
2. Si `result.compliance_status` vaut `evaluated` (placeholder « évaluation planifiée »), on recherche dans l'historique de cette exigence le dernier résultat **réellement évalué** sur n'importe quelle évaluation du même framework et on reporte celui-ci à la place.
3. Sinon, `result.compliance_status` et `result.compliance_level` sont reportés tels quels sur l'exigence ; `Requirement.last_assessment_date` et `Requirement.last_assessed_by` sont mis à jour avec les valeurs du résultat.

L'enum partagé garantit qu'aucun mapping n'est nécessaire entre résultat et exigence : un `major_non_conformity` côté résultat devient un `major_non_conformity` côté exigence, qui se voit ensuite agrégé en `non_compliant` dans les moyennes RC-01 / RC-02 via le mapping documenté côté Requirement.

### Lien avec le module Audits

Les `Finding` du module Audits peuvent être rattachés à un `AssessmentResult` via `Finding.requirements`. La méthode `ComplianceAssessment.apply_findings_to_results()` aligne ensuite le `compliance_status` de chaque résultat sur le statut le plus sévère parmi les findings rattachés (selon `FINDING_SEVERITY_ORDER` dans `compliance.constants`). Cela permet à un audit de produire des findings dont la sévérité écrase mécaniquement le statut d'un résultat sans saisie manuelle.
