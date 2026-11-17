# Glossary

One thing, one name, everywhere : the menu, the buttons, the helpers, the
generated documents and this documentation use the same word for the same
thing. This page is the reference for the French interface, with the English
term each word translates.

> **Status : proposal.** The interface does not follow this page yet. It was
> drawn from a count of how each notion is written today in the French
> catalogue (`locale/fr/LC_MESSAGES/django.po`, about 5 600 entries). The rows marked
> **to decide** oppose the word of the standards to the everyday word : that
> choice belongs to the product owner. Once it is made, the catalogue is
> aligned in one pass and a test holds it (rule W1 of the
> [usability standard](../sdk/usability-standard.md)).

## The principle proposed

**The word of the standard, explained where it is first met.** Cairn's records
are shown to auditors, and its users read ISO 27001, ISO 27005 and the ANSSI
guides beside it : when the tool, the standard and the auditor use the same
word, a newcomer learns it once. What stops a newcomer is not one unfamiliar
word that is explained, it is five words for one thing and an acronym nobody
spells out.

So : the standard's word when the standard has one, with its plain-language
sentence where it first appears (the introduction of a form section, the empty
state of a register, the first steps of the dashboard). The everyday word is
kept in this glossary as "also called", so the search finds it.

The alternative principle is **the everyday word first** ("analyse de risques",
"partie prenante", "actif"), the standard's word being given in the glossary
only. It reads more easily on the first day and less faithfully in front of an
auditor. The rows marked *to decide* are where the two principles differ.

## Things

| Notion (English) | Written today (occurrences) | Proposed | Also called | Decision |
| --- | --- | --- | --- | --- |
| Scope | périmètre (87) | **Périmètre** | domaine d'application (ISO 27001 §4.3) | settled |
| Essential asset | bien essentiel (27) | **Bien essentiel** | valeur métier (EBIOS RM), actif primordial (ISO 27005) | **to decide** |
| Support asset | bien support (29), actif support (1) | **Bien support** | actif support (ISO 27005) | follows the row above |
| Asset, alone | bien (88), actif (30 : "Groupes d'actifs", "Dépendances d'actifs", menu "Actifs et tiers") | **Bien** | actif | follows the row above |
| Supplier | fournisseur (100), tiers (10), prestataire (2) | **Fournisseur** ; menu section "Biens et fournisseurs" | tiers, prestataire | settled |
| Security needs of an asset | DIC (6), CIA (3) ; "Évaluation CIA", "Évaluation DIC" | **Besoins de sécurité** : disponibilité, intégrité, confidentialité (DIC) | CIA is the English acronym, never used in French | settled |
| Compliance assessment | évaluation (63), audit (7) | **Évaluation de conformité**, *évaluation* for short ; *audit* names a kind of evaluation and its findings | audit | settled |
| Risk assessment | appréciation des risques (15), évaluation des risques (4), analyse des risques (1) | **Appréciation des risques** (ISO 27005, ANSSI) | analyse de risques (everyday) | **to decide** |
| Control | mesure (79), contrôle (10, other meanings) | **Mesure** (de sécurité) | contrôle (anglicism) | settled |
| Requirement | exigence (106) | **Exigence** | | settled |
| Framework | référentiel (82) | **Référentiel** ; *cadre* stays the EBIOS RM study framework | norme, règlement | settled |
| Finding | constat (39), non-conformité (3), écart (2) | **Constat** ; a *non-conformité* is a kind of finding | écart | settled |
| Action plan (compliance) | plan d'action (38) | **Plan d'action** | | settled |
| Treatment plan (risks) | plan de traitement (19) | **Plan de traitement** : a different object, never swapped with the row above | | settled |
| Stakeholder | partie prenante (28), partie intéressée (10) | **Partie intéressée** (ISO 27001 §4.2) | partie prenante (everyday) | **to decide** |
| Issue | enjeu (25) | **Enjeu** (ISO 27001 §4.1) | | settled |
| Owner | propriétaire (9), responsable (2) | **Propriétaire** : who answers for a record and decides | responsable | settled |
| Manager | responsable (6) | **Responsable** : who runs it (a scope, an action) | | settled |
| Custodian | dépositaire (1) | **Gestionnaire** : who looks after an asset day to day | dépositaire | **to decide** |
| Position of a record in its lifecycle | état (43), statut (27), étape (3) | **Étape** (du cycle de vie) ; *statut* for a characteristic that is not the lifecycle (statut de conformité) | état | settled |
| Lifecycle | cycle de vie (76), workflow (2) | **Cycle de vie** | workflow | settled |
| Review | revue (163) | **Revue** | réexamen | settled |
| Evidence | preuve (84), élément de preuve (9), justificatif (2) | **Preuve** | élément de preuve | settled |
| Likelihood | vraisemblance (24) | **Vraisemblance** (ISO 27005) | probabilité (everyday) | **to decide** |
| Tag | étiquette (8), tag (5) | **Étiquette** | tag | settled |

