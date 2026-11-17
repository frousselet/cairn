# Glossary

One thing, one name, everywhere : the menu, the buttons, the helpers, the help
of each page, the generated documents and this documentation use the same word
for the same thing. This page is the reference for the French interface, with
the English term each word translates.

> **Status : adopted.** The interface follows this page. The application shows
> the same vocabulary to its users on the *Glossary* page
> ([`core/glossary.py`](../../core/glossary.py)), and
> [`core/tests/test_glossary.py`](../../core/tests/test_glossary.py) reads the
> French catalogue and refuses the spellings this page retires (rule W1 of the
> [usability standard](../sdk/usability-standard.md)).

## The principle

**The word of the standard, explained where it is first met.** Cairn's records
are shown to auditors, and its users read ISO 27001, ISO 27005 and the ANSSI
guides beside it : when the tool, the standard and the auditor use the same
word, a newcomer learns it once. What stops a newcomer is not one unfamiliar
word that is explained, it is five words for one thing and an acronym nobody
spells out.

So : the standard's word when the standard has one, with its plain-language
sentence where it is met (the help of the page, the introduction of a form
section, the empty state of a register, the first steps of the dashboard). The
everyday word is kept in the glossary as *also called*, so that the search
finds it : someone who types *actif*, *audit* or *partie prenante* is shown the
name the application uses.

The other principle, the everyday word first (*analyse de risques*, *partie
prenante*, *actif*), reads more easily on the first day and less faithfully in
front of an auditor. It was not retained.

## Things

| Notion (English) | French | Also called (not used in the interface) | Note |
| --- | --- | --- | --- |
| Scope | **Périmètre** | domaine d'application, champ d'application | ISO 27001 chapitre 4.3 |
| Essential asset | **Bien essentiel** | valeur métier (EBIOS RM), actif primordial (ISO 27005), actif essentiel | |
| Support asset | **Bien support** | actif support (ISO 27005) | |
| Asset, alone | **Bien** | actif | *Actif* remains the adjective of a record that is active |
| Supplier | **Fournisseur** | tiers, prestataire, sous-traitant | The menu section is *Biens et fournisseurs*. *Tiers* stays for a third party that is not a supplier record ("notification par un tiers") |
| Security needs of an asset | **Besoins de sécurité** : disponibilité, intégrité, confidentialité (DIC) | CIA, valorisation, classification | *CIA* is the English acronym, never used in French |
| Compliance assessment | **Évaluation de conformité**, *évaluation* for short | audit, contrôle de conformité | *Audit* names a kind of evaluation and its findings. The register that lists them is *Audits et conformité* |
| Risk assessment | **Appréciation des risques**, *appréciation* for short | analyse de risques, évaluation des risques, étude de risques | ISO 27005, ANSSI. The risk module never says *évaluation* for it |
| Control | **Mesure** (de sécurité) | contrôle | *Contrôle* keeps its other meanings : contrôle d'accès, zone de contrôle, autorité de contrôle |
| Requirement | **Exigence** | clause, obligation | |
| Framework | **Référentiel** | norme, règlement | *Cadre* stays the EBIOS RM study framework |
| Part of a standard | **Chapitre** (ISO 27001, chapitre 4.3) | clause, § | *Article* is kept for a law (RGPD, art. 33) |
| Finding | **Constat** | observation, écart | A *non-conformité* is a kind of finding, and has its register |
| Action plan (compliance) | **Plan d'action** | action corrective | |
| Treatment plan (risks) | **Plan de traitement** | plan de remédiation | A different object, never swapped with the row above |
| Document | **Document** | politique, procédure | The register is *Documents* : a policy is one type of document |
| Stakeholder | **Partie intéressée** | partie prenante | ISO 27001 chapitre 4.2. The actors of the EBIOS RM ecosystem keep *partie prenante*, the word of that method |
| Issue | **Enjeu** | facteur de contexte | ISO 27001 chapitre 4.1 |
| Owner | **Propriétaire** : who answers for a record and decides | responsable | |
| Manager | **Responsable** : who runs it (a scope, an action) | pilote | |
| Custodian | **Gestionnaire** : who looks after an asset day to day | dépositaire | |
| Lifecycle | **Cycle de vie** | workflow | |
| Step of a lifecycle | **Étape** | état | The column and the filter that show the step a record stands at are labelled *Statut* |
| Change decided by a management review | **Changement du SMSI** | modification du SMSI | |
| Review | **Revue** | réexamen, révision | |
| Evidence | **Preuve** | élément de preuve | A *justificatif* is the document proving that a notification was filed |
| Likelihood | **Vraisemblance** | probabilité | ISO 27005 |
| Tag | **Étiquette** | tag | |

