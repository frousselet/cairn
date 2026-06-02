# SecurityBaseline

`risks.models.ebios.security_baseline.SecurityBaseline`

Racine de l'atelier 1 EBIOS RM. Une seule par appréciation. Préfixe de référence : `EBSL`.

## 4.1.1 Entité : SecurityBaseline (Socle de sécurité)

Racine de l'atelier 1. Une seule par appréciation.

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| `id` | UUID | PK, auto | Identifiant unique |
| `assessment_id` | relation | FK -> [RiskAssessment](../risk-assessment.md), requis, unique | Appréciation parente |
| `reference` | string | requis, unique, préfixe EBSL | Code (ex. EBSL-1) |
| `business_values` | M2M -> Activity | requis | Valeurs métier retenues |
| `essential_assets` | M2M -> EssentialAsset | requis | Biens essentiels retenus |
| `support_assets` | M2M -> SupportAsset | requis | Biens supports retenus |
| `dic_summary` | text | optionnel | Synthèse des besoins de sécurité DIC |
| `baseline_references` | M2M -> Framework | optionnel | Référentiels du socle (ISO 27002, ANSSI, NIST, etc.) |
| `status` | enum | requis | `draft`, `in_progress`, `completed` |
| `created_by`, `created_at`, `updated_at` | - | auto | Standards |
