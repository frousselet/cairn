# Module 4 : Gestion des Risques

## Spécifications fonctionnelles et techniques

**Version :** 1.0
**Date :** 27 février 2026
**Statut :** Draft

---

## Entities in this module

- [RiskAssessment](risk-assessment.md)
- [RiskCriteria](risk-criteria.md) (with ScaleLevel and RiskLevel sub-entities)
- [Risk](risk.md)
- [RiskTreatmentPlan](risk-treatment-plan.md) (with TreatmentAction sub-entity)
- [RiskAcceptance](risk-acceptance.md)
- [ISO27005Risk](iso27005-risk.md) (ISO 27005 sub-module)
- [EBIOS RM sub-module](ebios-rm/README.md)

---

## 1. Présentation générale

### 1.1 Objectif du module

Le module **Gestion des Risques** permet de conduire l'appréciation et le traitement des risques liés à la sécurité de l'information selon deux méthodologies complémentaires :

- **ISO 27005:2022** : Approche systématique d'appréciation des risques basée sur l'identification des menaces, vulnérabilités et conséquences sur les actifs, avec évaluation quantitative ou qualitative de la vraisemblance et de l'impact.
- **EBIOS RM** (Expression des Besoins et Identification des Objectifs de Sécurité : Risk Manager) : Approche structurée en 5 ateliers, orientée vers l'identification des sources de risque, la construction de scénarios stratégiques et opérationnels, et le traitement itératif des risques.

Le module est conçu avec un **socle commun** (critères de risque, registre, traitement) et deux **sous-modules méthodologiques** qui partagent les entités transversales. Une appréciation des risques peut être conduite selon l'une ou l'autre méthodologie, et les résultats convergent vers un registre de risques unifié.

### 1.2 Périmètre fonctionnel

Le module se décompose en trois parties :

**A. Socle commun :**
1. Contexte de l'appréciation des risques (périmètre, critères, échelles)
2. Registre des risques (vue consolidée)
3. Traitement des risques (plans, options, suivi)
4. Cartographie et reporting

