# ComplianceAssessment

`compliance.models.assessment.ComplianceAssessment`

Campagne d'évaluation de conformité, **multi-référentiels**, pour un ou plusieurs [Framework](framework.md).

## Champs

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-généré | Identifiant unique |
| `reference` | string | auto-généré `CAST-N`, unique | Référence métier |
| `scopes` | relation | M2M -> Scope | Périmètres SMSI couverts |
| `frameworks` | relation | M2M -> Framework | Référentiels évalués dans cette campagne. L'implémentation est multi-référentielle (un audit peut couvrir ISO 27001 + RGPD simultanément), divergence assumée vs la spec d'origine mono-référentielle (voir l'écart documenté plus bas). |
| `name` | string | requis, max 255 | Intitulé de l'évaluation (ex. « Évaluation annuelle 2026 ») |
| `description` | text | optionnel, HTML | Contexte et objectif de l'évaluation |
| `limitations` | text | optionnel, HTML | Limitations / périmètre exclu / réserves de l'évaluation. Remplace le champ `methodology` de la spec d'origine ; la méthodologie est plutôt portée au niveau du framework ou de la documentation d'audit. |
| `assessment_start_date` | date | optionnel | Début de la période d'audit |
| `assessment_end_date` | date | optionnel | Fin de la période d'audit. La spec d'origine n'avait qu'une seule `assessment_date` ; l'implémentation utilise une période pour capter les audits qui s'étalent sur plusieurs jours / semaines. |
| `assessor` | relation | FK -> User, requis, PROTECT | Évaluateur principal (lead assessor) |
| `overall_compliance_level` | decimal(5,2) | calculé, 0-100 | Niveau de conformité global (%). Recalculé par `recalculate_counts()`. Exclut les `NOT_APPLICABLE` du numérateur et du dénominateur (issue #46). |
| `total_requirements` | integer | calculé | Nombre total d'exigences applicables couvertes |
| `compliant_count` | integer | calculé | Nombre d'exigences `compliant` |
| `major_non_conformity_count` | integer | calculé | Nombre d'exigences `major_non_conformity` |
| `minor_non_conformity_count` | integer | calculé | Nombre d'exigences `minor_non_conformity` |
| `observation_count` | integer | calculé | Nombre d'exigences `observation` |
| `improvement_opportunity_count` | integer | calculé | Nombre d'exigences `improvement_opportunity` |
| `strength_count` | integer | calculé | Nombre d'exigences `strength` |
| `evaluated_count` | integer | calculé | Nombre d'exigences `evaluated` (placeholder) |
| `not_assessed_count` | integer | calculé | Nombre d'exigences `not_assessed` |
| `not_applicable_count` | integer | calculé | Nombre d'exigences `not_applicable` |
| `status` | enum | requis, défaut `draft` | Voir « Cycle de vie » ci-dessous |
| `results` | reverse FK | O2M -> AssessmentResult | Résultats par exigence |
| `findings` | reverse M2M | <- compliance.Finding (`Finding.assessment`) | Constats d'audit rattachés |
| `is_approved` / `approved_by` / `approved_at` | bool / FK -> User / datetime | optionnel | Indicateur d'approbation, axe orthogonal au `status` (voir « Cycle de vie ») |
| `version` | int | auto-incrémenté | Bumpé à chaque modification majeure |
| `tags` | relation | M2M -> Tag | |
| `created_by` | relation | FK -> User | Créateur |
| `created_at` / `updated_at` | datetime | auto | |

## Cycle de vie

`status` suit le workflow réel : `draft -> planned -> in_progress -> completed -> closed`, plus `cancelled` comme branche terminale accessible depuis `draft` et `planned`. Une fois `completed` ou `closed`, l'évaluation ne peut plus reculer.

```text
  draft -> planned -> in_progress -> completed -> closed
    \         \
     +---------+----> cancelled  (terminal)
```

| Statut | Sens |
|---|---|
| `draft` | Brouillon de configuration : champs métier modifiables, pas encore lancée |
| `planned` | Configuration validée, planifiée, en attente de démarrage |
| `in_progress` | En cours : les `AssessmentResult` sont en train d'être remplis par l'évaluateur |
| `completed` | Évaluation conduite, résultats saisis, en attente de validation / clôture |
| `closed` | Terminée et clôturée (terminal). Le report RC-06 (`recalculate_counts`) est déclenché ici |
| `cancelled` | Évaluation annulée (terminal). Aucun report ne se déclenche |

### Validation et approbation

`is_approved` est un **axe orthogonal** au `status`, capté par l'action `approve_compliance_assessment` (REST `POST /assessments/<uuid>/approve/`, MCP `approve_compliance_assessment`). L'approbation peut être posée à n'importe quel moment (typiquement quand l'évaluation est `completed` ou `closed`) et représente la validation formelle du résultat par un approbateur (RSSI, DPO, comité de direction).

Le statut `validated` listé dans la spec d'origine M3 §2.4 n'existe pas dans l'enum implémentée : la « validation » est portée par le couple (`status=closed`, `is_approved=true`). Cette séparation a été retenue pour permettre :

- de **clôturer** une évaluation sans la valider formellement (audit interne récurrent dont les résultats sont consommés tout de suite sans signature d'approbateur) ;
- d'**approuver** une évaluation à plusieurs niveaux successifs (l'auditeur la passe en `completed`, le RSSI la passe en `closed`, le DPO ou le comité l'approuve plus tard via `is_approved`).

Le statut `archived` de la spec d'origine n'a pas été repris non plus : `closed` joue le rôle terminal, et un éventuel besoin d'archivage explicite peut être ajouté ultérieurement par un drapeau ou un statut séparé sans casser le workflow actuel.

| Spec d'origine | Implémentation actuelle |
|---|---|
| `draft` | `draft` |
| `in_progress` | `planned` ou `in_progress` (l'implémentation distingue la planification de l'exécution) |
| `completed` | `completed` |
| `validated` | `closed` + `is_approved=true` |
| `archived` | `closed` (terminal). Pas de statut dédié pour l'instant |

### Transitions autorisées

`ComplianceAssessment.transition_to(new_status)` valide la transition contre `ASSESSMENT_STATUS_TRANSITIONS` (`compliance/constants.py`) :

```text
draft        -> planned, cancelled
planned      -> in_progress, cancelled
in_progress  -> completed
completed    -> closed
closed       -> (terminal)
cancelled    -> (terminal)
```

L'API REST `POST /assessments/<uuid>/transition/` et le MCP `update_compliance_assessment` (via le champ `status`) appliquent ces règles. Une transition non autorisée lève une `ValueError` reformatée en `400 Bad Request`.

### Effets de bord par transition

- `in_progress -> completed` : reset les `AssessmentResult.compliance_status` qui sont restés en `EVALUATED` sans finding rattaché vers `NOT_ASSESSED` (cohérence : un placeholder « évaluation planifiée » qui n'a pas reçu de constat redevient « non évalué »). Appelle `recalculate_counts()`.
- `completed -> closed` : déclenche `recalculate_counts()` (RC-06). Les `AssessmentResult` sont reportés sur les `Requirement` ; `Framework.last_assessment_date` est mis à jour avec `assessment_end_date`.

### Déclencheur RC-06

Le report des résultats sur les exigences (RC-06) est déclenché à la **clôture** (`completed -> closed`), pas à l'approbation. `approve_compliance_assessment` ne déclenche aucun calcul, c'est purement une signature de validation. Cette séparation permet de relire et corriger une évaluation closed avant de l'approuver sans que l'approbation ait à recalculer quoi que ce soit.

## Divergences par rapport à la spec d'origine

La spec M3 §2.4 décrivait une évaluation mono-référentielle, datée d'une seule date, portant un champ `methodology` et sans rattachement explicite au périmètre. L'implémentation a évolué sur ces quatre axes ; les choix sont actés.

### Multi-référentiel (`frameworks` M2M)

Une évaluation peut couvrir plusieurs référentiels simultanément. Cas d'usage : un audit annuel ISO 27001 + RGPD + une norme sectorielle (ex. HDS pour la santé) est une seule campagne, pas trois. Permet de mutualiser le travail terrain (les preuves recueillies pour ISO 27001 §A.5.34 servent aussi à l'article 32 du RGPD) et de partager une seule fenêtre d'audit auprès des audités.

**Impact sur RC-06.** À la clôture, `recalculate_counts()` propage chaque `AssessmentResult` vers son `Requirement` cible, peu importe le framework auquel cette exigence appartient. Tous les frameworks rattachés voient ainsi leur `Framework.compliance_level` recalculé, et leur `Framework.last_assessment_date` mis à jour avec l'`assessment_end_date` de la campagne.

Côté requête : `assessment.frameworks.all()` énumère les référentiels couverts ; `assessment.results.all()` énumère les résultats tous référentiels confondus ; pour scoper par référentiel utiliser `assessment.results.filter(requirement__framework=fw)`.

### Période d'audit (`assessment_start_date` / `assessment_end_date`)

La spec d'origine n'avait qu'une `assessment_date` ponctuelle. L'implémentation utilise une **période** car un audit s'étale typiquement sur plusieurs jours (cycle terrain + revue documentaire + restitution), parfois sur plusieurs semaines pour les frameworks lourds. La `assessment_end_date` sert de référence pour la fraîcheur (`Framework.last_assessment_date` reprend cette valeur à la clôture) ; la `assessment_start_date` documente le début de fenêtre pour les exports d'audit.

### `limitations` au lieu de `methodology`

La spec d'origine avait un champ `methodology` pour décrire la méthode d'audit. L'implémentation a remplacé par `limitations` (réserves, exclusions, portée non couverte). La méthodologie est plutôt portée au niveau de la documentation d'audit attachée (modèle de preuve, plan d'audit) ou au niveau du Framework (un framework ISO 27001 implique une méthodologie connue, inutile de la dupliquer à chaque campagne). `limitations` capte ce qui doit obligatoirement apparaître dans le rapport d'audit : « la salle serveur du site B n'a pas pu être inspectée », « le scope exclut les filiales acquises en 2025 ».

### Rattachement au périmètre (`scopes` M2M)

L'évaluation est `ScopedModel` et accepte `scope_ids` comme toutes les autres entités domaine (rattachement transverse RG-01). Permet de cloisonner les audits par périmètre SMSI : un audit du périmètre « France » ne pollue pas les KPI du périmètre « Allemagne ». Un audit transverse peut rester sans périmètre (liste vide).

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
