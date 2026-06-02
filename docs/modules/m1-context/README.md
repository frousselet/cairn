# Module 1 : Contexte et Organisation

## Spécifications fonctionnelles et techniques

**Version :** 1.0
**Date :** 27 février 2026
**Statut :** Draft

---

## Entities in this module

- [Scope](scope.md)
- [Issue](issue.md)
- [Stakeholder](stakeholder.md) (et `StakeholderExpectation`)
- [Objective](objective.md)
- [SwotAnalysis](swot.md) (et `SwotItem`)
- [Role](role.md) (et `Responsibility`)
- [Activity](activity.md)

---

## 1. Présentation générale

### 1.1 Objectif du module

Le module **Contexte et Organisation** constitue le socle fondateur de l'outil GRC. Il permet de formaliser et maintenir à jour l'ensemble des éléments de contexte nécessaires à la gouvernance des risques et de la conformité, conformément aux exigences des référentiels ISO 27001, ISO 27005 et EBIOS RM (chapitres 4 et 5 de l'ISO 27001 notamment).

### 1.2 Périmètre fonctionnel

Le module couvre sept sous-domaines :

1. Domaine d'application (périmètre du SMSI ou du dispositif GRC)
2. Enjeux internes et externes
3. Parties intéressées
4. Objectifs de sécurité / conformité
5. Analyse SWOT
6. Rôles et responsabilités
7. Activités et processus métier

### 1.3 Dépendances avec les autres modules

| Module cible | Nature de la dépendance |
|---|---|
| Gestion des actifs | Les activités/processus sont rattachés aux biens essentiels |
| Gestion des risques | Les enjeux et le périmètre alimentent le contexte d'appréciation des risques |
| Conformité | Les parties intéressées expriment des exigences rattachées aux référentiels |
| Mesures | Les objectifs sont déclinés en mesures de sécurité |
| Fournisseurs | Les parties intéressées de type fournisseur alimentent le module fournisseurs |
| Audits | Le périmètre conditionne le programme d'audits |
| Incidents | Les rôles et responsabilités définissent les intervenants en gestion d'incidents |
| Formations | Les rôles conditionnent les besoins en formation |

---

## Règles de gestion

### Règles générales

| ID | Règle |
|---|---|
| RG-01 | Tout objet du module doit être rattaché à un **Scope** (périmètre). |
| ~~RG-02~~ | *Règle retirée.* Initialement : « un seul Scope actif à la fois, les anciennes versions passent en `archived` ». Depuis l'introduction de la hiérarchie de périmètres (`parent_scope_id`), plusieurs Scopes peuvent légitimement être actifs simultanément (un groupe et ses filiales, ou plusieurs périmètres SMSI couvrant des entités distinctes). Le cycle de vie du `status` reste libre - c'est à l'organisation de choisir quels périmètres elle considère actifs. |
| RG-03 | La suppression d'un objet référencé par un autre module est interdite. Une désactivation (`status = inactive` ou `archived`) est utilisée à la place. |
| RG-04 | Toute modification d'un objet génère une entrée dans le **journal d'audit** (audit trail) avec l'identifiant utilisateur, la date, l'ancien et le nouveau état. |
| RG-05 | Les champs `created_at` et `updated_at` sont gérés automatiquement par le système. |
| RG-06 | Les listes de valeurs de type `enum` paramétrables (catégories d'enjeux, catégories de parties intéressées) sont gérées via une table de configuration dédiée. |
| RG-07 | Les relations M2M (many-to-many) sont stockées dans des tables de jointure dédiées. |

### Règles spécifiques

| ID | Règle |
|---|---|
| RS-01 | Un **Issue** de type `internal` ne peut avoir que des catégories internes, et inversement pour `external`. |
| RS-02 | Un **Objective** avec `status = achieved` doit avoir `progress_percentage = 100`. |
| RS-03 | Un **Objective** enfant (`parent_objective_id` renseigné) doit appartenir au même **Scope** que son parent. |
| RS-04 | Une **Activity** enfant doit appartenir au même **Scope** que son parent. |
| RS-05 | Un **SwotItem** de quadrant `strength` ou `weakness` doit être cohérent avec des **Issues** de type `internal` ; `opportunity` et `threat` avec des Issues de type `external`. Cette règle est une recommandation (alerte) et non un blocage. |
| RS-06 | Un **Role** marqué `is_mandatory = true` doit avoir au moins un utilisateur affecté. Le système émet une alerte de conformité dans le cas contraire. |
| RS-07 | La matrice **RACI** (via Responsibility) doit respecter la règle : une seule personne `accountable` par activité. Le système émet une alerte si cette règle est violée. |

---

## Spécifications API REST

### Conventions générales

- **Base URL :** `/api/v1/context/`
- **Format :** JSON (application/json)
- **Authentification :** Bearer Token (JWT) ou API Key
- **Pagination :** `?page=1&page_size=25` (défaut : 25, max : 100)
- **Tri :** `?ordering=name` ou `?ordering=-created_at` (préfixe `-` = descendant)
- **Filtrage :** `?status=active&type=internal`
- **Recherche :** `?search=terme` (recherche full-text sur les champs texte)
- **Inclusion de relations :** `?include=stakeholders,issues`
- **Format de date :** ISO 8601 (`2026-02-27T14:30:00Z`)
- **Codes HTTP :** 200 (OK), 201 (Created), 204 (No Content), 400 (Bad Request), 401 (Unauthorized), 403 (Forbidden), 404 (Not Found), 409 (Conflict), 422 (Unprocessable Entity)

### Structure de réponse standard

```json
{
  "status": "success",
  "data": { },
  "meta": {
    "page": 1,
    "page_size": 25,
    "total_count": 142,
    "total_pages": 6
  }
}
```

**Structure d'erreur :**

```json
{
  "status": "error",
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Validation failed",
    "details": [
      {
        "field": "name",
        "message": "This field is required."
      }
    ]
  }
}
```

### Endpoints : Scope (Domaine d'application)

| Méthode | Endpoint | Description |
|---|---|---|
| `GET` | `/scopes` | Lister les périmètres |
| `POST` | `/scopes` | Créer un périmètre |
| `GET` | `/scopes/{id}` | Détail d'un périmètre |
| `PUT` | `/scopes/{id}` | Mise à jour complète |
| `PATCH` | `/scopes/{id}` | Mise à jour partielle |
| `DELETE` | `/scopes/{id}` | Supprimer (si non référencé) |
| `POST` | `/scopes/{id}/approve` | Approuver un périmètre |
| `POST` | `/scopes/{id}/archive` | Archiver un périmètre |
| `GET` | `/scopes/{id}/history` | Historique des modifications |
| `GET` | `/scopes/{id}/export` | Export (PDF, DOCX, JSON) |

### Endpoints : Issues (Enjeux)

| Méthode | Endpoint | Description |
|---|---|---|
| `GET` | `/scopes/{scope_id}/issues` | Lister les enjeux d'un périmètre |
| `POST` | `/scopes/{scope_id}/issues` | Créer un enjeu |
| `GET` | `/issues/{id}` | Détail d'un enjeu |
| `PUT` | `/issues/{id}` | Mise à jour complète |
| `PATCH` | `/issues/{id}` | Mise à jour partielle |
| `DELETE` | `/issues/{id}` | Supprimer |
| `GET` | `/issues` | Lister tous les enjeux (tous périmètres, filtrable) |
| `GET` | `/issues/categories` | Lister les catégories disponibles |

### Endpoints : Stakeholders (Parties intéressées)

| Méthode | Endpoint | Description |
|---|---|---|
| `GET` | `/scopes/{scope_id}/stakeholders` | Lister les PI d'un périmètre |
| `POST` | `/scopes/{scope_id}/stakeholders` | Créer une PI |
| `GET` | `/stakeholders/{id}` | Détail d'une PI |
| `PUT` | `/stakeholders/{id}` | Mise à jour complète |
| `PATCH` | `/stakeholders/{id}` | Mise à jour partielle |
| `DELETE` | `/stakeholders/{id}` | Supprimer |
| `GET` | `/stakeholders/{id}/expectations` | Lister les attentes d'une PI |
| `POST` | `/stakeholders/{id}/expectations` | Ajouter une attente |
| `PUT` | `/stakeholders/{id}/expectations/{exp_id}` | Modifier une attente |
| `DELETE` | `/stakeholders/{id}/expectations/{exp_id}` | Supprimer une attente |
| `GET` | `/stakeholders/matrix` | Matrice influence/intérêt (données agrégées) |

### Endpoints : Objectives (Objectifs)

| Méthode | Endpoint | Description |
|---|---|---|
| `GET` | `/scopes/{scope_id}/objectives` | Lister les objectifs d'un périmètre |
| `POST` | `/scopes/{scope_id}/objectives` | Créer un objectif |
| `GET` | `/objectives/{id}` | Détail d'un objectif |
| `PUT` | `/objectives/{id}` | Mise à jour complète |
| `PATCH` | `/objectives/{id}` | Mise à jour partielle |
| `DELETE` | `/objectives/{id}` | Supprimer |
| `GET` | `/objectives/{id}/children` | Lister les sous-objectifs |
| `GET` | `/objectives/{id}/measures` | Lister les mesures liées |
| `GET` | `/objectives/tree` | Arborescence complète des objectifs |
| `GET` | `/objectives/dashboard` | Données de tableau de bord (KPIs agrégés) |

### Endpoints : SWOT

| Méthode | Endpoint | Description |
|---|---|---|
| `GET` | `/scopes/{scope_id}/swot-analyses` | Lister les analyses SWOT |
| `POST` | `/scopes/{scope_id}/swot-analyses` | Créer une analyse SWOT |
| `GET` | `/swot-analyses/{id}` | Détail d'une analyse SWOT |
| `PUT` | `/swot-analyses/{id}` | Mise à jour complète |
| `PATCH` | `/swot-analyses/{id}` | Mise à jour partielle |
| `DELETE` | `/swot-analyses/{id}` | Supprimer |
| `POST` | `/swot-analyses/{id}/validate` | Valider l'analyse |
| `POST` | `/swot-analyses/{id}/items` | Ajouter un élément SWOT |
| `PUT` | `/swot-analyses/{id}/items/{item_id}` | Modifier un élément |
| `DELETE` | `/swot-analyses/{id}/items/{item_id}` | Supprimer un élément |
| `PATCH` | `/swot-analyses/{id}/items/reorder` | Réordonner les éléments |
| `GET` | `/swot-analyses/{id}/export` | Export (PDF, image, JSON) |

### Endpoints : Roles (Rôles et responsabilités)

| Méthode | Endpoint | Description |
|---|---|---|
| `GET` | `/scopes/{scope_id}/roles` | Lister les rôles d'un périmètre |
| `POST` | `/scopes/{scope_id}/roles` | Créer un rôle |
| `GET` | `/roles/{id}` | Détail d'un rôle |
| `PUT` | `/roles/{id}` | Mise à jour complète |
| `PATCH` | `/roles/{id}` | Mise à jour partielle |
| `DELETE` | `/roles/{id}` | Supprimer |
| `POST` | `/roles/{id}/assign` | Affecter un utilisateur |
| `DELETE` | `/roles/{id}/assign/{user_id}` | Retirer un utilisateur |
| `GET` | `/roles/{id}/responsibilities` | Lister les responsabilités |
| `POST` | `/roles/{id}/responsibilities` | Ajouter une responsabilité |
| `PUT` | `/roles/{id}/responsibilities/{resp_id}` | Modifier une responsabilité |
| `DELETE` | `/roles/{id}/responsibilities/{resp_id}` | Supprimer une responsabilité |
| `GET` | `/scopes/{scope_id}/raci-matrix` | Matrice RACI complète du périmètre |
| `GET` | `/roles/compliance-check` | Vérifier les rôles obligatoires non pourvus |

### Endpoints : Activities (Activités)

| Méthode | Endpoint | Description |
|---|---|---|
| `GET` | `/scopes/{scope_id}/activities` | Lister les activités d'un périmètre |
| `POST` | `/scopes/{scope_id}/activities` | Créer une activité |
| `GET` | `/activities/{id}` | Détail d'une activité |
| `PUT` | `/activities/{id}` | Mise à jour complète |
| `PATCH` | `/activities/{id}` | Mise à jour partielle |
| `DELETE` | `/activities/{id}` | Supprimer |
| `GET` | `/activities/{id}/children` | Lister les sous-activités |
| `GET` | `/activities/tree` | Arborescence complète |
| `GET` | `/activities/{id}/assets` | Lister les biens essentiels liés |

### Endpoints transversaux

| Méthode | Endpoint | Description |
|---|---|---|
| `GET` | `/context/dashboard` | Tableau de bord synthétique du module |
| `GET` | `/context/export` | Export global du contexte (PDF, DOCX, JSON) |
| `GET` | `/context/audit-trail` | Journal d'audit du module |
| `GET` | `/context/config/enums` | Lister toutes les listes de valeurs paramétrables |
| `PUT` | `/context/config/enums/{enum_name}` | Modifier une liste de valeurs |

---

## Spécifications d'interface utilisateur

### Navigation

Le module est accessible via un élément de navigation principal « Contexte & Organisation » se décomposant en sous-menus correspondant à chaque sous-domaine (Périmètre, Enjeux, Parties intéressées, Objectifs, SWOT, Rôles, Activités).

### Vue « Périmètre » (Scope)

- **Liste :** Tableau avec colonnes (Nom, Version, Statut, Date d'approbation, Date de revue) avec filtres et tri.
- **Détail / Édition :** Formulaire avec onglets : Informations générales, Périmètres (géographique, organisationnel, technique), Exclusions, Référentiels applicables, Historique.
- **Actions :** Créer, Modifier, Approuver, Archiver, Exporter.

### Vue « Enjeux » (Issues)

- **Liste :** Tableau filtrable par type (interne/externe), catégorie, niveau d'impact, statut et tendance. Vue alternative en diagramme de type « radar » ou « heatmap ».
- **Détail / Édition :** Formulaire avec les champs définis dans le modèle de données, section de liaison aux parties intéressées.
- **Visualisation :** Vue matricielle interne/externe avec code couleur par impact.

### Vue « Parties intéressées » (Stakeholders)

- **Liste :** Tableau filtrable par type, catégorie, influence, intérêt.
- **Matrice Influence/Intérêt :** Visualisation graphique positionnant chaque PI sur un quadrant (Informer, Satisfaire, Surveiller, Collaborer).
- **Détail / Édition :** Formulaire avec onglets : Informations, Attentes & Exigences, Relations (enjeux, référentiels).

### Vue « Objectifs » (Objectives)

- **Liste :** Tableau avec barre de progression visuelle, filtrable par catégorie, type, statut, responsable.
- **Arborescence :** Vue hiérarchique (tree view) des objectifs parent/enfant.
- **Tableau de bord :** Graphiques de progression globale, répartition par catégorie, objectifs en retard.
- **Détail / Édition :** Formulaire avec section KPI (valeur cible, actuelle, méthode de mesure).

### Vue « SWOT »

- **Liste :** Tableau des analyses SWOT avec date, statut.
- **Vue matrice :** Affichage classique en 4 quadrants (Forces, Faiblesses, Opportunités, Menaces) avec drag & drop pour réordonner.
- **Détail :** Chaque élément affiche son impact et ses liaisons vers les enjeux et objectifs.
- **Export :** Image (PNG/SVG), PDF.

### Vue « Rôles et responsabilités »

- **Liste :** Tableau des rôles avec nombre d'utilisateurs affectés, type, statut.
- **Matrice RACI :** Vue croisée Activités × Rôles avec cellules RACI colorées. Possibilité de modifier directement dans la matrice.
- **Alertes :** Indicateurs visuels pour les rôles obligatoires non pourvus et les violations de la règle RACI (plusieurs Accountable).
- **Détail / Édition :** Formulaire avec section responsabilités et affectation d'utilisateurs.

### Vue « Activités »

- **Liste :** Tableau filtrable par type, criticité, responsable, statut.
- **Arborescence :** Vue hiérarchique des processus et sous-processus.
- **Cartographie :** Vue graphique des interdépendances entre activités (optionnel, v2).
- **Détail / Édition :** Formulaire avec liaisons vers les parties intéressées, objectifs et biens essentiels.

### Tableau de bord du module

Un tableau de bord synthétique agrège les informations clés :

- Nombre d'enjeux par type et impact
- Matrice influence/intérêt des parties intéressées (miniature)
- Progression globale des objectifs
- Dernière analyse SWOT
- Couverture des rôles obligatoires
- Activités critiques sans propriétaire
- Alertes et actions requises

---

## Permissions et contrôle d'accès

### Modèle RBAC

Le module s'appuie sur un modèle de contrôle d'accès basé sur les rôles (RBAC) défini au niveau global de l'application.

| Permission | Description |
|---|---|
| `context.scope.read` | Consulter les périmètres |
| `context.scope.write` | Créer/modifier les périmètres |
| `context.scope.approve` | Approuver un périmètre |
| `context.scope.delete` | Supprimer un périmètre |
| `context.issue.read` | Consulter les enjeux |
| `context.issue.write` | Créer/modifier les enjeux |
| `context.issue.delete` | Supprimer les enjeux |
| `context.stakeholder.read` | Consulter les parties intéressées |
| `context.stakeholder.write` | Créer/modifier les parties intéressées |
| `context.stakeholder.delete` | Supprimer les parties intéressées |
| `context.objective.read` | Consulter les objectifs |
| `context.objective.write` | Créer/modifier les objectifs |
| `context.objective.delete` | Supprimer les objectifs |
| `context.swot.read` | Consulter les analyses SWOT |
| `context.swot.write` | Créer/modifier les analyses SWOT |
| `context.swot.validate` | Valider une analyse SWOT |
| `context.swot.delete` | Supprimer les analyses SWOT |
| `context.role.read` | Consulter les rôles |
| `context.role.write` | Créer/modifier les rôles |
| `context.role.assign` | Affecter des utilisateurs aux rôles |
| `context.role.delete` | Supprimer les rôles |
| `context.activity.read` | Consulter les activités |
| `context.activity.write` | Créer/modifier les activités |
| `context.activity.delete` | Supprimer les activités |
| `context.config.manage` | Gérer les listes de valeurs paramétrables |
| `context.export` | Exporter les données du module |
| `context.audit_trail.read` | Consulter le journal d'audit |

### Rôles applicatifs suggérés

| Rôle | Permissions |
|---|---|
| **Administrateur** | Toutes les permissions |
| **RSSI / DPO** | Toutes sauf `*.delete` et `config.manage` |
| **Auditeur** | `*.read` + `context.export` + `context.audit_trail.read` |
| **Contributeur** | `*.read` + `*.write` (hors scope.approve et swot.validate) |
| **Lecteur** | `*.read` uniquement |

---

## Journalisation et traçabilité

### Audit Trail

Chaque opération de création, modification ou suppression génère un enregistrement d'audit contenant :

| Champ | Description |
|---|---|
| `id` | Identifiant unique de l'entrée |
| `timestamp` | Horodatage UTC |
| `user_id` | Utilisateur ayant réalisé l'action |
| `action` | `create`, `update`, `delete`, `approve`, `validate`, `archive`, `assign`, `unassign` |
| `entity_type` | Type d'entité concernée (ex. `Scope`, `Issue`, `Stakeholder`) |
| `entity_id` | Identifiant de l'entité concernée |
| `changes` | Objet JSON décrivant les champs modifiés (`field`, `old_value`, `new_value`) |
| `ip_address` | Adresse IP de l'utilisateur |
| `user_agent` | User-agent du navigateur/client |

### Rétention

Les entrées d'audit sont conservées pendant une durée paramétrable (défaut : 7 ans) conformément aux exigences réglementaires.

---

## Export et reporting

### Formats d'export

| Format | Contenu |
|---|---|
| **JSON** | Export brut structuré (pour interopérabilité API) |
| **PDF** | Document formaté avec en-tête, sommaire, sections par entité |
| **DOCX** | Document éditable au format Word |
| **CSV** | Export tabulaire par entité (enjeux, PI, objectifs, activités) |

### Rapports prédéfinis

| Rapport | Description |
|---|---|
| Déclaration d'applicabilité du contexte | Synthèse du périmètre, enjeux et PI |
| Matrice des parties intéressées | Matrice influence/intérêt avec attentes |
| Rapport d'objectifs | État d'avancement de tous les objectifs |
| SWOT | Visualisation SWOT exportable |
| Matrice RACI | Matrice croisée activités × rôles |
| Cartographie des activités | Liste hiérarchique avec criticité |

---

## Notifications et alertes

| Événement | Destinataires | Canal |
|---|---|---|
| Périmètre en attente d'approbation | Approbateurs | In-app, email |
| Date de revue atteinte (scope, enjeu, PI, objectif, SWOT) | Propriétaire / Créateur | In-app, email |
| Rôle obligatoire non pourvu | Administrateur, RSSI | In-app, email |
| Violation de règle RACI | Administrateur | In-app |
| Objectif en retard (target_date dépassée, statut ≠ achieved) | Propriétaire de l'objectif | In-app, email |
| Modification du périmètre actif | Tous les contributeurs du périmètre | In-app |

---

## Considérations techniques

### Versioning des données

Le périmètre (Scope) supporte un mécanisme de versioning pour conserver l'historique des évolutions. Chaque version est un snapshot horodaté des données du périmètre à un instant T.

### Multi-tenant

Le modèle de données supporte le multi-tenant via un champ `tenant_id` (ou organisation) au niveau de chaque entité racine, permettant l'isolation des données entre organisations.

### Internationalisation (i18n)

Tous les libellés d'interface, messages d'erreur et labels d'enums sont externalisés et traduisibles. Le système supporte à minima le français et l'anglais.

### Performances

- Les listes paginées ne doivent pas dépasser un temps de réponse de **200 ms** pour 1 000 enregistrements.
- Les tableaux de bord agrégés sont mis en cache avec un TTL de **5 minutes**.
- Les exports volumineux (> 500 enregistrements) sont traités de manière asynchrone avec notification à l'utilisateur.

### Webhooks

Chaque événement de mutation (création, modification, suppression, changement de statut) peut déclencher un webhook configurable, permettant l'intégration avec des outils tiers (SIEM, ITSM, outils de BI, etc.).

Payload type :

```json
{
  "event": "context.issue.updated",
  "timestamp": "2026-02-27T14:30:00Z",
  "tenant_id": "org_xxx",
  "data": {
    "entity_type": "Issue",
    "entity_id": "uuid-xxx",
    "action": "update",
    "changes": { },
    "actor": {
      "user_id": "uuid-yyy",
      "email": "user@example.com"
    }
  }
}
```

---

## Critères d'acceptation

### Fonctionnels

- [ ] CRUD complet sur les 7 entités du module
- [ ] Toutes les relations entre entités sont fonctionnelles
- [ ] Les vues liste supportent pagination, tri, filtrage et recherche
- [ ] La matrice RACI est consultable et modifiable
- [ ] La matrice Influence/Intérêt est affichable graphiquement
- [ ] La vue SWOT en 4 quadrants est fonctionnelle avec drag & drop
- [ ] L'arborescence des objectifs et activités est navigable
- [ ] Les alertes de conformité (rôles obligatoires, RACI) sont fonctionnelles
- [ ] Les exports sont opérationnels dans tous les formats prévus
- [ ] Le tableau de bord synthétique affiche les données correctes

### API

- [ ] Tous les endpoints documentés sont implémentés et fonctionnels
- [ ] La documentation OpenAPI (Swagger) est générée automatiquement
- [ ] Les codes d'erreur et structures de réponse sont conformes aux spécifications
- [ ] La pagination, le tri et le filtrage fonctionnent sur tous les endpoints de liste
- [ ] Les webhooks sont déclenchés pour chaque événement de mutation

### Sécurité

- [ ] Le contrôle d'accès RBAC est appliqué sur chaque endpoint et chaque vue
- [ ] Le journal d'audit enregistre toutes les opérations
- [ ] Les données sont isolées entre tenants

### Performance

- [ ] Les temps de réponse respectent les seuils définis (Performances)
- [ ] Les exports volumineux sont traités de manière asynchrone

---

*Fin des spécifications du Module 1 : Contexte et Organisation*
