# ManagementReview

`reports.models.management_review.ManagementReview`

Persistent management review (ISO 27001:2022 clause 9.3) covering its full lifecycle from planning through closure.

Représente une revue de direction planifiée ou tenue. Objet racine persistant qui remplace le fonctionnement "export éphémère" actuel.

Fichier : `reports/models/management_review.py`

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-généré | Identifiant unique |
| `reference` | string | auto (préfixe `MRVW`), unique | Référence séquentielle (ex. `MRVW-1`) |
| `title` | string | requis, max 255 | Intitulé (ex. « Revue de direction annuelle 2026 ») |
| `description` | text | optionnel | Contexte, objet de la revue |
| `scopes` | relation | M2M → Scope, au moins 1 | Périmètres couverts par la revue |
| `frequency` | enum | requis | `quarterly`, `semiannual`, `annual`, `exceptional` |
| `period_start` | date | requis | Début de la période examinée |
| `period_end` | date | requis | Fin de la période examinée |
| `planned_date` | date | requis | Date planifiée de la revue |
| `held_date` | date | optionnel | Date effective de tenue |
| `location` | string | optionnel, max 255 | Lieu (physique ou visio) |
| `status` | enum | requis | `planned`, `in_preparation`, `held`, `closed`, `cancelled` |
| `facilitator` | FK → User | requis | Animateur / rédacteur |
| `approver` | FK → User | optionnel | Approbateur (typiquement direction) |
| `approved_at` | datetime | optionnel | Date d'approbation |
| `next_review_date` | date | optionnel | Date prévue de la prochaine revue |
| `summary` | text | optionnel | Synthèse exécutive rédigée par l'animateur |
| `agenda` | text | optionnel | Ordre du jour (HTML rich text) |
| `minutes` | text | optionnel | Compte rendu détaillé (HTML rich text) |
| `snapshot_data` | JSONField | optionnel | Snapshot des données agrégées au moment de la clôture (pour geler l'auditabilité) |
| `created_by` | FK → User | auto | Créateur |
| `created_at`, `updated_at` | datetime | auto | Traçabilité |
| `tags` | M2M → Tag | optionnel | Étiquetage libre |

**Historique** : `django-simple-history` (`HistoricalRecords`) pour audit-trail.

**Cycle de vie (workflow)** :

```
planned ─► in_preparation ─► held ─► closed
       └──────────────────────────► cancelled
```

Transitions :

- `planned → in_preparation` : l'animateur verrouille l'ordre du jour et déclenche la collecte des données.
- `in_preparation → held` : sur saisie de `held_date`. Les données entrées de clause 9.3.2 sont gelées dans `snapshot_data`.
- `held → closed` : toutes les décisions doivent avoir un responsable et une échéance ; le statut bascule si `approver` valide. Capture `approved_at`.
- `* → cancelled` : motif obligatoire, stocké via commentaire (cf. [comment.md](comment.md)).

L'UI doit utiliser le **stepper horizontal** décrit dans `CLAUDE.md` (cf. `compliance/templates/compliance/assessment_detail.html`).

## Extensions to Indicator / IndicatorMeasurement

**Aucun changement de modèle**. `IndicatorMeasurement` existe déjà (`context/models/indicator.py:352`). La spec impose uniquement d'exploiter ces mesures côté export :

- Calcul de la tendance sur la période de revue : comparaison de la **moyenne des mesures** `period_start → period_end` vs. la période précédente équivalente.
- Marqueur `trend` calculé : `improving`, `stable`, `degrading`, `insufficient_data` (< 2 mesures).
- Calcul du **respect de la fréquence** : nombre attendu de mesures sur la période (selon `review_frequency`) vs. nombre réel. Remonté en `measurement_compliance_pct`.
