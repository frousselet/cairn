# Framework

`compliance.models.framework.Framework`

Référentiel normatif, légal, réglementaire, contractuel ou interne auquel l'organisme doit ou choisit de se conformer.

## Entité : Framework (Référentiel)

Représente un référentiel normatif, légal, réglementaire, contractuel ou interne auquel l'organisme doit ou choisit de se conformer.

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-généré | Identifiant unique |
| `scope_id` | relation | FK → Scope, requis | Périmètre rattaché |
| `reference` | string | requis, unique | Code de référence (ex. REF-001) |
| `name` | string | requis, max 255 | Nom du référentiel (ex. « ISO 27001:2022 ») |
| `short_name` | string | optionnel, max 50 | Abréviation (ex. « ISO 27001 ») |
| `description` | text | optionnel | Description du référentiel |
| `type` | enum | requis | `standard`, `law`, `regulation`, `contract`, `internal_policy`, `industry_framework`, `other` |
| `category` | enum | requis | Voir liste ci-dessous |
| `version` | string | optionnel | Version du référentiel (ex. « 2022 ») |
| `publication_date` | date | optionnel | Date de publication officielle |
| `effective_date` | date | optionnel | Date d'entrée en vigueur |
| `expiry_date` | date | optionnel | Date d'expiration ou d'abrogation |
| `issuing_body` | string | optionnel | Organisme émetteur (ex. « ISO », « Parlement européen ») |
| `jurisdiction` | string | optionnel | Juridiction applicable (ex. « France », « Union européenne », « International ») |
| `url` | string | optionnel, format URL | Lien vers le texte officiel |
| `is_mandatory` | boolean | requis, défaut false | Référentiel obligatoire (contrainte légale/réglementaire) |
| `is_applicable` | boolean | requis, défaut true | Applicable au périmètre |
| `applicability_justification` | text | optionnel | Justification de l'applicabilité ou de la non-applicabilité |
| `owner_id` | relation | FK → User, requis | Responsable du suivi de conformité pour ce référentiel |
| `related_stakeholders` | relation | M2M → Stakeholder | Parties intéressées à l'origine de ce référentiel |
| `compliance_level` | decimal | calculé, 0-100 | Niveau de conformité global calculé (%) |
| `last_assessment_date` | date | calculé | Date de la dernière évaluation |
| `status` | enum | requis | `draft`, `active`, `under_review`, `deprecated`, `archived` |
| `review_date` | date | optionnel | Prochaine date de revue |
| `created_by` | relation | FK → User | Créateur |
| `created_at` | datetime | auto | Date de création |
| `updated_at` | datetime | auto | Date de dernière modification |

**Catégories de référentiels (valeurs de `category`) :**

- `information_security` (Sécurité de l'information : ISO 27001, ISO 27002, etc.)
- `privacy` (Protection des données : RGPD, CCPA, etc.)
- `risk_management` (Gestion des risques : ISO 27005, ISO 31000, etc.)
- `business_continuity` (Continuité d'activité : ISO 22301, etc.)
- `cloud_security` (Sécurité cloud : ISO 27017, ISO 27018, SecNumCloud, etc.)
- `sector_specific` (Réglementations sectorielles : NIS 2, DORA, HDS, PCI DSS, etc.)
- `it_governance` (Gouvernance IT : COBIT, ITIL, etc.)
- `quality` (Qualité : ISO 9001, etc.)
- `contractual` (Exigences contractuelles)
- `internal` (Politiques et procédures internes)
- `other`

> Note : Les catégories et les types doivent être paramétrables par l'administrateur.
