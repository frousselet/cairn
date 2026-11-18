# Usability standard

Cairn must be usable by someone who has never used it, without hours of
training. This page says what a screen owes to that person. It is a standard,
not advice : each rule is numbered, says how it is checked, and a screen that
breaks one is a bug.

The rules were written from what a newcomer met on a fresh instance : a
dashboard reading "everything is in order" with nothing in it, a creation form
of twenty-two fields in four steps of which seven were required, an unlabelled
round arrow to move on, a helper under *Name* reading "Name of the scope",
three French words for one thing, and a help that read "This page presents the
selected risk criteria set" and was gone for good once closed.

The rules about forms and records are applied module by module. The screens
that follow them are listed in
[`core/tests/test_usability_standard.py`](../../core/tests/test_usability_standard.py),
which holds them to it; what is not listed yet is not claimed to follow them.
Scopes and the assets module were the first. The rules about words (W1 to W4)
hold for the whole product.

## The idea : create short, complete on the record

A record is **created with the few fields that make it exist**, on one screen.
It then opens on its own page, which **lists what it still needs** and offers,
card by card, the short dialog that fills it. Nothing is lost in rigour : the
lifecycle **refuses to make an incomplete record authoritative**, and says what
is missing.

The alternative (asking everything at creation, in steps) is what makes a tool
feel like a tax form. Two thirds of the fields of the product are optional; a
newcomer cannot tell which, and stops.

## The rules

### First contact

| # | Rule | How it is checked |
| --- | --- | --- |
| N1 | An instance that holds nothing says what to do first. The dashboard opens on the *first steps* (`core/getting_started.py`) until the instance holds its first records. | `core/tests/test_getting_started.py` |
| N2 | A register with nothing in it says what the thing is, in a sentence without jargon, and offers to create the first one to who may. Emptied by a search or a filter, it says that instead. | `{% list_empty %}`; `test_usability_standard.py` reads the rows partial of each listed register |
| N3 | A page never reports a success or a failure of something that has not begun : no "all clear", no 0 % in red, on an instance with nothing in it. | `test_getting_started.py` |

### Words

| # | Rule | How it is checked |
| --- | --- | --- |
| W1 | One thing, one name, everywhere : the menu, the buttons, the helpers, the help and the documentation use the word of the [glossary](../brand/glossary.md). The application shows that vocabulary on its *Glossary* page, and its search answers the other names people know a thing by. | `core/tests/test_glossary.py` reads the French catalogue and refuses the spellings the glossary retires |
| W2 | A label is made of words. An acronym follows them in brackets : *Recovery time objective (RTO)*, never *RTO* alone. An everyday word (*PDF*, *URL*) stands as it is, and an acronym that spreads through the interface is explained in the glossary. | `core.usability.is_unexplained_acronym`, over every message, field and choice; `test_glossary.py` |
| W3 | A button says what it does : *Create* on a creation, *Save* on an edit, *Previous* / *Next* between steps, *Cancel* to leave. No button made of an icon alone moves through a form. | `core/tests/test_modal_forms.py` |
| W4 | A page has a help that a newcomer can read : its title is one sentence saying what the thing is, its body gives an example and says what to do first or what to watch, in seventy words at most, and it spells out the acronyms it uses. The reader hides it, and brings it back with *Help on this page*. | `helpers/tests/test_help_content.py` |

### Forms

