# ComplianceActionPlan

`compliance.models.action_plan.ComplianceActionPlan`

Plan d'action visant à corriger un écart de conformité constaté lors d'une [évaluation](compliance-assessment.md), à mitiger un [risque](../m4-risks/risk.md), ou à traiter le constat issu d'une revue de direction. Pilote son cycle de vie via un workflow Kanban à 7 états et conserve l'historique complet des transitions.

## Champs

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-généré | Identifiant unique |
| `reference` | string | auto-généré `CAPL-N`, unique | Référence métier |
| `scopes` | relation | M2M -> Scope | Périmètres SMSI concernés |
| `name` | string | requis, max 255 | Intitulé du plan d'action |
| `description` | text | optionnel, HTML | Description détaillée |
| `gap_description` | text | requis, HTML | Description de l'écart à combler |
| `remediation_plan` | text | requis, HTML | Plan de remédiation |
| `priority` | enum | requis | `low`, `medium`, `high`, `critical` |
| `owner` | relation | FK -> User, requis, PROTECT | Superviseur (responsable du suivi) |
| `assignees` | relation | M2M -> User | Affectés (réalisateurs du plan) |
| `requirements` | relation | M2M -> Requirement | Exigences que le plan adresse |
| `findings` | relation | M2M -> Finding | Constats d'audit que le plan adresse |
| `risks` | relation | M2M -> Risk | Risques que le plan mitige |
| `originating_review` | relation | FK -> ManagementReview, optionnel | Revue de direction qui a généré ce plan |
| `start_date` | date | optionnel | Date de début prévue |
| `target_date` | date | requis | Date cible d'achèvement |
| `completion_date` | date | optionnel | Date d'achèvement effective. Renseignée automatiquement à la transition vers `closed`. |
| `progress_percentage` | integer | défaut 0, 0-100 | Pourcentage d'avancement. Forcé à 100 à la transition vers `closed`. |
| `cost_estimate` | decimal(12,2) | optionnel | Estimation du coût |
| `status` | enum | requis, défaut `new` | Voir « Workflow » ci-dessous. **Lecture seule via REST/MCP standard** : utiliser l'outil `action_plan_transition` pour changer de statut. |
| `is_overdue` | boolean | calculé, lecture seule | `true` si `target_date` est dépassée et `status` n'est ni `closed` ni `cancelled`. Calculé à la lecture, pas stocké. |
| `tags` | relation | M2M -> Tag | |
| `is_approved` / `approved_by` / `approved_at` | bool / FK -> User / datetime | optionnel | Approbation hors workflow |
| `version` | int | auto-incrémenté | |
| `created_by` | relation | FK -> User | |
| `created_at` / `updated_at` | datetime | auto | |

## Workflow

Le plan d'action suit un workflow Kanban à 7 états plus `cancelled`. Chaque transition est validée par `ComplianceActionPlan.transition_to(new_status, user, comment)` ; les transitions arrière (« refus ») exigent un commentaire obligatoire et sont enregistrées comme `is_refusal=True` dans l'historique.

```text
new -> to_define -> to_validate -> to_implement -> implementation_to_validate -> validated -> closed
                  <-              <-              <-                            <-
                                              (refus avec commentaire obligatoire)

(toutes les étapes <= implementation_to_validate) -> cancelled  (terminal)
```

| Statut | Sens |
|---|---|
| `new` | Brouillon créé, en attente de définition |
| `to_define` | Définition en cours (préciser le plan de remédiation, le périmètre, les ressources) |
| `to_validate` | Définition soumise, en attente de validation par le superviseur |
| `to_implement` | Définition validée, en attente d'implémentation par les affectés |
| `implementation_to_validate` | Implémentation soumise, en attente de validation finale |
| `validated` | Implémentation validée, prêt à clore |
| `closed` | Plan terminé (terminal). `completion_date` et `progress_percentage=100` sont auto-renseignés à l'entrée. |
| `cancelled` | Plan annulé (terminal). Accessible depuis tout statut sauf `validated`, `closed` et `cancelled`. |

### Transitions et permissions

- **Avancement** : chaque transition forward exige la permission `compliance.action_plan.update` au minimum, et certaines étapes de validation peuvent exiger `compliance.action_plan.approve` (configurable).
- **Refus** : transition arrière depuis `to_validate -> to_define`, `implementation_to_validate -> to_implement`, etc. Le `comment` est requis pour tracer la raison du refus. La transition est enregistrée en `ActionPlanTransition.is_refusal=True`.
- **Annulation** : `cancelled` est atteignable depuis `new`, `to_define`, `to_validate`, `to_implement`, `implementation_to_validate` (cf. `ACTION_PLAN_CANCELLABLE_STATUSES`). Une fois `validated` ou `closed`, l'annulation n'est plus possible.
- **Historique** : chaque transition crée un `ActionPlanTransition` (`from_status`, `to_status`, `performed_by`, `comment`, `is_refusal`, `created_at`). Le détail est accessible via `assessment.transitions.all().order_by('created_at')`.

