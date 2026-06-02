# TargetedObjective

`risks.models.ebios.targeted_objective.TargetedObjective`

Objectif visé (OV) : finalité poursuivie par une source de risque. Préfixe de référence : `ETOV`.

## 4.2.2 Entité : TargetedObjective (Objectif visé)

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| `id` | UUID | PK, auto | Identifiant unique |
| `risk_source_id` | relation | FK -> [RiskSource](risk-source.md), requis | SR parente |
| `reference` | string | requis, unique, préfixe ETOV | Code (ex. ETOV-1) |
| `name` | string | requis, max 255 | Intitulé |
| `description` | text | optionnel | Description |
| `category` | enum | requis | `lucrative`, `strategic`, `terrorist`, `ideological`, `revenge`, `ludic`, `other` |
| `targeted_essential_assets` | M2M -> EssentialAsset | optionnel | Biens essentiels ciblés |
| `targeted_feared_events` | M2M -> [FearedEvent](feared-event.md) | optionnel | Événements redoutés associés |
| `is_retained` | boolean | requis, défaut true | OV retenu |
| `order` | integer | requis | Ordre |
| `created_by`, `created_at`, `updated_at` | - | auto | Standards |