| # | Rule | How it is checked |
| --- | --- | --- |
| F1 | A creation form asks for what makes the record exist : **six fields at most, one screen, no steps**. | `core.usability.form_findings(form, creation=True)` |
| F2 | A question that cannot have an answer is not asked (the parent of the very first scope, the scope when there is only one). | Per form; the engine follows a field the form drops |
| F3 | After a creation the user lands on the record, not back on the list. | `HtmxFormMixin.land_on_record`; `test_usability_standard.py` |
| F4 | A record is edited one card at a time : each step of its form is a **section** (`Step(..., key=...)`) that opens on its own from its card. | `test_usability_standard.py` |
| F5 | A helper says something its label does not (an example, a consequence, how to answer), or is absent. | `core.usability.help_restates_label`, in the two languages shipped |
| F6 | A notion is explained once, in the sentence that introduces its section (`Step(..., intro=...)`), not in the helper of each field. | Review |
| F7 | A required field left empty answers with its own name and what to do : *Fill in "Name".*, never one sentence repeated under every field. | `core.modal_forms.name_required_errors`; `test_modal_forms.py` |
| F8 | A default is never a silent decision : a value that stands for an assessment starts empty, reads *Not assessed*, and counts as missing. A classification a creation form asks (the criticality of a supplier, the type of a site) opens on no answer, whatever the model defaults to. | Per model (the security needs of an essential asset); `CreationFormMixin.decisions` (`core/tests/test_modal_forms.py`) |
| F9 | A scale shows its words. A level reads *High*, not *3*; the numeric pill is kept for a table cell that holds several. | `{{ level\|dic_level }}`; `assets/tests/test_essential_asset_completion.py` |

### Records

| # | Rule | How it is checked |
| --- | --- | --- |
| R1 | The page of a record lists what it still needs, what the lifecycle waits for first, each line opening the dialog that fills it. | `{% completeness_card %}`; `test_usability_standard.py` |
| R2 | A record cannot reach a step that makes it authoritative while something it needs is missing, and the refusal says what remains to be done, on the web, the REST API and the MCP server. | `core/tests/test_completeness.py` |
| R3 | What the system knows is not asked : the day a scope comes into force is filled in by its lifecycle. | Per model |

## Applying it to an entity

The work is the same for every entity, and short. Scopes
([`context/forms.py`](../../context/forms.py)), the assets module
([`assets/forms.py`](../../assets/forms.py) : essential and support assets,
suppliers, asset groups, sites, contracts, certificates) and the compliance
module ([`compliance/forms.py`](../../compliance/forms.py) : frameworks,
requirements, assessments, findings, action plans) are the examples to read.
The action plan is the one to read for a field that was required at creation :
its gap and its remediation are now what its lifecycle waits for. The
requirement is the one to read for a record that hangs under another and is
not filed under scopes itself.

**1. Choose what creation asks.** What makes the record exist and be
recognised : its name, what it is, who answers for it. Six fields at most. The
creation form is its own class, with its own `Meta.fields` and a single step :

```python
class ScopeCreateForm(ScopeBaseForm):
    steps = [Step(_("Identity"), "diagram-3", [[("icon", "auto"), "name"], "parent_scope", "description"])]

    class Meta(ScopeBaseForm.Meta):
        fields = ["name", "description", "parent_scope", "icon"]
```

A creation form of an entity filed under scopes puts `CreationFormMixin`
([`core/modal_forms.py`](../../core/modal_forms.py)) first in its bases. It
settles the two questions that often have one answer only : with a single scope
the reader may file under, the scope is not asked and the record is filed under
it; and whoever creates the record answers for it (`owner_field`) unless they
say otherwise.

```python
class SupportAssetCreateForm(CreationFormMixin, SupportAssetBaseForm):
    steps = [Step(_("Identity"), "hdd-stack", ["name", ["category", "owner"], "scopes", "description"])]

    class Meta(SupportAssetBaseForm.Meta):
        fields = ["scopes", "name", "description", "category", "owner"]
```

`decisions = ("criticality",)` names the choice fields the reader decides : the
select opens on *Choose…* and an answer is required, where the default of the
model would have been saved without anybody choosing it. `owner_field = None`
is for an entity that has no owner. A form drops in its `__init__` a question
that cannot have an answer (the type of a supplier when no type is declared,
the parent of the very first site).

A field of the model that had a default standing for an assessment becomes
nullable (rule F8), with its migration. A field the reader no longer answers
because another one settles it (the type of an asset, which follows from its
category) is set by the form, in `clean`.

The rows a record carries (the contacts of a supplier) have no page of their
own : their form is held to F1 and to the rules on helpers, and is listed in
`_forms()` alone.

**2. Make each step of the form a section.** One step per card of the record
page, each with a `key`, and an `intro` where a notion needs explaining :