## Acronyms

An acronym is never a label on its own (rule W2). The words come first, the
acronym follows in brackets where it is a label; it may be used alone after
that, on the same screen. The help of a page spells out the acronyms it uses,
or does not use them (rule W4).

| Acronym | Spelled out |
| --- | --- |
| SMSI | système de management de la sécurité de l'information |
| DIC | disponibilité, intégrité, confidentialité |
| DMT | durée maximale d'interruption tolérable |
| RTO | délai de reprise visé |
| RPO | perte de données maximale admissible |
| SPOF | point de défaillance unique |
| KPI | indicateur clé de performance |
| RACI | réalisateur, approbateur, consulté, informé |
| SWOT | forces, faiblesses, opportunités, menaces |
| DdA | déclaration d'applicabilité |
| TLP | Traffic Light Protocol : *niveau de diffusion (TLP)* as a label |
| SR/OV | source de risque, objectif visé (EBIOS RM) |
| PACS | plan d'amélioration continue de la sécurité (EBIOS RM) |
| DPO | délégué à la protection des données |
| CERT, CSIRT | centre de réponse aux incidents de sécurité informatique |
| SOC, SIEM | centre des opérations de sécurité; gestion des informations et des événements de sécurité |

The continuity acronyms keep the English letters French IT teams use (RTO,
RPO), not the French ones (DMIA, PDMA).

Two kinds of acronym stand as they are :

- **the name of a standard, a law, an agency or a method** (ISO 27001, RGPD,
  NIS2, ANSSI, EBIOS RM, MITRE ATT&CK) : `proper=True` in the glossary;
- **an everyday word of office and IT life** (PDF, URL, API, IA, RH) :
  `core.usability.EVERYDAY_ACRONYMS`.

An acronym met in three strings of the interface or more is in one of these
two lists or in the glossary : the test refuses the others.

## Verbs

One verb per act.

| Act | French | Example |
| --- | --- | --- |
| Open the dialog that creates a record (list button, title of that dialog, search palette) | **Nouveau / Nouvelle …** : the same words where one clicks and where one lands | Nouveau périmètre |
| Confirm a creation | **Créer** | |
| Confirm an edit | **Enregistrer** | |
| Attach something that exists, or add a line inside a record | **Ajouter …** | Ajouter un site |
| Change a record | **Modifier** | |
| Leave without saving | **Annuler** | |
| Move between the steps of a form | **Précédent**, **Suivant** | |
| Record an incident | **Déclarer un incident** : the verb of the trade, kept | |
| Remove for good | **Supprimer** ; **Archiver** when the record is kept | |

## Keeping it true

- A new string follows this page. When a notion has no row, add the row first.
- `core/tests/test_glossary.py` lists the retired spellings as pairs : what the
  English says, the French it must not be given. An exception is a message
  named in the test with its reason (the EBIOS RM ecosystem, *contrôle d'accès*).
- A term of the in-app glossary takes the very message the interface uses for
  it (`_("Stakeholder")`), so the two cannot drift apart.
- Changing a word here means changing the catalogue, the glossary of the
  application and the test in the same commit.
