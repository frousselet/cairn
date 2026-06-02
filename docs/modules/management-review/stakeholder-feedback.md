# StakeholderFeedback

`context.models.stakeholder_feedback.StakeholderFeedback`

Formalised stakeholder feedback channel required by ISO 27001:2022 clause 9.3.2.e, distinct from permanent `StakeholderExpectation` records.

Formalisation du canal de feedback exigé par la clause 9.3.2.e (distinct des attentes `StakeholderExpectation`, qui sont des exigences permanentes).

Fichier : `context/models/stakeholder_feedback.py`

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| `id` | UUID | PK | |
| `reference` | string | auto (préfixe `FBCK`), unique | ex. `FBCK-1` |
| `stakeholder` | FK → Stakeholder | requis, CASCADE | Partie intéressée émettrice |
| `channel` | enum | requis | `survey`, `meeting`, `complaint`, `email`, `audit`, `incident`, `other` |
| `received_date` | date | requis | Date de réception |
| `subject` | string | requis, max 255 | Objet du retour |
| `content` | text | requis | Contenu détaillé (HTML rich text) |
| `sentiment` | enum | optionnel | `positive`, `neutral`, `negative`, `mixed` |
| `severity` | enum | optionnel | `low`, `medium`, `high`, `critical` |
| `status` | enum | requis | `new`, `under_review`, `addressed`, `closed` |
| `response` | text | optionnel | Réponse apportée |
| `linked_issues` | M2M → Issue | optionnel | Enjeux associés |
| `linked_expectations` | M2M → StakeholderExpectation | optionnel | Attentes renforcées |
| `scopes` | M2M → Scope | requis, au moins 1 | Périmètres concernés |
| `created_by`, `created_at`, `updated_at` | auto | | Traçabilité |

**Historique** : `HistoricalRecords`.

**Agrégation en revue** : la section 5 de l'export devient :
- tableau des `StakeholderFeedback` sur la période (priorité aux `negative` + `critical`)
- plus la vue actuelle des attentes applicables (inchangée).