```python
Step(_("Boundaries and exclusions"), "bounding-box",
     ["boundaries", "justification_exclusions"],
     key="boundaries",
     intro=_("Where the scope stops : what is left out, and why."))
```

The form's `__init__` prepares a field only when it is there
(`if "managers" in self.fields:`) : a form opened on one section carries the
fields of that section alone.

**3. Say what complete means.** On the model, with the steps that wait for it :

```python
COMPLETENESS = Completeness(
    Requirement("managers", _("name at least one manager"),
                fields=["managers"], section="managers"),
    Requirement("sites", _("attach the sites it covers"),
                fields=["included_sites"], section="sites", blocking=False),
    before=("validation", "in_force"),
)
```

A label is an act in the infinitive, without a capital : it is shown
capitalised as a line of the list, and as written inside the sentence of a
refusal. `blocking=False` is an advice the record can do without. See
[`core/completeness.py`](../../core/completeness.py).

**4. Wire the views.** `land_on_record = True` on the create and update views
(the model needs a `get_absolute_url`), `CompleteOnRecordMixin` on the detail
view with `edit_url_name` and `edit_permission`.

**5. Lay the page out as its sections.** `{% completeness_card completeness
edit_url=edit_url %}` first, then one `{% section_card %}` per section of the
form, each with `{% section_edit edit_url "key" _("Title") %}` in its `actions`
slot. The rows partial of the register ends on `{% list_empty %}`. See
[UI components](ui-components.md).

**6. Write the helpers.** Each one says what its label does not, or is removed.
Run `core.usability.form_findings` on the forms, in English and in French.
Write the help of the list and of the record page the same way (rule W4), in a
data migration of `helpers` modelled on
[`0012_plain_words_everywhere`](../../helpers/migrations/0012_plain_words_everywhere.py),
and give a new notion its row in the [glossary](../brand/glossary.md) and its
entry in [`core/glossary.py`](../../core/glossary.py).

**7. Expose it.** `CompletenessSerializerMixin` on the serializer of a single
record ([`core/completeness_api.py`](../../core/completeness_api.py)); the
generic MCP `get_` tool adds it by itself. The transition tools and endpoints
already answer with the refusal.

**8. List the entity** in `core/tests/test_usability_standard.py` : its two
forms in `_forms()`, its views and templates in `_pages()`. The tests then
create a record through the dialog with what it requires alone, check where the
reader lands, that each section of the form has its card, and that a reader is
offered no edit. Update its specification and its page of the user guide.

## What the shared shell already gives every form

These came with the standard and apply to the forms that have not been
shortened yet :

- a footer whose buttons carry words (*Cancel*, *Previous*, *Next*, *Create* /
  *Save*) in place of the round arrows that floated outside the dialog;
- a step indicator whose steps are buttons, which names the current step whole
  past four steps instead of cutting every title to its first letters;
- a record being edited can be saved from any step, and every step is open;
- required fields that answer with their own name;
- the close button at the far end of the header.

## Checks

| Check | What it holds |
| --- | --- |
| `core/tests/test_usability_standard.py` | The listed forms and pages : creation size, helpers, labels, sections, landing, completeness card, empty register |
| `core/tests/test_modal_forms.py` | The shell : buttons with words, steps as buttons, sections, named required errors |
| `core/tests/test_completeness.py` | The declarations against the lifecycles and the forms; the refusal on every surface |
| `core/tests/test_getting_started.py` | The first steps and the messages of an instance with nothing in it |
| `core/tests/test_glossary.py` | The vocabulary : no retired spelling in the French catalogue, no acronym alone as a label, the glossary on its page, in the search, over REST and MCP |
| `core/tests/test_translations.py` | Every string of the interface has its French, a sentence used with a count is filed as a plural, a translation carries the variables of its sentence |
| `helpers/tests/test_help_content.py` | The help of every page : written for each page that asks for one, in both languages, in plain words; hidden and brought back |
| The interface sweep and `scripts/a11y_audit.py` | Every page and dialog still renders, in both themes, with no accessibility defect |
