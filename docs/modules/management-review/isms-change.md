# IsmsChange

`reports.models.management_review.IsmsChange`

Formalised ISMS change decided during a management review (ISO 27001:2022 clause 9.3.3 requirement on "any need for changes to the ISMS").

Exigence 9.3.3 : « toute nécessité de modifier le SMSI ». Formalisation des changements décidés en revue.

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| `id` | UUID | PK | |
| `reference` | string | auto (préfixe `ICHG`), unique | ex. `ICHG-1` |
| `review` | FK → ManagementReview | requis, CASCADE | Revue d'origine |
| `change_type` | enum | requis | `scope`, `policy`, `control`, `organization`, `resource`, `process`, `other` |
| `title` | string | requis, max 255 | Intitulé |
| `description` | text | requis | Description du changement |
| `impact_analysis` | text | optionnel | Analyse d'impact (PI, risques, actifs) |
| `affected_scopes` | M2M → Scope | optionnel | Périmètres impactés |
| `affected_frameworks` | M2M → Framework | optionnel | Référentiels impactés |
| `affected_policies` | text | optionnel | Liste des politiques à réviser (texte libre, évolution future vers un modèle `Policy`) |
| `status` | enum | requis | `proposed`, `approved`, `in_progress`, `implemented`, `rejected` |
| `owner` | FK → User | requis | Responsable de mise en œuvre |
| `target_date` | date | optionnel | Date cible |
| `implemented_at` | date | optionnel | Date de mise en œuvre effective |
| `created_at`, `updated_at` | datetime | auto | |

**Historique** : `HistoricalRecords`.