L'API expose `GET /api/v1/compliance/action-plans/<uuid>/allowed-transitions/` (et le MCP `action_plan_allowed_transitions`) qui retourne la liste des transitions possibles depuis le statut courant pour l'utilisateur courant, en tenant compte de ses permissions. C'est l'API à appeler avant de proposer une action UI ou un outil MCP de transition.

## Règles de gestion

| ID | Règle |
|---|---|
| RG-CAP-01 | Le `status` n'est pas modifiable directement via `update_compliance_action_plan` : passer par `action_plan_transition` qui applique les règles de workflow, le contrôle de permission, et écrit l'historique. |
| RG-CAP-02 | Une transition arrière (refus) exige un `comment` non vide. La requête est rejetée avec un 400 explicite si le commentaire manque. |
| RG-CAP-03 | À la transition vers `closed`, `completion_date` est forcée à la date du jour et `progress_percentage` est forcé à 100. La complétion RP-02 est donc attachée au statut terminal `closed`. |
| RG-CAP-04 | `is_overdue` est une propriété calculée, vraie ssi `target_date < today` et `status not in (closed, cancelled)`. Sert aux indicateurs et aux filtres « plans en retard ». Pas de migration automatique du statut : le plan reste dans son état Kanban tant qu'un opérateur ne l'a pas avancé ou clos. |

## Écarts par rapport à la spec d'origine

La spec M3 §2.7 listait un workflow à 5 statuts (`planned`, `in_progress`, `completed`, `cancelled`, `overdue`). L'implémentation a évolué vers un workflow Kanban à 7 états :

| Spec d'origine | Implémentation actuelle |
|---|---|
| `planned` | `new` puis `to_define`, `to_validate`, `to_implement` (la définition est un processus, pas un statut) |
| `in_progress` | `implementation_to_validate` (l'implémentation est en cours de revue) |
| `completed` | `validated` (implémentation acceptée) puis `closed` (terminal). RP-02 (auto-100% + date) attachée au passage à `closed`. |
| `cancelled` | `cancelled` (identique) |
| `overdue` | **Propriété calculée `is_overdue`**, pas un statut. RP-01 (passage automatique en overdue) n'est pas appliquée comme transition de workflow ; à la place, `is_overdue` se calcule à chaque lecture. Évite la friction d'un statut qui se met à jour seul à minuit chaque jour, sans rien perdre côté détection. |

Le workflow plus riche reflète la pratique réelle : le passage de la « définition » à « l'implémentation validée » d'un plan d'action n'est pas un saut binaire mais une chaîne de validations (auditeur -> superviseur -> affecté -> superviseur), et les rejets sont fréquents (« non, cette définition n'est pas assez précise »). Le statut Kanban en 7 étapes capte cette chaîne sans surcharger le code applicatif d'un état parallèle « en attente de quoi ». La spec originale est entérinée comme étant trop simple pour l'usage réel, et l'écart est conservé en l'état avec cette correspondance documentée.

## Endpoints

### REST

- `GET /api/v1/compliance/action-plans/` : liste avec filtres `status`, `priority`, `owner_id`, `requirement_id`, `assignee_id`
- `POST /api/v1/compliance/action-plans/`
- `GET /api/v1/compliance/action-plans/<uuid>/`
- `PATCH /api/v1/compliance/action-plans/<uuid>/` : modification des champs métier (sauf `status`)
- `DELETE /api/v1/compliance/action-plans/<uuid>/`
- `POST /api/v1/compliance/action-plans/<uuid>/approve/`
- `GET /api/v1/compliance/action-plans/<uuid>/allowed-transitions/` : transitions possibles pour l'utilisateur
- `POST /api/v1/compliance/action-plans/<uuid>/transition/` : applique une transition (`{"status": "...", "comment": "..."}`)
- `GET /api/v1/compliance/action-plans/<uuid>/transitions/` : historique

### MCP

- `list_action_plans` / `get_action_plan` / `create_action_plan` / `update_action_plan` (sans `status`) / `delete_action_plan` / `approve_action_plan` / `batch_create_action_plans`
- `action_plan_allowed_transitions(id)` : liste les transitions disponibles
- `action_plan_transition(id, status, comment=...)` : applique une transition
- `action_plan_transitions(id)` : historique chronologique

## Permissions

| Codename | Description |
|---|---|
| `compliance.action_plan.read` | Lire les plans d'action |
| `compliance.action_plan.create` | Créer |
| `compliance.action_plan.update` | Modifier les champs métier + appliquer les transitions forward standard |
| `compliance.action_plan.approve` | Appliquer les transitions de validation (`to_validate -> to_implement`, `implementation_to_validate -> validated`) |
| `compliance.action_plan.delete` | Supprimer |

## Références

- ISO/IEC 27001:2022 §10.1 (Amélioration continue) et §10.2 (Non-conformité et actions correctives)
- [ComplianceAssessment](compliance-assessment.md) : source typique des plans d'action via les `Finding`
- [Risk](../m4-risks/risk.md) et [RiskTreatmentPlan](../m4-risks/risk-treatment-plan.md) : un plan d'action conformité peut être lié à un plan de traitement de risque via `RiskTreatmentPlan.related_action_plans`
- [ManagementReview](../management-review/management-review.md) : un plan d'action peut être généré à partir d'une décision de revue de direction (`originating_review`)
