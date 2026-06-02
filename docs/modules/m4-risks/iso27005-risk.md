# ISO27005Risk

`risks.models.iso27005_risk.ISO27005Risk`

Analyse détaillée d'un scénario de risque selon la méthodologie ISO 27005 : triplet (menace, vulnérabilité, actif) avec évaluation de la vraisemblance et de l'impact.

## 3.3 Entité : ISO27005Risk (Analyse de risque ISO 27005)

Représente l'analyse détaillée d'un scénario de risque selon la méthodologie ISO 27005 : un triplet (menace, vulnérabilité, actif) avec évaluation de la vraisemblance et de l'impact.

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-généré | Identifiant unique |
| `assessment_id` | relation | FK → RiskAssessment, requis | Appréciation parente (methodology = iso27005) |
| `threat_id` | relation | FK → Threat, requis | Menace exploitante |
| `vulnerability_id` | relation | FK → Vulnerability, requis | Vulnérabilité exploitée |
| `affected_essential_assets` | relation | M2M → EssentialAsset | Biens essentiels impactés |
| `affected_support_assets` | relation | M2M → SupportAsset | Biens supports ciblés |
| `threat_likelihood` | integer | requis | Vraisemblance de la menace (sur l'échelle) |
| `vulnerability_exposure` | integer | requis | Niveau d'exposition de la vulnérabilité (sur l'échelle) |
| `combined_likelihood` | integer | calculé | Vraisemblance combinée |
| `impact_confidentiality` | integer | optionnel | Impact sur la confidentialité (sur l'échelle) |
| `impact_integrity` | integer | optionnel | Impact sur l'intégrité |
| `impact_availability` | integer | optionnel | Impact sur la disponibilité |
| `max_impact` | integer | calculé | Impact maximum retenu |
| `risk_level` | integer | calculé | Niveau de risque (via matrice) |
| `existing_controls` | text | optionnel | Mesures existantes prises en compte |
| `existing_measures` | relation | M2M → Measure | Mesures existantes formalisées |
| `risk_id` | relation | FK → [Risk](risk.md), optionnel | Risque consolidé dans le registre |
| `description` | text | optionnel | Description narrative du scénario |
| `created_by` | relation | FK → User | Créateur |
| `created_at` | datetime | auto | Date de création |
| `updated_at` | datetime | auto | Date de dernière modification |

> Note : Le sous-module ISO 27005 comprend également les entités `Threat` (`risks.models.threat.Threat`) et `Vulnerability` (`risks.models.vulnerability.Vulnerability`), respectivement référentielles pour les menaces et les vulnérabilités utilisées dans les triplets.
