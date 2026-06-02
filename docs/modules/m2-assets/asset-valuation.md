# AssetValuation

`assets.models.valuation.AssetValuation`

Historique des évaluations DIC d'un bien essentiel, permettant de suivre l'évolution des besoins de sécurité dans le temps.

Conserve l'historique des évaluations DIC d'un bien essentiel, permettant de suivre l'évolution des besoins de sécurité dans le temps.

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-généré | Identifiant unique |
| `essential_asset_id` | relation | FK → EssentialAsset, requis | Bien essentiel évalué |
| `evaluation_date` | date | requis | Date de l'évaluation |
| `confidentiality_level` | enum | requis | Niveau C à cette date |
| `integrity_level` | enum | requis | Niveau I à cette date |
| `availability_level` | enum | requis | Niveau D à cette date |
| `evaluated_by` | relation | FK → User, requis | Évaluateur |
| `justification` | text | optionnel | Justification globale de l'évaluation |
| `context` | text | optionnel | Contexte de l'évaluation (revue annuelle, incident, changement…) |
| `created_at` | datetime | auto | Date de création |
