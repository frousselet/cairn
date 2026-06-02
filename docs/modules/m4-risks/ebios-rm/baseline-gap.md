# BaselineGap

`risks.models.ebios.baseline_gap.BaselineGap`

Écart constaté entre l'état actuel de sécurité et le socle de sécurité attendu (référentiels, bonnes pratiques). Préfixe de référence : `EBGP`.

## 4.1.3 Entité : BaselineGap (Écart au socle)

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| `id` | UUID | PK, auto | Identifiant unique |
| `baseline_id` | relation | FK -> [SecurityBaseline](security-baseline.md), requis | Socle parent |
| `reference` | string | requis, unique, préfixe EBGP | Code (ex. EBGP-1) |
| `reference_source` | string | requis | Source du socle (ex. « ISO 27002:2022 A.5.1 », « Guide d'hygiène ANSSI #12 ») |
| `linked_requirement_id` | relation | FK -> Requirement, optionnel | Exigence de conformité liée |
| `description` | text | requis | Description de l'écart |
| `affected_support_assets` | M2M -> SupportAsset | optionnel | Biens supports concernés |
| `severity` | enum | requis | `low`, `medium`, `high`, `critical` |
| `recommended_remediation` | text | optionnel | Remédiation recommandée |
| `status` | enum | requis | `identified`, `accepted`, `in_remediation`, `remediated` |
| `linked_pacs_measures` | M2M -> [PACSMeasure](pacs-measure.md) | optionnel | Mesures PACS traitant l'écart |
| `order` | integer | requis | Ordre d'affichage |
| `created_by`, `created_at`, `updated_at` | - | auto | Standards |
