# Issue

`context.models.issue.Issue`

Représente un enjeu interne ou externe pouvant influencer la capacité de l'organisme à atteindre les résultats attendus de son dispositif GRC.

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-généré | Identifiant unique |
| `scope_id` | relation | FK → Scope, requis | Périmètre rattaché |
| `name` | string | requis, max 255 | Intitulé de l'enjeu |
| `description` | text | optionnel | Description détaillée |
| `type` | enum | requis | `internal`, `external` |
| `category` | enum | requis | Voir liste ci-dessous |
| `impact_level` | enum | requis | `low`, `medium`, `high`, `critical` |
| `trend` | enum | optionnel | `improving`, `stable`, `degrading` |
| `source` | string | optionnel | Source de l'identification de l'enjeu |
| `related_stakeholders` | relation | M2M → Stakeholder | Parties intéressées liées |
| `review_date` | date | optionnel | Prochaine date de revue |
| `status` | enum | requis | `identified`, `active`, `monitored`, `closed` |
| `created_by` | relation | FK → User | Créateur |
| `created_at` | datetime | auto | Date de création |
| `updated_at` | datetime | auto | Date de dernière modification |

**Catégories d'enjeux (valeurs de `category`) :**

- *Enjeux internes :* `strategic`, `organizational`, `human_resources`, `technical`, `financial`, `cultural`
- *Enjeux externes :* `political`, `economic`, `social`, `technological`, `legal`, `environmental`, `competitive`, `regulatory`

> Note : Les catégories doivent être paramétrables par l'administrateur (ajout/modification/suppression).
