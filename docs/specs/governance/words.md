# Words : glossary and help

> Platform-wide. What makes the interface readable by someone who has never
> used it : one name per thing, shown in the application, and a help on every
> page. The rules are W1 to W4 of the
> [usability standard](../../sdk/usability-standard.md); the vocabulary itself
> is [docs/brand/glossary.md](../../brand/glossary.md).

## 1. The glossary

### 1.1 Registry

`core/glossary.py` declares the vocabulary once.

| Object | Fields | Meaning |
| --- | --- | --- |
| `Term` | `key`, `name`, `definition`, `also`, `url_name` | A notion of the product under the one name the interface gives it; a definition a newcomer can read, with an example; the other names people know it by (one string, comma separated); the register where it lives |
| `Acronym` | `key`, `letters`, `words`, `definition`, `proper` | An acronym a screen may show, spelled out and explained. `proper` marks the name of a standard, a law, an agency or a method, used as it is |

| Rule | |
| --- | --- |
| RG-WD-01 | A term takes the very message the interface uses for the thing (`_("Stakeholder")`, or the message with its context), so the glossary cannot name a thing otherwise than the screens do. |
| RG-WD-02 | Every string of the registry is translated. `also` and the letters of an acronym have their own contexts (`glossary : other names`, `glossary : acronym`) : the other names of a thing are not the same in each language (*tag* is the other name of *étiquette*, not its translation), and neither are the letters (*ISMS*, *SMSI*). |
| RG-WD-03 | A definition is one or two sentences, forty words at most, ends with a full stop and leans on no acronym the glossary does not explain. |
| RG-WD-04 | The registry is code, not data : it is the vocabulary of the product, the same on every instance, and is not editable in the administration. |

### 1.2 Search

`terms(query, deep=True)` and `acronyms(query, deep=True)` return the entries
in the language in use, sorted without case nor accents. A query is compared
the same way.

| Rule | |
| --- | --- |
| RG-WD-05 | A query matches the name of a term, any of its other names, the letters of an acronym or its words. With `deep`, it also matches the definitions. |
| RG-WD-06 | The page, the REST endpoint and the MCP tool search deep. The search palette does not : a word that merely appears in a definition would bury the records. |

### 1.3 Surfaces

| Surface | Address | Access | Content |
| --- | --- | --- | --- |
| Page | `/glossary/` (`glossary`), `?q=` | Any signed-in user | Words, then acronyms. A term links to its register for who may open it (`core.navigation.required_permissions`) |
| Search palette | `/api/search/?q=` | Any signed-in user | A *Glossary* group : the name used for the word typed, linking to the entry (`#term-<key>`, `#acronym-<key>`); and a *Glossary* navigation entry |
| REST | `GET /api/v1/glossary/`, `?q=` | Any authenticated caller | `{"terms": [{key, name, definition, also_called, url}], "acronyms": [{key, acronym, meaning, definition}]}`, in the language of the request |
| MCP | `get_glossary(query, language)` | Any authenticated caller, no permission : it holds no record | Same payload, in the language of the user unless `language` (`en`, `fr`) is given |

The glossary is reached from the account menu of the sidebar and from the foot
of every help.

## 2. The help of a page

### 2.1 Content

`helpers.HelpContent` holds one row per page and language : `key` (the
identifier of the page, `context.scope_list`), `language`, `title`, `body`
(plain text, paragraphs separated by a blank line). A page asks for its help
with `{% help_modal "key" %}`, placed under its header.

| Rule | |
| --- | --- |
| RG-HP-01 | The title is one sentence that says what the thing is, or what the page is for : three to eighteen words, no final full stop, never the name of the page again nor "... details". |
| RG-HP-02 | The body gives an example, then what to do first or what to watch : twelve to seventy words. The help of a register starts from things a newcomer can picture. |
| RG-HP-03 | A help spells out the acronyms it uses, every word of them, or does not use them. A proper name and an everyday word stand as they are. No section sign. |
| RG-HP-04 | The French uses the words of the glossary. |
| RG-HP-05 | Every page that asks for a help has one in English and in French, and no help is written for a page that does not exist. |
| RG-HP-06 | A help is shipped by a data migration of `helpers`. The migration replaces a row only while it still holds the text a previous migration shipped (recognised by a fingerprint of the old title and body) and creates a row that does not exist : a help an administrator rewrote is theirs. |
| RG-HP-07 | The text follows the language of the reader, then its base language (`fr-ca` reads `fr`), then English. A page without a text renders nothing. |

### 2.2 Shown, hidden, brought back

The help is open until the reader hides it. Hidden, it leaves a *Help on this
page* button in its place, which brings it back. The choice is kept per reader
in `User.dismissed_helpers`, a list of page keys (it also holds
`getting_started`, the first steps of the dashboard).

| Rule | |
| --- | --- |
| RG-HP-08 | The block is a note (`role="note"`) named by its title, never an alert. Hiding moves the focus to the button, showing moves it to the note. |
| RG-HP-09 | The block carries no inline style and no script : it names the actions `hidePageHelp` and `showPageHelp`, registered once in `static/js/cairn/actions.js`. |
| RG-HP-10 | `POST /helpers/dismiss/` with `{"key": "<page key>", "dismissed": true \| false}` keeps the choice (`dismissed` left out means hidden). A body that is not an object, a key that is not a string of one to a hundred characters, or a `dismissed` that is not a boolean is refused with `400`, and nothing is stored. |
| RG-HP-11 | A reader keeps five hundred hidden keys at most : past that, hiding is refused, bringing back still works. |
| RG-HP-12 | The profile page keeps its *restore the help* action, which brings every help back at once. |

## 3. The catalogue

The French catalogue (`locale/fr/LC_MESSAGES/django.po`) is maintained by hand.
Three test modules read it and the code, and fail the build on :

| Check | Test |
| --- | --- |
| A string the code asks a translation for, with no French (extracted the way `makemessages` does); a menu label or a column heading with no French | `core/tests/test_translations.py` |
| A sentence used with a count whose French entry is a singular one (gettext then never finds it, and the reader gets the English) | `core/tests/test_translations.py` |
| A translation that uses a variable its sentence does not provide, or drops one | `core/tests/test_translations.py` |
| A French spelling the glossary retires, given to the English that names the thing; *assessment* rendered as *évaluation* in a message of the risk module | `core/tests/test_glossary.py` |
| A message, a field label or a choice made of an acronym alone; an acronym met in three strings or more and explained nowhere | `core/tests/test_glossary.py` |

## 4. Technical considerations

- The registry is read on the page, in the palette and by the two interfaces
  from the same functions : there is no second list to keep in step.
- The help of a page costs one query (the three candidate languages at once).
- The capture of the documentation screenshots removes the help block, except
  for the image that shows it (`scripts/capture_screenshots.py`, `WITH_HELP`).