## Acronyms

An acronym never stands alone as a label (rule W2). The words come first, the
acronym follows in brackets where it is first shown on a screen; it may be used
alone after that, on the same screen.

| Acronym | Spelled out | Where |
| --- | --- | --- |
| SMSI | système de management de la sécurité de l'information (SMSI) | 25 strings, never spelled out today |
| DIC | disponibilité, intégrité, confidentialité (DIC) | assets |
| DMT | durée maximale d'interruption tolérable (DMT) | essential asset (done) |
| RTO | délai de reprise visé (RTO) | essential asset (done) |
| RPO | perte de données maximale admissible (RPO) | essential asset (done) |
| SPOF | point de défaillance unique (SPOF) | dependencies |
| TLP | niveau de diffusion (TLP, Traffic Light Protocol) | incidents |
| EBIOS RM | méthode EBIOS Risk Manager (EBIOS RM) | risks |
| SR, OV | source de risque (SR), objectif visé (OV) | EBIOS RM workshop 2 |
| PACS | plan d'amélioration continue de la sécurité (PACS) | EBIOS RM workshop 5 |
| RACI | responsable, approbateur, consulté, informé (RACI) | roles |
| RGPD | règlement général sur la protection des données (RGPD) | assets, incidents |

The continuity acronyms keep the English letters French IT teams use (RTO,
RPO). The French ones (DMIA, PDMA) are the alternative : **to decide**.

## Verbs

One verb per act. Today the creation of a record is written four ways :
*Nouveau / Nouvelle / Nouvel …* (65), *Ajouter …* (40), *Créer …* (16),
*Déclarer …* (3).

| Act | Proposed | Example |
| --- | --- | --- |
| Open the dialog that creates a record (list button, and the title of that dialog) | **Nouveau / Nouvelle …** : the same words where one clicks and where one lands | Nouveau périmètre |
| Confirm a creation | **Créer** | (done, in every dialog) |
| Confirm an edit | **Enregistrer** | (done) |
| Attach something that exists, or add a line inside a record | **Ajouter …** | Ajouter un site |
| Change a record | **Modifier** | |
| Leave without saving | **Annuler** | |
| Move between the steps of a form | **Précédent**, **Suivant** | (done) |
| Record an incident | **Déclarer un incident** : the verb of the trade, kept | |
| Remove for good | **Supprimer** ; **Archiver** when the record is kept | |

The brand guidelines currently give *Create a requirement* as the model of a
button, against the 65 *Nouveau …* of the interface : adopting this table
settles it, and the example of the guidelines follows.

## What adopting it changes

- About 150 French strings are rewritten (the minority spellings of the table),
  none of them in a stored value : it is a change of catalogue, not of data.
- The menu section "Actifs et tiers" becomes "Biens et fournisseurs".
- Each acronym of the table gains its words where it is a label.
- A test reads the catalogue and refuses the spellings this page retires, so
  the vocabulary cannot drift again.
- This glossary is shown in the application, where the search reaches it.
