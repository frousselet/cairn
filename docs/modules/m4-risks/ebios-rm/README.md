# Module 4 bis - EBIOS Risk Manager

## Spécifications fonctionnelles et techniques (conformité ANSSI EBIOS RM v1.5 - 2024)

**Version :** 1.0
**Date :** 29 mai 2026
**Statut :** Draft
**Remplace :** Section 4 du document M4 (voir [../README.md](../README.md))

---

## Entities in this sub-module

- **W0 : Cadre de l'étude**
  - [StudyFramework](study-framework.md) (EFRA)
  - [EbiosWorkshopProgress](workshop-progress.md) (EWSP)
- **W1 : Socle de sécurité**
  - [SecurityBaseline](security-baseline.md) (EBSL)
  - [FearedEvent](feared-event.md) (EFER)
  - [BaselineGap](baseline-gap.md) (EBGP)
- **W2 : Sources de risque et objectifs visés**
  - [RiskSource](risk-source.md) (ERSC)
  - [TargetedObjective](targeted-objective.md) (ETOV)
  - [RiskSourceObjectivePair](sr-ov-pair.md) (ESOV)
- **W3 : Écosystème et scénarios stratégiques**
  - [EcosystemStakeholder](ecosystem-stakeholder.md) (EECS)
  - [StrategicScenario](strategic-scenario.md) (ESTS)
  - [AttackPathStep](attack-path-step.md) (EAPS)
- **W4 : Scénarios opérationnels**
  - [MitreAttackTechnique](mitre-attack-technique.md)
  - [OperationalScenario](operational-scenario.md) (EOPS)
  - [AttackTechnique](attack-technique.md) (EATT)
- **W5 : Synthèse et PACS**
  - [EbiosSummary](ebios-summary.md) (ESUM)
  - [PACSMeasure](pacs-measure.md) (EPAC)

---

## 1. Présentation générale

### 1.1 Objectif du module

