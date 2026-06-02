# Attachment

`compliance.models.assessment.AssessmentResultAttachment`

Pièce jointe documentaire associée à un résultat d'[évaluation de conformité](compliance-assessment.md) ou à un [plan d'action](compliance-action-plan.md).

## Sous-entité : Attachment (Pièce jointe)

Utilisée pour stocker les preuves documentaires associées aux évaluations de conformité.

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-généré | Identifiant unique |
| `entity_type` | string | requis | Type d'entité parente (ex. `AssessmentResult`, `ComplianceActionPlan`) |
| `entity_id` | UUID | requis | Identifiant de l'entité parente |
| `file_name` | string | requis, max 255 | Nom du fichier |
| `file_path` | string | requis | Chemin de stockage |
| `file_size` | integer | requis | Taille en octets |
| `mime_type` | string | requis | Type MIME |
| `description` | text | optionnel | Description de la pièce jointe |
| `uploaded_by` | relation | FK → User, requis | Utilisateur ayant téléversé |
| `created_at` | datetime | auto | Date de création |
