# FearedEvent

`risks.models.ebios.feared_event.FearedEvent`

Caractérise une atteinte DIC sur un bien essentiel avec gravité. Préfixe de référence : `EFER`.

## 4.1.2 Entité : FearedEvent (Événement redouté)

Caractérise une atteinte DIC sur un bien essentiel avec gravité.

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| `id` | UUID | PK, auto | Identifiant unique |
| `baseline_id` | relation | FK -> [SecurityBaseline](security-baseline.md), requis | Socle parent |
| `reference` | string | requis, unique, préfixe EFER | Code (ex. EFER-1) |
| `essential_asset_id` | relation | FK -> EssentialAsset, requis | Bien essentiel concerné |
| `name` | string | requis, max 255 | Intitulé court |
| `description` | text | requis | Description |
| `dic_criterion` | enum | requis | `confidentiality`, `integrity`, `availability` |
| `gravity_level` | integer | requis, calculé/saisi | Gravité (échelle impact RiskCriteria) |
| `gravity_justification` | text | optionnel | Justification de la gravité |
| `business_impacts` | json | optionnel | Impacts détaillés (clés : `financial`, `legal`, `reputation`, `operational`, `human`, `environmental`) |
| `criteria_snapshot` | json | calculé | Snapshot du barème au moment de la saisie |
| `order` | integer | requis | Ordre d'affichage |
| `created_by`, `created_at`, `updated_at` | - | auto | Standards |

> Règle : pour un même `essential_asset_id`, au plus 3 `FearedEvent` (un par critère DIC). Géré par contrainte d'unicité `(baseline_id, essential_asset_id, dic_criterion)`.