**B. Sous-module ISO 27005 :**
1. Identification des risques (menaces, vulnérabilités, conséquences)
2. Analyse des risques (vraisemblance, impact, niveau de risque)
3. Évaluation des risques (comparaison aux critères d'acceptation)

**C. Sous-module EBIOS RM :**
1. Atelier 1 : Socle de sécurité (cadrage, périmètre métier et technique, écarts)
2. Atelier 2 : Sources de risque (SR, objectifs visés OV, couples SR/OV)
3. Atelier 3 : Scénarios stratégiques (parties prenantes, chemins d'attaque, scénarios)
4. Atelier 4 : Scénarios opérationnels (modes opératoires, scénarios techniques)
5. Atelier 5 : Traitement du risque (stratégie, PACS, risques résiduels)

### 1.3 Dépendances avec les autres modules

| Module cible | Nature de la dépendance |
|---|---|
| Contexte et Organisation | Le périmètre (Scope), les enjeux et les parties intéressées alimentent le contexte d'appréciation des risques. Les activités métier sont les objets de l'atelier 1 EBIOS RM. |
| Gestion des actifs | Les biens essentiels portent les besoins de sécurité (DIC) et définissent les valeurs métier impactées. Les biens supports sont les cibles des vulnérabilités et des scénarios opérationnels. |
| Conformité | Les non-conformités peuvent générer des risques. Les exigences de conformité peuvent être liées à des risques identifiés. |
| Mesures | Les mesures de sécurité réduisent le niveau de risque. Le traitement des risques génère des mesures nouvelles ou renforcées. |
| Fournisseurs | Les fournisseurs constituent des parties prenantes de l'écosystème (Atelier 3 EBIOS RM) et peuvent être des vecteurs de risque. |
| Audits | Les constats d'audit peuvent révéler des risques ou valider l'efficacité des traitements. |
| Incidents | Les incidents alimentent la réévaluation des risques et valident (ou invalident) les scénarios identifiés. |

---

## Sous-module ISO 27005

Le sous-module ISO 27005 s'appuie sur l'approche par triplet (menace × vulnérabilité × actif) pour l'analyse de risque. Il s'appuie sur les entités `Threat`, `Vulnerability` et `ISO27005Risk`, alimentées par des catalogues prédéfinis (ISO 27005 Annexe A, ENISA Threat Landscape, CWE).

Voir l'entité dédiée : [ISO27005Risk](iso27005-risk.md).

---

## Sous-module EBIOS RM

Le sous-module EBIOS RM implémente la méthode ANSSI EBIOS RM v1.5 (édition 2024), structurée en 5 ateliers (W1 à W5) complétés par un cadre d'étude pré-requis (W0). Il alimente le registre des risques unifié via la consolidation des scénarios stratégiques et opérationnels.

Voir la documentation dédiée du sous-module : [EBIOS RM](ebios-rm/README.md).

> **Note de remplacement (29 mai 2026)** : la section 4 du document source M4 (Modèle de données EBIOS RM) est **obsolète** et entièrement remplacée par le document dédié [ebios-rm/README.md](ebios-rm/README.md), qui aligne le sous-module EBIOS RM sur le guide ANSSI v1.5 (2024). Le M4bis ajoute notamment le cadre d'étude (atelier 0), le suivi des portes de validation par atelier, les formules de scoring ANSSI (niveau de menace SR, niveau de menace écosystème, vraisemblance V1-V4), le cycle stratégique vs opérationnel, l'intégration MITRE ATT&CK et la structuration du PACS. Toute implémentation EBIOS RM doit se référer au M4bis. Les sections suivantes (règles, API, UI, permissions, export) restent valides pour les parties non EBIOS.

---

## 5. Règles de gestion

### 5.1 Règles générales

| ID | Règle |
|---|---|
| RG-01 | Toute appréciation des risques doit être rattachée à un **Scope** et utiliser un jeu de **RiskCriteria**. |
| RG-02 | La suppression d'un risque référencé par le module Mesures, Incidents ou Conformité est interdite. La désactivation via `status = closed` est utilisée à la place. |
| RG-03 | Toute modification d'un objet génère une entrée dans le **journal d'audit**. |
| RG-04 | Les niveaux de risque (initial, actuel, résiduel) sont **calculés automatiquement** via la matrice définie dans les `RiskCriteria` associés. |
| RG-05 | Les codes de référence suivent un format paramétrable avec incrémentation automatique. |

### 5.2 Règles du socle commun

| ID | Règle |
|---|---|
| RS-01 | Le **niveau de risque** est déterminé par croisement vraisemblance × impact dans la `risk_matrix` des `RiskCriteria`. |
| RS-02 | Un risque avec `current_risk_level` ≥ `acceptance_threshold` et `treatment_decision = not_decided` déclenche une **alerte** de traitement requis. |
| RS-03 | Un risque avec `treatment_decision = accept` doit posséder un enregistrement `RiskAcceptance` valide. Le système émet une alerte si l'acceptation est expirée (`valid_until` dépassé). |
| RS-04 | Un `RiskTreatmentPlan` avec `target_date` dépassée et `status ≠ completed` ou `cancelled` passe automatiquement en `status = overdue`. |
| RS-05 | La complétion d'un `RiskTreatmentPlan` déclenche une **suggestion de réévaluation** du risque associé (recalcul du niveau résiduel). |
| RS-06 | La validation d'une `RiskAssessment` verrouille ses données en modification. Toute modification ultérieure nécessite de créer une nouvelle version ou de repasser le statut en `in_progress`. |

### 5.3 Règles ISO 27005

| ID | Règle |
|---|---|
| RI-01 | Un `ISO27005Risk` est rattaché à une appréciation de `methodology = iso27005`. |
| RI-02 | La `combined_likelihood` est calculée comme `MAX(threat_likelihood, vulnerability_exposure)` par défaut. Ce mode de calcul est paramétrable (MAX, MOYENNE, ou formule personnalisée). |
| RI-03 | Le `max_impact` est calculé comme `MAX(impact_confidentiality, impact_integrity, impact_availability)`. Les impacts non renseignés sont exclus du calcul. |
| RI-04 | À la création d'un `ISO27005Risk`, un `Risk` correspondant est automatiquement proposé à l'utilisateur pour consolidation dans le registre. L'utilisateur peut fusionner avec un risque existant ou créer un nouveau. |

### 5.4 Règles EBIOS RM

| ID | Règle |
|---|---|
| RE-01 | Les entités EBIOS RM sont rattachées à une appréciation de `methodology = ebios_rm`. |
| RE-02 | Un `FearedEvent` est associé à un seul critère DIC (`confidentiality`, `integrity` ou `availability`). Pour un même bien essentiel, il peut exister jusqu'à 3 événements redoutés (un par critère). |
| RE-03 | Seuls les couples SR/OV marqués `is_retained = true` sont utilisables dans les scénarios stratégiques (atelier 3). |
| RE-04 | Seuls les scénarios stratégiques marqués `is_retained = true` sont déclinables en scénarios opérationnels (atelier 4). |
| RE-05 | Chaque `StrategicScenario` et `OperationalScenario` peut être consolidé en `Risk` dans le registre commun via le champ `risk_id`. |
| RE-06 | Le `gravity_level` d'un scénario opérationnel est par défaut hérité du scénario stratégique parent. L'utilisateur peut l'ajuster avec justification. |
| RE-07 | Les étapes du chemin d'attaque (`AttackPathStep`) doivent respecter un ordre logique (`order` croissant). |
| RE-08 | Les techniques d'attaque (`AttackTechnique`) peuvent référencer le framework **MITRE ATT&CK**. Le système propose une autocomplétion basée sur un catalogue intégré. |

> Les règles spécifiques EBIOS RM détaillées (RE-01 à RE-19) du M4bis sont documentées dans [ebios-rm/README.md](ebios-rm/README.md).

---

## 6. Spécifications API REST

### 6.1 Conventions générales

Identiques aux modules précédents. Base URL : `/api/v1/risks/`

### 6.2 Endpoints : Socle commun

#### Risk Assessments (Appréciations)

| Méthode | Endpoint | Description |
|---|---|---|
| `GET` | `/assessments` | Lister toutes les appréciations |
| `POST` | `/assessments` | Créer une appréciation |
| `GET` | `/assessments/{id}` | Détail d'une appréciation |
| `PUT` | `/assessments/{id}` | Mise à jour complète |
| `PATCH` | `/assessments/{id}` | Mise à jour partielle |
| `DELETE` | `/assessments/{id}` | Supprimer (si en draft) |
| `POST` | `/assessments/{id}/validate` | Valider l'appréciation |
| `POST` | `/assessments/{id}/duplicate` | Dupliquer pour nouvelle itération |
| `GET` | `/assessments/{id}/export` | Export (PDF, DOCX, JSON) |
| `GET` | `/assessments/{id}/summary` | Synthèse (KPIs) |

#### Risk Criteria (Critères)

| Méthode | Endpoint | Description |
|---|---|---|
| `GET` | `/criteria` | Lister les jeux de critères |
| `POST` | `/criteria` | Créer un jeu de critères |
| `GET` | `/criteria/{id}` | Détail d'un jeu de critères |
| `PUT` | `/criteria/{id}` | Mise à jour complète |
| `PATCH` | `/criteria/{id}` | Mise à jour partielle |
| `DELETE` | `/criteria/{id}` | Supprimer (si non utilisé) |
| `GET` | `/criteria/{id}/matrix-preview` | Aperçu visuel de la matrice |

#### Risk Register (Registre des risques)

| Méthode | Endpoint | Description |
|---|---|---|
| `GET` | `/risks` | Lister tous les risques (registre, filtrable) |
| `POST` | `/risks` | Créer un risque manuellement |
| `GET` | `/risks/{id}` | Détail d'un risque |
| `PUT` | `/risks/{id}` | Mise à jour complète |
| `PATCH` | `/risks/{id}` | Mise à jour partielle |
| `DELETE` | `/risks/{id}` | Supprimer (si non référencé) |
| `GET` | `/risks/{id}/treatment-plans` | Lister les plans de traitement |
| `GET` | `/risks/{id}/acceptances` | Lister les acceptations |
| `GET` | `/risks/{id}/history` | Historique des évaluations |
| `GET` | `/risks/matrix` | Cartographie des risques (données pour matrice) |
| `GET` | `/risks/dashboard` | Tableau de bord (KPIs) |

**Paramètres de filtrage :**

- `?assessment_id={uuid}`
- `?methodology=iso27005|ebios_rm`
- `?risk_source=iso27005_analysis|ebios_strategic_scenario|manual`
- `?treatment_decision=accept|mitigate|transfer|avoid|not_decided`
- `?status=identified|analyzed|treatment_in_progress|accepted`
- `?initial_risk_level_min=3`
- `?current_risk_level_min=2`
- `?risk_owner_id={uuid}`
- `?affected_essential_asset_id={uuid}`
- `?priority=high,critical`
- `?search=terme`

#### Treatment Plans (Plans de traitement)

| Méthode | Endpoint | Description |
|---|---|---|
| `GET` | `/treatment-plans` | Lister tous les plans de traitement |
| `POST` | `/treatment-plans` | Créer un plan de traitement |
| `GET` | `/treatment-plans/{id}` | Détail d'un plan |
| `PUT` | `/treatment-plans/{id}` | Mise à jour |
| `PATCH` | `/treatment-plans/{id}` | Mise à jour partielle |
| `DELETE` | `/treatment-plans/{id}` | Supprimer |
| `POST` | `/treatment-plans/{id}/actions` | Ajouter une action |
| `PUT` | `/treatment-plans/{id}/actions/{action_id}` | Modifier une action |
| `DELETE` | `/treatment-plans/{id}/actions/{action_id}` | Supprimer une action |
| `GET` | `/treatment-plans/overdue` | Plans en retard |

#### Risk Acceptances (Acceptations)

| Méthode | Endpoint | Description |
|---|---|---|
| `GET` | `/acceptances` | Lister toutes les acceptations |
| `POST` | `/acceptances` | Créer une acceptation |
| `GET` | `/acceptances/{id}` | Détail d'une acceptation |
| `PATCH` | `/acceptances/{id}` | Mise à jour (renouvellement, révocation) |
| `GET` | `/acceptances/expiring` | Acceptations arrivant à expiration |

### 6.3 Endpoints : ISO 27005

#### Threats (Menaces)

| Méthode | Endpoint | Description |
|---|---|---|
| `GET` | `/iso27005/threats` | Lister les menaces |
| `POST` | `/iso27005/threats` | Créer une menace |
| `GET` | `/iso27005/threats/{id}` | Détail d'une menace |
| `PUT` | `/iso27005/threats/{id}` | Mise à jour |
| `DELETE` | `/iso27005/threats/{id}` | Supprimer |
| `GET` | `/iso27005/threats/catalog` | Catalogue de menaces prédéfini |
| `POST` | `/iso27005/threats/import-catalog` | Importer depuis le catalogue |

#### Vulnerabilities (Vulnérabilités)

| Méthode | Endpoint | Description |
|---|---|---|
| `GET` | `/iso27005/vulnerabilities` | Lister les vulnérabilités |
| `POST` | `/iso27005/vulnerabilities` | Créer une vulnérabilité |
| `GET` | `/iso27005/vulnerabilities/{id}` | Détail |
| `PUT` | `/iso27005/vulnerabilities/{id}` | Mise à jour |
| `DELETE` | `/iso27005/vulnerabilities/{id}` | Supprimer |
| `GET` | `/iso27005/vulnerabilities/catalog` | Catalogue prédéfini |

#### ISO 27005 Risk Analysis

| Méthode | Endpoint | Description |
|---|---|---|
| `GET` | `/iso27005/analyses` | Lister les analyses de risque ISO 27005 |
| `POST` | `/iso27005/analyses` | Créer une analyse |
| `GET` | `/iso27005/analyses/{id}` | Détail d'une analyse |
| `PUT` | `/iso27005/analyses/{id}` | Mise à jour |
| `DELETE` | `/iso27005/analyses/{id}` | Supprimer |
| `POST` | `/iso27005/analyses/{id}/consolidate` | Consolider en risque du registre |
| `GET` | `/assessments/{id}/iso27005/summary` | Synthèse ISO 27005 d'une appréciation |

### 6.4 Endpoints : EBIOS RM

Les endpoints EBIOS RM sont documentés dans [ebios-rm/README.md](ebios-rm/README.md#6-spécifications-api-rest). Base URL EBIOS : `/api/v1/risks/ebios/`.

### 6.5 Endpoints transversaux

| Méthode | Endpoint | Description |
|---|---|---|
| `GET` | `/risks/dashboard` | Tableau de bord global du module |
| `GET` | `/risks/export` | Export global (PDF, DOCX, JSON) |
| `GET` | `/risks/audit-trail` | Journal d'audit du module |
| `GET` | `/risks/config/enums` | Lister les listes de valeurs |
| `PUT` | `/risks/config/enums/{enum_name}` | Modifier une liste de valeurs |
| `GET` | `/risks/statistics` | Statistiques globales |
| `GET` | `/risks/alerts` | Alertes actives |

---

## 7. Spécifications d'interface utilisateur

### 7.1 Navigation

Le module est accessible via un élément de navigation principal « Gestion des Risques » se décomposant en :

- **Appréciations** (liste des campagnes)
- **Registre des risques** (vue consolidée)
- **ISO 27005** (sous-menu : Menaces, Vulnérabilités, Analyses)
- **EBIOS RM** (sous-menu : Atelier 1 à 5)
- **Traitements** (plans de traitement, acceptations)
- **Cartographie** (matrices de risque)
- **Tableau de bord**

### 7.2 Vue « Appréciations »

- **Liste :** Tableau avec colonnes (Référence, Nom, Méthodologie, Date, Responsable, Nombre de risques, Statut). Badge de méthodologie (ISO 27005 / EBIOS RM).
- **Création :** Assistant en étapes : choix de la méthodologie → sélection du périmètre → sélection des critères de risque → informations générales.
- **Détail :** Vue de synthèse avec accès aux sous-modules et progression de l'analyse.

### 7.3 Vue « Critères de risque »

- **Éditeur d'échelles :** Interface de configuration des niveaux de vraisemblance et d'impact (ajout, modification, suppression de niveaux avec libellé, description et couleur).
- **Éditeur de matrice :** Grille interactive vraisemblance (lignes) × impact (colonnes) où chaque cellule est assignée à un niveau de risque par sélection. Aperçu visuel coloré en temps réel.
- **Niveaux de risque :** Configuration des niveaux résultants avec seuil d'acceptation.

### 7.4 Vue « Registre des risques »

- **Liste :** Tableau avec colonnes (Référence, Nom, Source, Biens impactés, C/I/D, Vraisemblance, Impact, Niveau initial, Niveau actuel, Niveau résiduel, Traitement, Propriétaire, Statut). Code couleur par niveau de risque. Filtres avancés.
- **Matrice de risques :** Vue matricielle vraisemblance × impact positionnant chaque risque sous forme de bulle (taille proportionnelle au nombre de biens impactés). Bascule entre risque initial / actuel / résiduel.
- **Vue comparée :** Superposition des positions initiales et résiduelles pour visualiser l'effet du traitement.
- **Détail / Édition :** Formulaire avec onglets (Identification, Analyse, Traitement, Acceptation, Historique, Relations).

### 7.5 Vues ISO 27005

#### 7.5.1 Menaces et vulnérabilités

- **Listes :** Tableaux filtrables avec accès au catalogue prédéfini.
- **Catalogue :** Bibliothèque de menaces et vulnérabilités avec sélection et import.

#### 7.5.2 Analyse de risque

- **Vue de travail :** Interface de création des triplets (menace × vulnérabilité × actif) avec évaluation de la vraisemblance et de l'impact. Mode formulaire ou mode tableau en ligne.
- **Matrice croisée :** Vue menaces × vulnérabilités avec les actifs concernés et les niveaux de risque.
- **Consolidation :** Bouton de consolidation vers le registre avec option de fusion.

### 7.6 Vues EBIOS RM

Les vues EBIOS RM sont documentées dans [ebios-rm/README.md](ebios-rm/README.md#8-spécifications-dinterface-utilisateur).

### 7.7 Tableau de bord du module

- Nombre total de risques par niveau (initial, actuel, résiduel)
- Répartition par décision de traitement (camembert)
- Évolution des niveaux de risque dans le temps (courbes de tendance)
- Cartographie matricielle des risques (miniature interactive)
- Top 10 des risques les plus critiques
- Plans de traitement en retard
- Acceptations de risques arrivant à expiration
- Biens essentiels les plus exposés (nombre de risques associés)
- Couverture des risques par les mesures existantes
- Alertes et actions requises

---

## 8. Permissions et contrôle d'accès

### 8.1 Modèle RBAC

| Permission | Description |
|---|---|
| `risks.assessment.read` | Consulter les appréciations |
| `risks.assessment.write` | Créer/modifier les appréciations |
| `risks.assessment.validate` | Valider une appréciation |
| `risks.assessment.delete` | Supprimer les appréciations |
| `risks.criteria.read` | Consulter les critères de risque |
| `risks.criteria.write` | Créer/modifier les critères |
| `risks.criteria.delete` | Supprimer les critères |
| `risks.risk.read` | Consulter le registre des risques |
| `risks.risk.write` | Créer/modifier les risques |
| `risks.risk.delete` | Supprimer les risques |
| `risks.treatment.read` | Consulter les plans de traitement |
| `risks.treatment.write` | Créer/modifier les plans de traitement |
| `risks.treatment.delete` | Supprimer les plans de traitement |
| `risks.acceptance.read` | Consulter les acceptations |
| `risks.acceptance.write` | Créer/modifier les acceptations (réservé aux propriétaires de risque) |
| `risks.iso27005.read` | Consulter les données ISO 27005 (menaces, vulnérabilités, analyses) |
| `risks.iso27005.write` | Créer/modifier les données ISO 27005 |
| `risks.iso27005.delete` | Supprimer les données ISO 27005 |
| `risks.ebios.read` | Consulter les données EBIOS RM (ateliers 1-5) |
| `risks.ebios.write` | Créer/modifier les données EBIOS RM |
| `risks.ebios.delete` | Supprimer les données EBIOS RM |
| `risks.export` | Exporter les données du module |
| `risks.config.manage` | Gérer les catalogues et listes de valeurs |
| `risks.audit_trail.read` | Consulter le journal d'audit |

### 8.2 Rôles applicatifs suggérés

| Rôle | Permissions |
|---|---|
| **Administrateur** | Toutes les permissions |
| **RSSI / DPO** | Toutes sauf `*.delete` et `config.manage` |
| **Analyste risque** | `*.read` + `*.write` + `risks.iso27005.*` + `risks.ebios.*` (hors validate et config) |
| **Propriétaire de risque** | `risks.risk.read` + `risks.treatment.read` + `risks.acceptance.write` (restreint à ses risques) |
| **Auditeur** | `*.read` + `risks.export` + `risks.audit_trail.read` |
| **Lecteur** | `*.read` uniquement |

---

## 9. Journalisation et traçabilité

### 9.1 Audit Trail

Actions spécifiques à ce module :

| Action | Description |
|---|---|
| `create` | Création d'une entité du module |
| `update` | Modification |
| `delete` | Suppression |
| `validate_assessment` | Validation d'une appréciation |
| `consolidate_risk` | Consolidation d'une analyse/scénario en risque du registre |
| `accept_risk` | Acceptation formelle d'un risque |
| `revoke_acceptance` | Révocation d'une acceptation |
| `complete_treatment` | Clôture d'un plan de traitement |
| `evaluate_risk` | Évaluation/réévaluation d'un risque |

### 9.2 Rétention

Identique aux modules précédents. Durée paramétrable, défaut 7 ans.

---

## 10. Export et reporting

### 10.1 Formats d'export

| Format | Contenu |
|---|---|
| **JSON** | Export brut structuré |
| **PDF** | Rapport formaté avec matrices, cartographies, détail des risques |
| **DOCX** | Document éditable |
| **CSV** | Export tabulaire (registre, menaces, vulnérabilités, scénarios) |

### 10.2 Rapports prédéfinis

| Rapport | Description |
|---|---|
| Registre des risques | Liste complète avec niveaux initial/actuel/résiduel et traitements |
| Cartographie des risques | Matrice vraisemblance × impact (avant et après traitement) |
| Rapport d'appréciation ISO 27005 | Synthèse complète d'une appréciation ISO 27005 |
| Rapport d'appréciation EBIOS RM | Synthèse complète des 5 ateliers EBIOS RM |
| Plan de traitement des risques | Liste des plans de traitement avec avancement |
| Rapport d'acceptation des risques | Risques acceptés avec justification et dates de revue |
| Rapport de tendance | Évolution des niveaux de risque dans le temps |
| PACS (EBIOS RM) | Plan d'Amélioration Continue de la Sécurité |
| Matrice MITRE ATT&CK | Mapping des techniques d'attaque identifiées |

---

## 11. Notifications et alertes

| Événement | Destinataires | Canal |
|---|---|---|
| Risque de niveau critique identifié | RSSI, Propriétaire du risque | In-app, email |
| Traitement requis (risque au-dessus du seuil, non traité) | Propriétaire du risque | In-app, email |
| Plan de traitement en retard | Responsable du plan, RSSI | In-app, email |
| Acceptation de risque arrivant à expiration (30 jours avant) | Propriétaire du risque, RSSI | In-app, email |
| Acceptation de risque expirée | Propriétaire du risque, RSSI | In-app, email |
| Appréciation en attente de validation | Validateur | In-app, email |
| Date de revue d'un risque atteinte | Propriétaire du risque | In-app, email |
| Nouveau risque consolidé dans le registre | RSSI | In-app |
| Plan de traitement complété : suggestion de réévaluation | Propriétaire du risque | In-app |
| Réévaluation périodique requise (fréquence paramétrable) | Responsable de l'appréciation | In-app, email |

---

## 12. Considérations techniques

### 12.1 Calcul automatique des niveaux de risque

Le calcul du niveau de risque est effectué côté serveur à partir de la matrice définie dans les `RiskCriteria` :

```
risk_level = risk_matrix[likelihood][impact]
```

La matrice est stockée au format JSON :

```json
{
  "matrix": [
    [1, 1, 2, 3],
    [1, 2, 3, 4],
    [2, 3, 3, 4],
    [3, 3, 4, 4]
  ]
}
```

Où `matrix[likelihood_index][impact_index]` retourne le `risk_level`.

Le recalcul est déclenché à chaque modification de vraisemblance ou d'impact, et à la modification des critères de risque (recalcul de tous les risques associés).

### 12.2 Consolidation des risques

Le mécanisme de consolidation permet de créer un `Risk` dans le registre commun à partir d'un `ISO27005Risk`, `StrategicScenario` ou `OperationalScenario` :

1. L'utilisateur initie la consolidation depuis l'entité source
2. Le système propose de créer un nouveau risque ou de fusionner avec un risque existant (recherche par similarité)
3. Les données sont pré-remplies à partir de l'entité source
4. L'utilisateur valide et ajuste
5. Le lien bidirectionnel est maintenu (`source_entity_id` / `risk_id`)

### 12.3 Catalogue MITRE ATT&CK

Un catalogue MITRE ATT&CK est intégré et mis à jour périodiquement. Il fournit :

- La liste des tactiques et techniques avec descriptions
- L'autocomplétion lors de la saisie des techniques d'attaque
- La visualisation en heatmap des techniques identifiées dans les scénarios

### 12.4 Catalogues de menaces et vulnérabilités

Des catalogues prédéfinis sont fournis à l'installation :

- **Menaces** : basé sur ISO 27005 Annexe A et ENISA Threat Landscape
- **Vulnérabilités** : basé sur ISO 27005 Annexe D et CWE (Common Weakness Enumeration)

Ces catalogues sont importables en un clic et personnalisables ensuite.

### 12.5 Multi-tenant

Identique aux modules précédents. Les catalogues prédéfinis sont globaux (partagés entre tenants) ; les éléments ajoutés par les utilisateurs sont isolés par tenant.

### 12.6 Internationalisation (i18n)

Identique aux modules précédents. Les catalogues prédéfinis sont fournis en français et en anglais.

### 12.7 Performances

- Les listes paginées ne doivent pas dépasser **200 ms** pour 1 000 enregistrements.
- Le calcul de la matrice de risques pour 500 risques doit s'exécuter en moins de **1 seconde**.
- Le graphe de l'écosystème (Atelier 3) doit se charger en moins de **2 secondes** pour 50 nœuds.
- La heatmap MITRE ATT&CK doit se charger en moins de **1 seconde**.
- Les tableaux de bord agrégés sont mis en cache avec un TTL de **5 minutes**.
- Les exports volumineux sont traités de manière asynchrone.

### 12.8 Webhooks

Événements spécifiques :

- `risks.assessment.created`, `validated`
- `risks.risk.created`, `updated`, `consolidated`
- `risks.risk.level_changed` (changement de niveau de risque)
- `risks.treatment_plan.created`, `completed`, `overdue`
- `risks.acceptance.created`, `expired`, `revoked`
- `risks.ebios.scenario_created` (stratégique ou opérationnel)

---

## 13. Critères d'acceptation

### 13.1 Socle commun

- [ ] CRUD complet sur les appréciations, critères, risques, plans de traitement et acceptations
- [ ] La matrice de risques est configurable (échelles, niveaux, couleurs)
- [ ] Les niveaux de risque (initial, actuel, résiduel) sont calculés automatiquement via la matrice
- [ ] Le registre des risques est consultable avec tous les filtres
- [ ] La cartographie matricielle des risques est interactive (bascule initial/actuel/résiduel)
- [ ] Les plans de traitement supportent le suivi d'avancement et la détection de retard
- [ ] L'acceptation formelle des risques est fonctionnelle avec gestion d'expiration
- [ ] Le tableau de bord affiche les données correctes avec tendances

### 13.2 ISO 27005

- [ ] Les catalogues de menaces et vulnérabilités sont importables
- [ ] L'analyse de risque par triplet (menace × vulnérabilité × actif) est fonctionnelle
- [ ] Le calcul combiné de vraisemblance est correct
- [ ] La consolidation vers le registre fonctionne (création et fusion)
- [ ] Le rapport d'appréciation ISO 27005 est générable

### 13.3 EBIOS RM

- [ ] Les 5 ateliers sont accessibles et séquencés
- [ ] Atelier 1 : les événements redoutés et écarts au socle sont gérables
- [ ] Atelier 2 : les sources de risque, objectifs visés et couples SR/OV sont gérables, la matrice croisée est fonctionnelle
- [ ] Atelier 3 : le graphe de l'écosystème est interactif, les scénarios stratégiques et chemins d'attaque sont éditables
- [ ] Atelier 4 : les scénarios opérationnels et techniques d'attaque sont éditables, l'autocomplétion MITRE ATT&CK fonctionne
- [ ] Atelier 5 : la cartographie avant/après est fonctionnelle, le PACS est générable
- [ ] La consolidation des scénarios vers le registre fonctionne
- [ ] Le rapport d'appréciation EBIOS RM complet est générable

### 13.4 API

- [ ] Tous les endpoints documentés sont implémentés et fonctionnels
- [ ] La documentation OpenAPI (Swagger) est générée automatiquement
- [ ] Les codes d'erreur et structures de réponse sont conformes
- [ ] Les webhooks sont déclenchés pour chaque événement de mutation

### 13.5 Sécurité

- [ ] Le contrôle d'accès RBAC est appliqué sur chaque endpoint et vue
- [ ] La restriction « propriétaire de risque » limite bien l'acceptation aux risques dont l'utilisateur est propriétaire
- [ ] Le journal d'audit enregistre toutes les opérations
- [ ] Les données sont isolées entre tenants

### 13.6 Performance

- [ ] Les temps de réponse respectent les seuils définis (§12.7)
- [ ] Les exports volumineux sont traités de manière asynchrone

---

*Fin des spécifications du Module 4 : Gestion des Risques*
