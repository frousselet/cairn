# Section

`compliance.models.section.Section`

Structure hiérarchique d'un [Framework](framework.md) (chapitres, sections, sous-sections).

## Entité : Section (Section / Chapitre du référentiel)

Représente la structure hiérarchique d'un référentiel (chapitres, sections, sous-sections). Permet de reproduire fidèlement le plan du référentiel original.

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-généré | Identifiant unique |
| `framework_id` | relation | FK → Framework, requis | Référentiel parent |
| `parent_section_id` | relation | FK → Section, optionnel | Section parente (hiérarchie) |
| `reference` | string | requis | Numéro de section (ex. « A.5 », « 4.2.1 ») |
| `name` | string | requis, max 255 | Intitulé de la section |
| `description` | text | optionnel | Description ou texte de la section |
| `order` | integer | requis | Ordre d'affichage au sein du parent |
| `compliance_level` | decimal | calculé, 0-100 | Niveau de conformité agrégé de la section (%) |
| `created_at` | datetime | auto | Date de création |
| `updated_at` | datetime | auto | Date de dernière modification |

> Contrainte : la combinaison (`framework_id`, `reference`) doit être unique.