Le module **EBIOS Risk Manager** implémente la méthode d'appréciation et de traitement des risques numériques publiée par l'ANSSI (Agence Nationale de la Sécurité des Systèmes d'Information). Il vise une **conformité stricte au guide ANSSI EBIOS RM v1.5 (édition 2024)**, qui actualise la méthode v1.0 (2018) avec une intégration explicite de MITRE ATT&CK pour la modélisation des scénarios opérationnels et un raffinement des grilles de scoring.

Ce document est autonome : sa lecture ne suppose pas la connaissance préalable du document M4 (voir [../README.md](../README.md)). Il s'inscrit néanmoins dans le module 4 « Gestion des Risques » et réutilise le socle commun (registre des risques, critères, traitement, acceptation) défini dans M4 §2.

### 1.2 Positionnement vs ISO 27005

EBIOS RM et ISO 27005:2022 cohabitent dans le module 4 selon le principe suivant :

| Aspect | ISO 27005 | EBIOS RM |
|---|---|---|
| Approche | Analyse par triplet menace × vulnérabilité × bien | Approche par scénarios construits depuis les sources de risque |
| Granularité | Risque atomique sur un bien | Scénario stratégique haut niveau + scénario opérationnel technique |
| Cycle | Itération unique par appréciation | 5 ateliers chaînés, cycle stratégique et cycle opérationnel itératifs |
| Sortie commune | Risk (registre) | Risk (registre) |

Les deux méthodes alimentent un **registre des risques unifié** (entité [`Risk`](../risk.md) du socle commun). Une appréciation ([`RiskAssessment`](../risk-assessment.md)) est conduite selon une méthodologie unique : champ `methodology` à `iso27005` ou `ebios_rm`.

### 1.3 Périmètre fonctionnel

Le sous-module EBIOS RM couvre :

- **Atelier 0 - Cadre de l'étude** : périmètre, participants, référentiels applicables, hypothèses, contraintes temporelles et financières (non décrit comme atelier formel dans ANSSI v1.5 mais exigé en pré-requis).
- **Atelier 1 - Socle de sécurité** : valeurs métier, biens supports, événements redoutés, écarts au socle.
- **Atelier 2 - Sources de risque et objectifs visés** : SR/OV, évaluation, couples retenus.
- **Atelier 3 - Scénarios stratégiques** : cartographie de la menace numérique de l'écosystème, chemins d'attaque haut niveau.
- **Atelier 4 - Scénarios opérationnels** : modes opératoires détaillés, alignés MITRE ATT&CK.
- **Atelier 5 - Traitement du risque** : stratégie, PACS (Plan d'Amélioration Continue de la Sécurité), cartographie avant/après, risques résiduels.

### 1.4 Dépendances avec les autres modules

| Module cible | Nature de la dépendance |
|---|---|
| Module 1 - Contexte | Le `Scope` ancre l'appréciation. Les `Activity` et `Stakeholder` alimentent l'atelier 1 (valeurs métier) et 3 (écosystème). |
| Module 2 - Gestion des actifs | Les `EssentialAsset` portent les besoins de sécurité DIC. Les `SupportAsset` et `AssetDependency` structurent l'atelier 4. |
| Module 3 - Conformité | Les `Framework` et `Requirement` constituent le socle de sécurité référentiel (atelier 1). Un `BaselineGap` peut référencer un `Requirement`. |
| Module 4 - Socle risques | Les [`RiskCriteria`](../risk-criteria.md), [`Risk`](../risk.md), [`RiskTreatmentPlan`](../risk-treatment-plan.md), [`RiskAcceptance`](../risk-acceptance.md) du socle commun sont réutilisés. Les scénarios stratégiques et opérationnels se consolident en `Risk`. |
| Fournisseurs | Les `Supplier` apparaissent comme parties prenantes de l'écosystème (atelier 3). |

### 1.5 Intégration au registre des risques unifié

La consolidation vers le registre unifié obéit aux règles suivantes :

- Un [`StrategicScenario`](strategic-scenario.md) peut être consolidé en [`Risk`](../risk.md) (champ `Risk.risk_source = ebios_strategic_scenario`).
- Un [`OperationalScenario`](operational-scenario.md) peut être consolidé en [`Risk`](../risk.md) (champ `Risk.risk_source = ebios_operational_scenario`).
- En pratique, la consolidation s'opère majoritairement au niveau opérationnel (atelier 4) car il porte la vraisemblance technique mesurée.
- Les [`PACSMeasure`](pacs-measure.md) (mesures du PACS) sont reliées à un ou plusieurs [`RiskTreatmentPlan`](../risk-treatment-plan.md) du socle commun.

---

## 2. Concepts ANSSI EBIOS RM v1.5

### 2.1 Vocabulaire et glossaire

| Terme ANSSI | Code | Définition |
|---|---|---|
| Valeur métier | - | Service, activité ou information à protéger. Modélisé par `context.Activity` et `assets.EssentialAsset`. |
| Bien support | - | Composant technique, organisationnel ou humain qui porte les valeurs métier. Modélisé par `assets.SupportAsset`. |
| Événement redouté (ER) | EFER | Effet préjudiciable sur une valeur métier exprimé par une atteinte à un critère DIC. |
| Source de risque (SR) | ERSC | Élément (personne, groupe, organisation, État, phénomène) à l'origine d'un risque. |
| Objectif visé (OV) | ETOV | Finalité poursuivie par une SR (ex. enrichissement, destruction, espionnage). |
| Couple SR/OV | ESOV | Association formelle SR x OV évaluée en pertinence. |
| Partie prenante écosystème | EECS | Acteur de l'écosystème pouvant constituer un vecteur d'attaque. |
| Scénario stratégique | ESTS | Chemin d'attaque haut niveau depuis une SR vers un OV en passant par l'écosystème. |
| Scénario opérationnel | EOPS | Déclinaison technique d'un scénario stratégique avec modes opératoires sur les biens supports. |
| Gravité | - | Niveau d'impact d'un événement redouté ou d'un scénario (échelle 1 à 4 ou 1 à 5). |
| Vraisemblance | - | Probabilité de réalisation. ANSSI utilise l'échelle V1-V4 pour le niveau opérationnel. |
| PACS | EPAC | Plan d'Amélioration Continue de la Sécurité. Synthèse des mesures issues de l'atelier 5. |
| Socle de sécurité | EBSL | Ensemble des règles, mesures et référentiels constituant la base sécuritaire applicable. |
| DIC | - | Confidentialité, Intégrité, Disponibilité. Critères de sécurité primaires. |
| Cycle stratégique | - | Boucle longue (annuelle) de réévaluation des ateliers 1 à 3 et 5. |
| Cycle opérationnel | - | Boucle courte (semestrielle) de réévaluation des ateliers 4 et 5. |

### 2.2 Les 5 ateliers et leurs livrables

| Atelier | Intitulé | Livrables ANSSI obligatoires | Porte de validation |
|---|---|---|---|
| W1 | Socle de sécurité | Liste des valeurs métier, liste des biens supports, événements redoutés, écarts au socle | Validation par la direction métier |
| W2 | Sources de risque | Catalogue SR/OV, couples SR/OV retenus avec justification | Validation par le RSSI |
| W3 | Scénarios stratégiques | Cartographie de la menace numérique de l'écosystème, scénarios stratégiques retenus | Validation par le RSSI |
| W4 | Scénarios opérationnels | Scénarios opérationnels avec modes opératoires (MITRE ATT&CK), évaluation V1-V4 | Validation par le RSSI |
| W5 | Traitement du risque | PACS, cartographie avant/après, registre des risques résiduels | Validation par la direction générale |

Une porte de validation ne peut être franchie que si l'atelier précédent est validé (état `validated`). Le système refuse la création d'entités d'un atelier supérieur si l'atelier inférieur n'est pas validé.

### 2.3 Cycle stratégique vs cycle opérationnel

EBIOS RM est itératif :

- **Cycle stratégique (long)** : reprise complète des ateliers 1, 2, 3 et 5. Déclenché par un changement majeur de contexte (nouvelle activité, fusion, évolution réglementaire). Cadence typique : annuelle.
- **Cycle opérationnel (court)** : reprise des ateliers 4 et 5 uniquement, en s'appuyant sur les sorties du cycle stratégique en cours. Cadence typique : semestrielle ou trimestrielle.

Le modèle [`EbiosWorkshopProgress`](workshop-progress.md) porte les champs `iteration_type` (strategic, operational) et `iteration_number` (entier incrémenté) pour tracer ces cycles.

### 2.4 Sources de risque vs objectifs visés

Une **source de risque** est l'auteur ou le vecteur du risque. Un **objectif visé** est l'intention de la SR. Une même SR peut poursuivre plusieurs OV, et un même OV peut être poursuivi par plusieurs SR. L'évaluation porte sur les **couples** SR/OV (ANSSI v1.5 §3.3).

Catégories de SR (énumération ANSSI) :

`state`, `organized_crime`, `terrorist`, `activist`, `competitor`, `employee`, `service_provider`, `amateur`, `natural`, `other`.

Catégories d'OV (énumération ANSSI) :

`lucrative`, `strategic`, `terrorist`, `ideological`, `revenge`, `ludic`, `other`.

### 2.5 Scénarios stratégiques vs scénarios opérationnels

| Aspect | Scénario stratégique | Scénario opérationnel |
|---|---|---|
| Niveau | Stratégique (qui, pourquoi, par où) | Technique (comment, sur quoi) |
| Granularité | Chemin d'attaque traversant l'écosystème | Séquence d'actions techniques |
| Acteurs | SR + parties prenantes écosystème | SR + biens supports |
| Évaluation | Gravité + vraisemblance stratégique | Gravité (héritée) + vraisemblance opérationnelle V1-V4 |
| Référentiel technique | - | MITRE ATT&CK Enterprise Matrix |
| Atelier | W3 | W4 |

Tout scénario opérationnel **doit** être rattaché à un scénario stratégique parent.

### 2.6 Cartographie de la menace numérique de l'écosystème

Concept central de l'atelier 3 ANSSI v1.5. Chaque partie prenante de l'écosystème est positionnée sur un graphe (zone de **contrôle**, zone de **surveillance**, zone de **danger**) selon son niveau de menace calculé.

La formule ANSSI est :

```
niveau_de_menace = (dependance * penetration) / (maturite * confiance)
```

Avec :
- `dependance` : niveau de dépendance de l'organisme vis-à-vis de la partie prenante (1 à 4).
- `penetration` : degré de pénétration de la partie prenante dans l'écosystème (1 à 4).
- `maturite` : maturité cyber de la partie prenante (1 à 4).
- `confiance` : niveau de confiance dans la partie prenante (1 à 4).

Seuils de zonage (paramétrables) :
- `niveau_de_menace < 0.5` : zone de **contrôle** (vert).
- `0.5 <= niveau_de_menace < 1.5` : zone de **surveillance** (orange).
- `niveau_de_menace >= 1.5` : zone de **danger** (rouge).

### 2.7 PACS (Plan d'Amélioration Continue de la Sécurité)

Le PACS est le livrable structurant de l'atelier 5. Il liste les **mesures** de sécurité décidées pour traiter les risques résiduels au-delà du socle existant. Chaque mesure est portée par une instance [`PACSMeasure`](pacs-measure.md) avec échéance, responsable, coût, gain attendu, statut, et lien vers un [`RiskTreatmentPlan`](../risk-treatment-plan.md) du socle commun.

### 2.8 Grilles de scoring ANSSI

**Grille A - Niveau de menace d'une SR** (atelier 2, agrégat motivation x ressources x activité, retour V1 à V4) :

| Motivation \ Ressources | Limitées | Modérées | Importantes | Illimitées |
|---|---|---|---|---|
| Faible | V1 | V1 | V2 | V2 |
| Modérée | V1 | V2 | V3 | V3 |
| Forte | V2 | V3 | V3 | V4 |
| Très forte | V2 | V3 | V4 | V4 |

L'activité (faible, moyenne, élevée) peut majorer d'un cran le niveau résultant (paramétrable).

**Grille B - Vraisemblance opérationnelle V1-V4** (atelier 4) :

| Code | Libellé | Critère ANSSI |
|---|---|---|
| V1 | Minimal | Réalisation peu vraisemblable. Pas de mode opératoire connu ou techniquement très difficile. |
| V2 | Significatif | Réalisation possible. Mode opératoire documenté mais nécessite des compétences spécifiques. |
| V3 | Fort | Réalisation probable. Mode opératoire éprouvé, accessible à un attaquant de niveau intermédiaire. |
| V4 | Maximal | Réalisation quasi certaine. Mode opératoire automatisé ou trivial. |

---

## 3. Architecture technique

### 3.1 Positionnement dans l'app `risks/`

Le sous-module EBIOS RM est implémenté dans l'app Django existante `risks/`. Les modèles EBIOS sont regroupés dans un sous-package dédié `risks/models/ebios/` (un fichier par modèle). Le `__init__.py` du sous-package réexporte les classes vers `risks.models` pour conserver une API stable.

```
risks/
  models/
    __init__.py            # réexporte tout
    risk.py                # existant
    risk_assessment.py     # existant
    risk_criteria.py       # existant
    iso27005_risk.py       # existant
    threat.py              # existant
    vulnerability.py       # existant
    treatment.py           # existant
    acceptance.py          # existant
    ebios/
      __init__.py
      study_framework.py
      workshop_progress.py
      security_baseline.py
      feared_event.py
      baseline_gap.py
      risk_source.py
      targeted_objective.py
      sr_ov_pair.py
      ecosystem_stakeholder.py
      strategic_scenario.py
      attack_path_step.py
      operational_scenario.py
      attack_technique.py
      mitre_attack.py
      ebios_summary.py
      pacs_measure.py
```

Les vues, formulaires, templates et API sont organisés en miroir : `risks/views/ebios/...`, `risks/forms/ebios.py`, `risks/templates/risks/ebios/...`, `risks/api/ebios/...`.

### 3.2 Intégration au socle commun

L'entité parente reste [`RiskAssessment`](../risk-assessment.md) (existante, M4 §2.1) avec `methodology = ebios_rm`. Les entités EBIOS sont rattachées via FK à `RiskAssessment` (directement ou indirectement). Aucune duplication des critères, du registre ou des plans de traitement : tout passe par les entités du socle commun.

### 3.3 Réutilisation des entités existantes

| Entité existante | Réutilisation EBIOS RM |
|---|---|
| `context.Scope` | Ancrage de l'appréciation. |
| `context.Activity` | Source des valeurs métier (atelier 1). |
| `context.Stakeholder` | FK optionnel depuis [`EcosystemStakeholder`](ecosystem-stakeholder.md) (atelier 3). |
| `assets.EssentialAsset` | Cible des événements redoutés (atelier 1) et des objectifs visés (atelier 2). |
| `assets.SupportAsset` | Cible des scénarios opérationnels (atelier 4). |
| `assets.AssetDependency` | Lit la cartographie technique pour suggérer les biens supports impactés. |
| `assets.Supplier` | Candidat naturel pour [`EcosystemStakeholder`](ecosystem-stakeholder.md) (atelier 3). |
| `compliance.Requirement` | FK depuis [`BaselineGap`](baseline-gap.md) (atelier 1). |
| [`risks.Risk`](../risk.md) | Cible de consolidation depuis [`StrategicScenario`](strategic-scenario.md) et [`OperationalScenario`](operational-scenario.md). |
| [`risks.RiskTreatmentPlan`](../risk-treatment-plan.md) | FK depuis [`PACSMeasure`](pacs-measure.md) (atelier 5). |
| [`risks.RiskCriteria`](../risk-criteria.md) | Source des échelles likelihood/impact et de la matrice de calcul. |

### 3.4 Workflow `EbiosWorkshopProgress`

À la création d'une appréciation `methodology = ebios_rm`, le système crée automatiquement **6 instances** de [`EbiosWorkshopProgress`](workshop-progress.md) (W0 à W5). Chaque instance porte un état (`not_started`, `in_progress`, `under_review`, `validated`, `rejected`) et alimente le stepper UI (pattern compliance/assessment_detail.html).

Une porte de validation est franchie par un appel POST `/risks/ebios/workshops/{id}/validate` qui :
1. Vérifie que les livrables obligatoires de l'atelier sont présents.
2. Vérifie que tous les ateliers précédents sont en état `validated`.
3. Passe l'état à `validated`, enregistre `validated_by` et `validated_at`.
4. Émet un webhook `risks.ebios.workshop_validated`.

### 3.5 Table récapitulative des préfixes de référence

| Entité EBIOS | Préfixe | Exemple |
|---|---|---|
| StudyFramework | EFRA | EFRA-1 |
| EbiosWorkshopProgress | EWSP | EWSP-1 |
| SecurityBaseline | EBSL | EBSL-1 |
| FearedEvent | EFER | EFER-1 |
| BaselineGap | EBGP | EBGP-1 |
| RiskSource | ERSC | ERSC-1 |
| TargetedObjective | ETOV | ETOV-1 |
| RiskSourceObjectivePair | ESOV | ESOV-1 |
| EcosystemStakeholder | EECS | EECS-1 |
| StrategicScenario | ESTS | ESTS-1 |
| AttackPathStep | EAPS | EAPS-1 |
| OperationalScenario | EOPS | EOPS-1 |
| AttackTechnique | EATT | EATT-1 |
| EbiosSummary | ESUM | ESUM-1 |
| PACSMeasure | EPAC | EPAC-1 |

Le modèle [`MitreAttackTechnique`](mitre-attack-technique.md) (catalogue) n'utilise pas de préfixe interne : sa clé naturelle est `mitre_id` (ex. T1566.001).

---

## 4. Modèle de données par atelier

Toutes les entités EBIOS héritent de `BaseModel` (UUID, timestamps, `created_by`, approbation, versioning, tags) ou de `ScopedModel` (idem + M2M `scopes`) selon leur portée. Sauf indication contraire, les entités EBIOS sont rattachées à un [`RiskAssessment`](../risk-assessment.md) et héritent du scope de celui-ci (pas de `scopes` propre).

Les définitions détaillées de chaque entité sont publiées dans des fichiers dédiés :

- **W0** : [StudyFramework](study-framework.md), [EbiosWorkshopProgress](workshop-progress.md)
- **W1** : [SecurityBaseline](security-baseline.md), [FearedEvent](feared-event.md), [BaselineGap](baseline-gap.md)
- **W2** : [RiskSource](risk-source.md), [TargetedObjective](targeted-objective.md), [RiskSourceObjectivePair](sr-ov-pair.md)
- **W3** : [EcosystemStakeholder](ecosystem-stakeholder.md), [StrategicScenario](strategic-scenario.md), [AttackPathStep](attack-path-step.md)
- **W4** : [MitreAttackTechnique](mitre-attack-technique.md), [OperationalScenario](operational-scenario.md), [AttackTechnique](attack-technique.md)
- **W5** : [EbiosSummary](ebios-summary.md), [PACSMeasure](pacs-measure.md)

L'atelier 5 réutilise également les entités du socle commun : [`Risk`](../risk.md), [`RiskTreatmentPlan`](../risk-treatment-plan.md), [`TreatmentAction`](../risk-treatment-plan.md), [`RiskAcceptance`](../risk-acceptance.md).

---

## 5. Règles de gestion EBIOS RM

| ID | Règle |
|---|---|
| RE-01 | Toutes les entités EBIOS sont rattachées à une [`RiskAssessment`](../risk-assessment.md) dont `methodology = ebios_rm`. La création est refusée si l'appréciation est `iso27005`. |
| RE-02 | À la création d'une [`RiskAssessment`](../risk-assessment.md) ebios_rm, le système crée automatiquement : 1 [`StudyFramework`](study-framework.md) (status draft), 6 [`EbiosWorkshopProgress`](workshop-progress.md) (W0 à W5, status not_started). |
| RE-03 | Une porte de validation d'atelier ne peut être franchie que si tous les ateliers précédents sont en état `validated`. |
| RE-04 | Pour `EbiosWorkshopProgress.workshop_number = N`, les livrables obligatoires sont contrôlés avant validation : W0 = StudyFramework status validated ; W1 = SecurityBaseline + au moins 1 FearedEvent par EssentialAsset retenu ; W2 = au moins 1 RiskSourceObjectivePair is_retained ; W3 = au moins 1 StrategicScenario is_retained ; W4 = au moins 1 OperationalScenario par StrategicScenario retenu ; W5 = EbiosSummary status validated + au moins 1 PACSMeasure. |
| RE-05 | Un [`FearedEvent`](feared-event.md) est unique par couple `(essential_asset, dic_criterion)` au sein d'un même [`SecurityBaseline`](security-baseline.md). |
| RE-06 | [`RiskSource.threat_level`](risk-source.md) est calculé dans `save()` via la grille A ANSSI (§2.8). Le snapshot du barème est conservé dans `criteria_snapshot`. |
| RE-07 | [`EcosystemStakeholder.threat_level`](ecosystem-stakeholder.md) et `threat_zone` sont calculés dans `save()` via la formule (dependency x penetration) / (maturity x trust) et les seuils paramétrables (§2.6). |
| RE-08 | Seuls les couples SR/OV `is_retained = true` peuvent être référencés par un [`StrategicScenario`](strategic-scenario.md). |
| RE-09 | Seuls les [`StrategicScenario`](strategic-scenario.md) `is_retained = true` peuvent être déclinés en [`OperationalScenario`](operational-scenario.md). |
| RE-10 | [`OperationalScenario.gravity_level`](operational-scenario.md) hérite par défaut de `strategic_scenario.gravity_level`. Toute modification doit renseigner `gravity_override_justification` et bascule `gravity_inherited` à false. |
| RE-11 | La consolidation d'un [`OperationalScenario`](operational-scenario.md) en [`Risk`](../risk.md) est l'opération privilégiée. La consolidation d'un [`StrategicScenario`](strategic-scenario.md) est possible pour les scénarios non déclinés en opérationnel. |
| RE-12 | La consolidation crée un [`Risk`](../risk.md) avec `risk_source = ebios_operational_scenario` (ou `ebios_strategic_scenario`), pré-remplit les champs (gravité, vraisemblance via mapping V1-V4, biens, DIC) et établit le lien bidirectionnel `consolidated_risk_id`. |
| RE-13 | Une [`AttackTechnique`](attack-technique.md) doit référencer soit une [`MitreAttackTechnique`](mitre-attack-technique.md) (recommandé) soit un `custom_name`. Si MITRE est référencé, le champ `mitre_version` du [`OperationalScenario`](operational-scenario.md) parent doit être figé pour traçabilité. |
| RE-14 | Le passage d'un cycle stratégique à un cycle opérationnel crée de nouvelles [`EbiosWorkshopProgress`](workshop-progress.md) (W4 et W5) avec `iteration_number` incrémenté, sans toucher aux entités W1-W3 du cycle stratégique en cours. |
| RE-15 | La suppression d'une entité EBIOS est refusée si elle est référencée par une entité d'atelier supérieur (ex. SR utilisée dans un couple SR/OV retenu). Désactivation via `is_retained = false` à la place. |
| RE-16 | La validation finale (W5) verrouille en lecture seule toutes les entités EBIOS de l'appréciation. Une nouvelle itération est nécessaire pour modifier. |
| RE-17 | Toute modification d'une entité avec champ calculé déclenche le recalcul automatique au save() et incrémente la version simple_history. |
| RE-18 | Une [`PACSMeasure`](pacs-measure.md) `target_date` dépassée et `status not in [completed, cancelled]` passe automatiquement en `overdue` (tâche planifiée quotidienne). |
| RE-19 | Toute modification du barème [`RiskCriteria.ebios_threat_grid`](../risk-criteria.md) ou `ebios_ecosystem_thresholds` propose le recalcul de toutes les entités EBIOS de l'appréciation associée (action manuelle, jamais automatique pour préserver l'historique). |

---

## 6. Spécifications API REST

Base URL : `/api/v1/risks/ebios/`. Toutes les routes héritent de la pagination, du filtrage, du tri et de l'authentification définis pour le module Risques (voir [../README.md](../README.md#6-spécifications-api-rest)).

### 6.1 Atelier 0 - Cadre d'étude et progression

| Méthode | Endpoint | Description |
|---|---|---|
| `GET` | `/study-frameworks` | Lister les cadres d'étude (filtre `?assessment_id=`) |
| `POST` | `/study-frameworks` | Créer (1 par appréciation) |
| `GET` | `/study-frameworks/{id}` | Détail |
| `PUT` / `PATCH` | `/study-frameworks/{id}` | Mise à jour |
| `POST` | `/study-frameworks/{id}/validate` | Valider le cadre |
| `GET` | `/workshops` | Lister les EbiosWorkshopProgress (filtre `?assessment_id=`) |
| `GET` | `/workshops/{id}` | Détail |
| `PATCH` | `/workshops/{id}` | Mise à jour statut/notes |
| `POST` | `/workshops/{id}/start` | Démarrer l'atelier |
| `POST` | `/workshops/{id}/validate` | Valider l'atelier (avec contrôle des livrables) |
| `POST` | `/workshops/{id}/reject` | Rejeter l'atelier (avec motif) |
| `POST` | `/workshops/{id}/iterate` | Démarrer une nouvelle itération |

### 6.2 Atelier 1 - Socle de sécurité

| Méthode | Endpoint | Description |
|---|---|---|
| `GET` | `/baselines` | Lister les SecurityBaseline |
| `POST` | `/baselines` | Créer (1 par appréciation) |
| `GET` / `PUT` / `PATCH` / `DELETE` | `/baselines/{id}` | CRUD |
| `GET` | `/baselines/{id}/feared-events` | Lister les ER du socle |
| `POST` | `/baselines/{id}/feared-events` | Créer un ER |
| `GET` / `PUT` / `PATCH` / `DELETE` | `/feared-events/{id}` | CRUD ER |
| `GET` | `/baselines/{id}/gaps` | Lister les écarts |
| `POST` | `/baselines/{id}/gaps` | Créer un écart |
| `GET` / `PUT` / `PATCH` / `DELETE` | `/baseline-gaps/{id}` | CRUD écart |
| `POST` | `/baselines/{id}/import-from-context` | Importer EssentialAsset, SupportAsset, Activity, Stakeholder retenus depuis le scope |

### 6.3 Atelier 2 - Sources de risque

| Méthode | Endpoint | Description |
|---|---|---|
| `GET` | `/risk-sources` | Lister les SR (filtres `?assessment_id`, `?category`, `?is_retained`, `?threat_level_min`) |
| `POST` | `/risk-sources` | Créer une SR |
| `GET` / `PUT` / `PATCH` / `DELETE` | `/risk-sources/{id}` | CRUD |
| `POST` | `/risk-sources/{id}/approve` | Approuver |
| `GET` | `/risk-sources/catalog` | Catalogue ANSSI de SR types |
| `POST` | `/risk-sources/import-catalog` | Importer depuis catalogue |
| `GET` | `/targeted-objectives` | Lister les OV |
| `POST` | `/risk-sources/{id}/objectives` | Créer un OV pour une SR |
| `GET` / `PUT` / `PATCH` / `DELETE` | `/targeted-objectives/{id}` | CRUD OV |
| `GET` | `/sr-ov-pairs` | Lister les couples SR/OV (filtres) |
| `POST` | `/sr-ov-pairs` | Créer un couple |
| `GET` / `PUT` / `PATCH` / `DELETE` | `/sr-ov-pairs/{id}` | CRUD |
| `POST` | `/sr-ov-pairs/{id}/approve` | Approuver |
| `GET` | `/assessments/{id}/sr-ov-matrix` | Matrice croisée SR x OV avec pertinence |

### 6.4 Atelier 3 - Écosystème et scénarios stratégiques

| Méthode | Endpoint | Description |
|---|---|---|
| `GET` | `/ecosystem-stakeholders` | Lister les PP écosystème (filtres `?assessment_id`, `?threat_zone`) |
| `POST` | `/ecosystem-stakeholders` | Créer une PP |
| `GET` / `PUT` / `PATCH` / `DELETE` | `/ecosystem-stakeholders/{id}` | CRUD |
| `POST` | `/ecosystem-stakeholders/{id}/approve` | Approuver |
| `POST` | `/ecosystem-stakeholders/import-suppliers` | Importer depuis Module 2 Suppliers |
| `GET` | `/assessments/{id}/ecosystem-graph` | Graphe écosystème (nodes + edges + zones) |
| `GET` | `/strategic-scenarios` | Lister (filtres `?assessment_id`, `?is_retained`, `?risk_level_min`) |
| `POST` | `/strategic-scenarios` | Créer |
| `GET` / `PUT` / `PATCH` / `DELETE` | `/strategic-scenarios/{id}` | CRUD |
| `POST` | `/strategic-scenarios/{id}/approve` | Approuver |
| `POST` | `/strategic-scenarios/{id}/consolidate` | Consolider en Risk |
| `GET` | `/strategic-scenarios/{id}/attack-path` | Lister les étapes |
| `POST` | `/strategic-scenarios/{id}/attack-path` | Ajouter une étape |
| `GET` / `PUT` / `PATCH` / `DELETE` | `/attack-path-steps/{id}` | CRUD étape |
| `PATCH` | `/strategic-scenarios/{id}/attack-path/reorder` | Réordonner |

### 6.5 Atelier 4 - Scénarios opérationnels

| Méthode | Endpoint | Description |
|---|---|---|
| `GET` | `/operational-scenarios` | Lister (filtres `?strategic_scenario_id`, `?likelihood_v`, `?risk_level_min`) |
| `POST` | `/operational-scenarios` | Créer |
| `GET` / `PUT` / `PATCH` / `DELETE` | `/operational-scenarios/{id}` | CRUD |
| `POST` | `/operational-scenarios/{id}/approve` | Approuver |
| `POST` | `/operational-scenarios/{id}/consolidate` | Consolider en Risk |
| `GET` | `/operational-scenarios/{id}/techniques` | Lister les techniques |
| `POST` | `/operational-scenarios/{id}/techniques` | Ajouter une technique |
| `GET` / `PUT` / `PATCH` / `DELETE` | `/attack-techniques/{id}` | CRUD |
| `PATCH` | `/operational-scenarios/{id}/techniques/reorder` | Réordonner |
| `GET` | `/mitre-attack/techniques` | Catalogue MITRE (recherche `?search`, `?tactic`) |
| `GET` | `/mitre-attack/techniques/{mitre_id}` | Détail technique MITRE |
| `GET` | `/assessments/{id}/mitre-heatmap` | Heatmap MITRE des techniques utilisées |

### 6.6 Atelier 5 - Synthèse et PACS

| Méthode | Endpoint | Description |
|---|---|---|
| `GET` | `/summaries` | Lister les EbiosSummary |
| `POST` | `/summaries` | Créer (1 par appréciation) |
| `GET` / `PUT` / `PATCH` | `/summaries/{id}` | CRUD |
| `POST` | `/summaries/{id}/snapshot-mappings` | Capturer les snapshots avant/après |
| `POST` | `/summaries/{id}/validate` | Valider la synthèse (direction générale) |
| `GET` | `/pacs-measures` | Lister les mesures PACS (filtres) |
| `POST` | `/pacs-measures` | Créer |
| `GET` / `PUT` / `PATCH` / `DELETE` | `/pacs-measures/{id}` | CRUD |
| `GET` | `/pacs-measures/overdue` | Mesures en retard |
| `GET` | `/assessments/{id}/risk-mapping` | Cartographie avant/après (matrices côte à côte) |

### 6.7 Endpoints transversaux

| Méthode | Endpoint | Description |
|---|---|---|
| `GET` | `/assessments/{id}/ebios/progress` | Synthèse de progression (6 ateliers) |
| `GET` | `/assessments/{id}/ebios/export` | Export DOCX/PDF rapport complet |
| `GET` | `/assessments/{id}/ebios/export-pacs` | Export PACS DOCX/XLSX |
| `GET` | `/assessments/{id}/ebios/audit-trail` | Journal d'audit EBIOS de l'appréciation |
| `POST` | `/assessments/{id}/ebios/recompute-scores` | Recalculer les scores EBIOS suite à modification barème |

---

## 7. Spécifications MCP

Toutes les entités EBIOS sont exposées via MCP dans `mcp/tools.py` selon le pattern existant (`@require_perm("risks.ebios_xxx.action")` + helpers `_list_handler`, `_get_handler`, `_create_handler`, `_update_handler`).

### 7.1 Tools CRUD standards (par entité)

Pour chacune des 15 entités EBIOS (StudyFramework, EbiosWorkshopProgress, SecurityBaseline, FearedEvent, BaselineGap, RiskSource, TargetedObjective, RiskSourceObjectivePair, EcosystemStakeholder, StrategicScenario, AttackPathStep, OperationalScenario, AttackTechnique, EbiosSummary, PACSMeasure) :

- `list_{entity}` (filtres exposés)
- `get_{entity}` (par id ou reference)
- `create_{entity}`
- `update_{entity}`
- `delete_{entity}`
- `approve_{entity}` (pour les entités approvables : SecurityBaseline, RiskSource, RiskSourceObjectivePair, EcosystemStakeholder, StrategicScenario, OperationalScenario, EbiosSummary)
- `batch_create_{entity}` (M4 conserve ce pattern)

Total : environ 90 à 100 tools CRUD.

### 7.2 Tools spécifiques EBIOS

| Tool | Permission | Description |
|---|---|---|
| `transition_workshop` | `risks.ebios_assessment.update` | Change le statut d'un EbiosWorkshopProgress (start, validate, reject, iterate) |
| `validate_workshop` | `risks.ebios_assessment.validate` | Valide un atelier avec contrôle des livrables obligatoires |
| `consolidate_strategic_to_risk` | `risks.risk.create` | Consolide un StrategicScenario en Risk du registre |
| `consolidate_operational_to_risk` | `risks.risk.create` | Consolide un OperationalScenario en Risk du registre |
| `compute_risk_source_threat_level` | `risks.ebios_risk_source.read` | Recalcule le niveau de menace d'une SR |
| `compute_stakeholder_threat_level` | `risks.ebios_ecosystem.read` | Recalcule le niveau de menace d'une PP écosystème |
| `recompute_assessment_scores` | `risks.ebios_assessment.update` | Recalcule tous les scores d'une appréciation suite à modification barème |
| `list_mitre_techniques` | `risks.ebios_operational.read` | Recherche dans le catalogue MITRE |
| `get_mitre_technique` | `risks.ebios_operational.read` | Détail d'une technique MITRE |
| `get_ecosystem_graph` | `risks.ebios_ecosystem.read` | Graphe de l'écosystème (nodes, edges, zones) |
| `get_sr_ov_matrix` | `risks.ebios_risk_source.read` | Matrice SR x OV |
| `get_mitre_heatmap` | `risks.ebios_operational.read` | Heatmap MITRE des techniques utilisées |
| `get_assessment_progress` | `risks.ebios_assessment.read` | Synthèse de progression des 6 ateliers |
| `generate_ebios_report` | `risks.export` | Génère le rapport DOCX EBIOS complet |
| `generate_pacs_report` | `risks.export` | Génère le PACS DOCX/XLSX |
| `import_risk_source_catalog` | `risks.ebios_risk_source.create` | Importe le catalogue ANSSI de SR types |
| `import_ecosystem_from_suppliers` | `risks.ebios_ecosystem.create` | Importe les Suppliers comme PP candidates |

---

## 8. Spécifications d'interface utilisateur

### 8.1 Navigation

Le sous-module EBIOS RM est accessible depuis le détail d'une [`RiskAssessment`](../risk-assessment.md) dont `methodology = ebios_rm`. La page de détail affiche en bandeau supérieur :
- Le **stepper 5 ateliers** (W1 à W5, avec branche cancelled si rejet).
- L'indicateur **cycle stratégique vs opérationnel** (badge).
- Le bouton « Nouvelle itération » (RSSI/Admin).

Une entrée dans le menu latéral du module Risques propose « EBIOS RM » qui affiche le tableau des appréciations EBIOS (filtre `methodology=ebios_rm` sur la liste M4).

### 8.2 Stepper des 5 ateliers

Reproduit le pattern de [compliance/templates/compliance/assessment_detail.html](compliance/templates/compliance/assessment_detail.html) :

- 5 pills horizontales (W1 à W5) avec connecteurs.
- 6e pill (W0) en amont, plus petite et en gris (pré-requis).
- État `validated` -> coche verte. État `in_progress` -> pill accent. État `under_review` -> pill orange. État `not_started` -> pill grise pointillée. État `rejected` -> branche secondaire vers le bas.
- Clic sur une pill -> navigation vers la vue de l'atelier correspondant.
- Le contexte côté serveur est construit par méthode `EbiosWorkshopMixin.get_workshop_steps(assessment)` qui retourne la liste ordonnée des 6 progressions avec leur état.

### 8.3 Vue W0 - Cadre de l'étude

Layout 2 colonnes :
- **Colonne principale (col-lg-8)** : formulaire StudyFramework (description, périmètres, hypothèses, contraintes, livrables attendus).
- **Sidebar (col-lg-4)** : statut, participants internes (multi-select User), participants externes (mini formset), référentiels applicables (multi-select Framework), enveloppe budgétaire, dates, bouton « Valider le cadre ».

### 8.4 Vue W1 - Socle de sécurité

Layout 2 colonnes :
- **Colonne principale** :
  - Card « Périmètre métier » : récap des Activity et EssentialAsset retenus (en lecture, avec lien vers Module 1/2 pour édition).
  - Card « Événements redoutés » : tableau Bien essentiel x DIC x Description x Gravité avec actions inline. Bouton d'ajout. Vue compacte mobile (cards empilées).
  - Card « Écarts au socle » : tableau Référentiel x Description x Sévérité x Statut avec lien Requirement et actions inline.
- **Sidebar** :
  - Référentiels du socle (multi-select Framework).
  - Statut atelier (stepper W1).
  - Bouton « Valider l'atelier 1 » (RSSI).
  - Bouton « Importer depuis Contexte/Actifs » qui pré-remplit les valeurs métier et biens supports.

### 8.5 Vue W2 - Sources de risque et objectifs visés

Trois sous-onglets :

1. **Sources de risque** : tableau avec colonnes Référence, Nom, Catégorie, Motivation, Ressources, Activité, Niveau de menace (badge V1-V4), Retenue. Filtres. Formulaire d'ajout dans modal. Bouton « Importer catalogue ANSSI ».
2. **Objectifs visés** : groupés par SR (accordéon). Pour chaque SR, tableau des OV avec biens essentiels ciblés et événements redoutés.
3. **Matrice SR x OV** : grille croisée. Lignes = SR retenues, colonnes = OV. Cellule = pertinence (low/medium/high/critical) avec code couleur. Cellule vide cliquable pour créer le couple. Cellule remplie cliquable pour éditer ou exclure (`is_retained`).

### 8.6 Vue W3 - Écosystème et scénarios stratégiques

Deux sous-onglets :

1. **Cartographie écosystème** :
   - Graphe interactif (vis.js ou D3.js) avec 3 zones visuelles (vert/orange/rouge).
   - Nœuds = EcosystemStakeholder, taille proportionnelle à `dependency`, couleur selon `threat_zone`.
   - Arêtes = relations (M2M `accessible_support_assets` agrégées).
   - Panneau de détail à droite (sélection d'un nœud -> édition des dimensions ANSSI : dependency, penetration, maturity, trust ; recalcul live de `threat_level`).
   - Légende des seuils de zones.
   - Vue tabulaire de bascule.

2. **Scénarios stratégiques** :
   - Liste avec colonnes Référence, Nom, Couple SR/OV, Gravité, Vraisemblance, Niveau, Retenu, Risque consolidé.
   - Détail : éditeur de chemin d'attaque en mode visuel (timeline horizontale d'étapes avec PP impliquée à chaque étape, drag-and-drop pour réordonner).
   - Bouton « Consolider en risque ».

### 8.7 Vue W4 - Scénarios opérationnels

Deux sous-onglets :

1. **Scénarios opérationnels** :
   - Liste groupée par scénario stratégique parent (accordéon).
   - Colonnes : Référence, Nom, Biens supports, Vraisemblance V1-V4, Gravité (badge « hérité »/« ajusté »), Niveau, Risque consolidé.
   - Détail : éditeur de séquence d'attaque (techniques chaînées), autocomplétion MITRE ATT&CK sur la saisie (recherche par tactic ou ID).
   - Bouton « Consolider en risque ».

2. **Heatmap MITRE ATT&CK** :
   - Matrice des 14 tactiques x techniques, code couleur selon le nombre de scénarios opérationnels utilisant chaque technique.
   - Filtre par scénario stratégique parent.
   - Export PNG/PDF.

### 8.8 Vue W5 - Synthèse et PACS

Layout 2 colonnes :
- **Colonne principale** :
  - Card « Cartographie avant/après » : deux matrices de risques (initiale vs résiduelle) côte à côte avec heatmap.
  - Card « Stratégie résiduelle » : éditeur de `residual_risk_strategy`.
  - Card « PACS » : liste structurée de PACSMeasure (kanban par statut ou tableau triable).
  - Pour chaque mesure : référence, description, type, échéance, responsable, statut, coût, gain attendu, lien RiskTreatmentPlan.
- **Sidebar** :
  - Statut atelier W5 (stepper).
  - Prochains cycles (dates stratégique et opérationnel).
  - Validation par direction générale.
  - Export DOCX/PDF rapport complet.
  - Export PACS DOCX/XLSX.

### 8.9 Adaptations mobile

- Stepper : passage en mode vertical sur écrans < 768px, avec scroll horizontal pour les pills.
- Matrices et graphes : passage en vue tabulaire avec bascule explicite.
- Multi-select : utilisation du composant existant `select2-mobile` du projet.
- Sticky bars : action principale (Valider/Approuver) sticky en bas de l'écran sur mobile.
- Formsets : empilement vertical avec affordances tactiles.

### 8.10 Thèmes clair/sombre

Tous les composants spécifiques EBIOS RM (graphe écosystème, heatmap MITRE, matrices avant/après) utilisent les variables CSS du thème (`--color-bg`, `--color-text`, `--color-accent`, `--color-success`, `--color-warning`, `--color-danger`). Vérifications obligatoires en thème sombre :
- Lisibilité des labels sur le graphe (texte clair sur nœuds sombres).
- Contraste suffisant des zones de couleur (vert/orange/rouge en version sombre).
- Heatmap MITRE : palette adaptée pour ne pas saturer en mode sombre.

---

## 9. Permissions et internationalisation

### 9.1 PERMISSION_REGISTRY

Ajout dans `accounts/constants.py` sous la clé `risks` :

```python
PERMISSION_REGISTRY["risks"].update({
    "ebios_assessment": {
        "actions": ["read", "update", "validate"],
        "label": _("EBIOS RM assessment pilotage"),
    },
    "ebios_baseline": {
        "actions": ["create", "read", "update", "delete", "approve"],
        "label": _("EBIOS RM security baseline (workshop 1)"),
    },
    "ebios_risk_source": {
        "actions": ["create", "read", "update", "delete", "approve"],
        "label": _("EBIOS RM risk sources and objectives (workshop 2)"),
    },
    "ebios_ecosystem": {
        "actions": ["create", "read", "update", "delete", "approve"],
        "label": _("EBIOS RM ecosystem stakeholders (workshop 3)"),
    },
    "ebios_strategic": {
        "actions": ["create", "read", "update", "delete", "approve"],
        "label": _("EBIOS RM strategic scenarios (workshop 3)"),
    },
    "ebios_operational": {
        "actions": ["create", "read", "update", "delete", "approve"],
        "label": _("EBIOS RM operational scenarios (workshop 4)"),
    },
    "ebios_summary": {
        "actions": ["create", "read", "update", "delete", "approve"],
        "label": _("EBIOS RM summary and PACS (workshop 5)"),
    },
})
```

Codes générés : `risks.ebios_assessment.read`, `risks.ebios_baseline.create`, etc. (environ 35 nouvelles permissions).

### 9.2 Mappings groupes système

| Groupe | Permissions EBIOS accordées |
|---|---|
| Super Admin | toutes |
| Admin | toutes sauf `*.delete` |
| RSSI / DPO | `*.read`, `*.create`, `*.update`, `*.approve`, `ebios_assessment.validate` |
| Auditeur | `*.read` uniquement |
| Contributeur | `*.read`, `*.create`, `*.update` (hors `approve` et `validate`) |
| Lecteur | `*.read` uniquement |

À ajouter dans la data migration `accounts/migrations/00xx_add_ebios_permissions.py`.

### 9.3 Internationalisation (FR)

Toutes les chaînes UI sont enveloppées de `_()`, `gettext_lazy()` ou `{% trans %}`. Les traductions FR doivent être ajoutées dans `locale/fr/LC_MESSAGES/django.po` en évitant les doublons `msgid` (utiliser `pgettext_lazy` avec contexte si conflit).

Clés FR à vérifier/ajouter (liste non exhaustive) :

| msgid (EN) | msgstr (FR) | Contexte si nécessaire |
|---|---|---|
| Workshop 1 | Atelier 1 - Socle de sécurité | déjà présent |
| Workshop 2 | Atelier 2 - Sources de risque | déjà présent |
| Workshop 3 | Atelier 3 - Scénarios stratégiques | déjà présent |
| Workshop 4 | Atelier 4 - Scénarios opérationnels | déjà présent |
| Workshop 5 | Atelier 5 - Traitement du risque | déjà présent |
| Study framework | Cadre de l'étude | - |
| Security baseline | Socle de sécurité | ebios |
| Feared event | Événement redouté | - |
| Baseline gap | Écart au socle | - |
| Risk source | Source de risque | - |
| Targeted objective | Objectif visé | - |
| Risk source / objective pair | Couple source de risque / objectif visé | - |
| Ecosystem stakeholder | Partie prenante de l'écosystème | - |
| Threat level | Niveau de menace | - |
| Threat zone | Zone de menace | - |
| Control zone | Zone de contrôle | - |
| Monitoring zone | Zone de surveillance | - |
| Danger zone | Zone de danger | - |
| Strategic scenario | Scénario stratégique | - |
| Attack path step | Étape du chemin d'attaque | - |
| Operational scenario | Scénario opérationnel | - |
| Attack technique | Technique d'attaque | - |
| EBIOS summary | Synthèse EBIOS RM | - |
| PACS measure | Mesure du PACS | - |
| Continuous security improvement plan | Plan d'amélioration continue de la sécurité | - |
| Strategic cycle | Cycle stratégique | - |
| Operational cycle | Cycle opérationnel | - |
| MITRE ATT&CK heatmap | Cartographie MITRE ATT&CK | - |
| Minimal (V1) | Minimal (V1) | likelihood |
| Significant (V2) | Significatif (V2) | likelihood |
| Strong (V3) | Fort (V3) | likelihood |
| Maximal (V4) | Maximal (V4) | likelihood |

---

## 10. Tests

### 10.1 Matrice de tests obligatoires

| Domaine | Tests obligatoires |
|---|---|
| Calculs ANSSI | Grille A SR (4x4x3 combinaisons) renvoie V1-V4 attendus. Formule écosystème (dependency x penetration) / (maturity x trust) renvoie threat_zone attendu sur 12 cas frontières. Mapping likelihood_v -> entier (V1=1, V4=4) pour matrice risk_level. |
| Portes de validation | W1 ne peut être validé sans SecurityBaseline et au moins 1 FearedEvent. W2 ne peut être validé sans 1 ESOV is_retained. W3 sans 1 ESTS is_retained. W4 sans 1 EOPS par ESTS retenu. W5 sans EbiosSummary validé et 1 PACSMeasure. |
| Cycle itératif | Création nouvelle itération opérationnelle ne touche pas aux entités stratégiques. iteration_number s'incrémente correctement. |
| Héritage gravité | OperationalScenario hérite par défaut. Modification déclenche bascule gravity_inherited à false et exige justification. |
| Filtres is_retained | SR non retenue -> OV non utilisables. ESOV non retenu -> ne peut être référencé par ESTS. ESTS non retenu -> ne peut être décliné en EOPS. |
| Consolidation Risk | Consolidation EOPS crée Risk avec champs pré-remplis. Lien bidirectionnel consolidé. risk_source = ebios_operational_scenario. |
| MITRE catalog | Seed via fixture charge >500 techniques. Recherche par tactic fonctionne. Sous-techniques rattachées au parent. |
| Permissions | Accès refusé pour les codenames non accordés. RSSI peut valider, Auditeur ne peut pas. |
| Snapshot critères | Modification du barème ne recalcule pas automatiquement les entités existantes. Action manuelle `recompute_assessment_scores` recalcule en conservant l'historique simple_history. |

### 10.2 Factories factory-boy

Ajouts dans `risks/tests/factories.py` (15 factories) : `StudyFrameworkFactory`, `EbiosWorkshopProgressFactory`, `SecurityBaselineFactory`, `FearedEventFactory`, `BaselineGapFactory`, `RiskSourceFactory`, `TargetedObjectiveFactory`, `RiskSourceObjectivePairFactory`, `EcosystemStakeholderFactory`, `StrategicScenarioFactory`, `AttackPathStepFactory`, `OperationalScenarioFactory`, `AttackTechniqueFactory`, `MitreAttackTechniqueFactory`, `EbiosSummaryFactory`, `PACSMeasureFactory`.

Chaque factory garantit un assessment EBIOS valide en dépendance (sub_factory ou trait).

### 10.3 Organisation des tests

| Fichier | Contenu |
|---|---|
| `risks/tests/test_ebios_models.py` | Tests des calculs `save()`, formules ANSSI, snapshots criteria, contraintes d'unicité. |
| `risks/tests/test_ebios_views.py` | Transitions de workflow, vues stepper, rendu UI, accès permissions. |
| `risks/tests/test_ebios_api.py` | CRUD endpoints, actions custom (validate, consolidate, recompute), filtres. |
| `risks/tests/test_ebios_mcp.py` | Tools MCP CRUD + spécifiques. |
| `risks/tests/test_ebios_workflow.py` | Scénarios end-to-end (création appréciation -> validation des 6 ateliers -> export rapport). |
| `risks/tests/test_ebios_mitre.py` | Catalogue MITRE (seed, recherche, heatmap). |

Couverture cible : >= 85% sur les modules `risks/models/ebios/`, `risks/api/ebios/`, `risks/views/ebios/`.

---

## 11. Migration et données initiales

### 11.1 Ordre des migrations

1. `risks/migrations/00NN_ebios_study_framework_workshop.py` : StudyFramework + EbiosWorkshopProgress.
2. `risks/migrations/00NN_ebios_baseline.py` : SecurityBaseline + FearedEvent + BaselineGap.
3. `risks/migrations/00NN_ebios_risk_sources.py` : RiskSource + TargetedObjective + RiskSourceObjectivePair.
4. `risks/migrations/00NN_ebios_ecosystem.py` : EcosystemStakeholder.
5. `risks/migrations/00NN_ebios_strategic.py` : StrategicScenario + AttackPathStep.
6. `risks/migrations/00NN_mitre_catalog.py` : MitreAttackTechnique.
7. `risks/migrations/00NN_ebios_operational.py` : OperationalScenario + AttackTechnique.
8. `risks/migrations/00NN_ebios_summary_pacs.py` : EbiosSummary + PACSMeasure.
9. `risks/migrations/00NN_risk_link_ebios_scenarios.py` : ajoute `consolidated_risk_id` (reverse) et complète `Risk.source_entity_type` choices.

### 11.2 Data migration MITRE ATT&CK

`risks/migrations/00NN_seed_mitre_attack.py` : charge `risks/fixtures/mitre_attack_v15.json` (Enterprise Matrix complète, environ 600+ techniques, ~14 tactics). Compatible offline (pas d'appel API). Mise à jour via la management command :

```
python manage.py refresh_mitre_attack --version 15.1
```

La commande prend en argument le fichier JSON local (téléchargé manuellement depuis le repo officiel MITRE/CTI sur GitHub) et met à jour le catalogue en conservant les FK existantes.

### 11.3 Data migration permissions

`accounts/migrations/00NN_add_ebios_permissions.py` :
- Crée les 35 permissions `risks.ebios_*.*` à partir du registry étendu.
- Attribue les permissions aux groupes système (cf. §9.2).

### 11.4 Data migration catalogue de sources de risque

`risks/migrations/00NN_seed_ebios_risk_source_catalog.py` : ajoute un catalogue ANSSI de SR types avec `is_from_catalog = true` (cybercriminel, État, hacktiviste, employé malveillant, employé négligent, concurrent, prestataire, etc.). Ces entrées servent de pool de copie lors de la création d'une appréciation EBIOS (action « Importer catalogue »).

### 11.5 Compatibilité historique

Pour les [`RiskAssessment`](../risk-assessment.md) existantes avec `methodology = ebios_rm` (uniquement la coquille pour l'instant) :
- Data migration `00NN_backfill_ebios_workshops.py` : crée pour chaque appréciation ebios_rm existante 1 StudyFramework status draft + 6 EbiosWorkshopProgress not_started.
- Aucune migration des entités EBIOS antérieures (il n'y en a pas).

---

## 12. Annexes

### Annexe A - Grille ANSSI niveau de menace SR (Grille A)

Détail de la grille de calcul [`RiskSource.threat_level`](risk-source.md) (4 motivations x 4 ressources x 3 activités = 48 combinaisons aplaties). Tableau de référence (extrait) :

| Motivation | Ressources | Activité | Niveau menace |
|---|---|---|---|
| Faible (1) | Limitées (1) | Faible | V1 |
| Faible (1) | Limitées (1) | Moyenne | V1 |
| Faible (1) | Limitées (1) | Élevée | V2 |
| Modérée (2) | Modérées (2) | Moyenne | V2 |
| Forte (3) | Importantes (3) | Élevée | V4 |
| Très forte (4) | Illimitées (4) | Élevée | V4 |

La grille complète est fournie dans le fichier `risks/constants/ebios_grids.py` et alimente le calcul de `threat_level`. Paramétrable au niveau [`RiskCriteria.ebios_threat_grid`](../risk-criteria.md).

### Annexe B - Grille ANSSI vraisemblance opérationnelle V1-V4 (Grille B)

| Code | Libellé EN | Libellé FR | Critère d'évaluation |
|---|---|---|---|
| V1 | Minimal | Minimal | Mode opératoire inconnu ou difficilement réalisable. Compétences expertes requises, outils sur mesure. |
| V2 | Significant | Significatif | Mode opératoire documenté mais demande des compétences spécifiques. Outils peu courants. |
| V3 | Strong | Fort | Mode opératoire éprouvé, accessible à un attaquant intermédiaire avec outils standards. |
| V4 | Maximal | Maximal | Mode opératoire automatisé, kits clés en main, ou trivial. Aucune compétence particulière requise. |

### Annexe C - Seuils threat_zone écosystème

| Zone | Plage `threat_level` | Couleur UI | Sémantique ANSSI |
|---|---|---|---|
| Contrôle (control) | `threat_level < 0.5` | Vert | Partie prenante sous maîtrise, exposition résiduelle faible. |
| Surveillance (monitoring) | `0.5 <= threat_level < 1.5` | Orange | Partie prenante à surveiller. Mesures de réduction recommandées. |
| Danger (danger) | `threat_level >= 1.5` | Rouge | Partie prenante critique. Mesures de réduction obligatoires. |

Les seuils sont paramétrables sur [`RiskCriteria.ebios_ecosystem_thresholds`](../risk-criteria.md) (JSON : `{"control": 0.5, "monitoring": 1.5}`).

### Annexe D - Exemples de scénarios types ANSSI

1. **Ransomware ciblé** :
   - SR : cybercriminel (motivation lucrative, ressources importantes, activité élevée -> V4).
   - OV : enrichissement (lucrative).
   - Couple SR/OV : critique.
   - PP écosystème : MSP (zone surveillance).
   - Chemin stratégique : MSP -> accès distant -> mouvement latéral -> chiffrement.
   - Scénario opérationnel : phishing (T1566.001) -> accès initial (T1078) -> mouvement latéral (T1021) -> chiffrement (T1486).
   - Vraisemblance opérationnelle : V3.

2. **Supply chain compromise** :
   - SR : État (motivation stratégique, ressources illimitées, activité élevée -> V4).
   - OV : espionnage (strategic).
   - PP écosystème : éditeur logiciel critique (zone danger).
   - Chemin stratégique : éditeur -> mise à jour empoisonnée -> persistance -> exfiltration.
   - Scénario opérationnel : T1195.002 -> T1543 -> T1041.
   - Vraisemblance opérationnelle : V2.

3. **Insider menant fraude** :
   - SR : employé interne (motivation rancune, ressources modérées, activité moyenne -> V2).
   - OV : revenge.
   - PP écosystème : aucune (interne).
   - Chemin stratégique : abus de privilège -> manipulation données -> dissimulation.
   - Scénario opérationnel : T1078.003 -> T1565 -> T1070.
   - Vraisemblance opérationnelle : V3.

### Annexe E - Glossaire ANSSI

| Terme | Définition |
|---|---|
| SR | Source de Risque. Élément à l'origine du risque. |
| OV | Objectif Visé. Finalité poursuivie par la SR. |
| ER | Événement Redouté. Atteinte à un critère DIC sur une valeur métier. |
| PACS | Plan d'Amélioration Continue de la Sécurité. Livrable de l'atelier 5. |
| DIC | Disponibilité, Intégrité, Confidentialité. Critères de sécurité primaires. |
| Valeur métier | Service, activité ou information à protéger (terminologie Module 1/2). |
| Bien support | Composant qui porte la valeur métier (terminologie Module 2). |
| Écosystème | Ensemble des parties prenantes externes en interaction avec l'organisme. |
| Socle de sécurité | Ensemble des règles et mesures applicables (référentiels, état de l'art). |
| Cycle stratégique | Réévaluation longue des ateliers 1-3 et 5. |
| Cycle opérationnel | Réévaluation courte des ateliers 4 et 5. |
| V1 à V4 | Échelle ANSSI de vraisemblance opérationnelle. |

### Annexe F - Correspondance vocabulaire ANSSI <-> code

| Vocabulaire ANSSI | Code (modèle Django) | App |
|---|---|---|
| Mission | StudyFramework.mission_statement | risks |
| Cadre d'étude | StudyFramework | risks |
| Atelier | EbiosWorkshopProgress | risks |
| Valeur métier | Activity / EssentialAsset | context / assets |
| Bien support | SupportAsset | assets |
| Socle de sécurité | SecurityBaseline | risks |
| Événement redouté | FearedEvent | risks |
| Écart au socle | BaselineGap | risks |
| Source de risque (SR) | RiskSource | risks |
| Objectif visé (OV) | TargetedObjective | risks |
| Couple SR/OV | RiskSourceObjectivePair | risks |
| Partie prenante écosystème | EcosystemStakeholder | risks |
| Niveau de menace | EcosystemStakeholder.threat_level | risks |
| Zone (contrôle/surveillance/danger) | EcosystemStakeholder.threat_zone | risks |
| Scénario stratégique | StrategicScenario | risks |
| Chemin d'attaque | StrategicScenario.attack_path (via AttackPathStep) | risks |
| Étape | AttackPathStep | risks |
| Scénario opérationnel | OperationalScenario | risks |
| Mode opératoire | OperationalScenario.attack_techniques (via AttackTechnique) | risks |
| Technique MITRE | MitreAttackTechnique | risks |
| Vraisemblance V1-V4 | OperationalScenario.likelihood_v | risks |
| Gravité | OperationalScenario.gravity_level / FearedEvent.gravity_level | risks |
| Synthèse | EbiosSummary | risks |
| PACS | EbiosSummary.pacs_summary + PACSMeasure | risks |
| Stratégie résiduelle | EbiosSummary.residual_risk_strategy | risks |
| Risque résiduel | Risk.residual_risk_level | risks |

### Annexe G - Note de remplacement de M4 §4

La section 4 du document M4 (« Modèle de données - Sous-module EBIOS RM ») est obsolète. La présente spec M4bis la remplace intégralement. Les implémentations à venir doivent se référer à ce document. Les références croisées vers M4 §2 (socle commun), §5 (règles), §6 (API), §7 (UI), §10 (export) restent valides pour les parties non EBIOS.

---

*Fin des spécifications du Module 4 bis - EBIOS Risk Manager (ANSSI v1.5).*
