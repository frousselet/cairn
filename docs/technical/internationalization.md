# Internationalisation

Cairn is bilingual, English and French, and treats that as a contract rather
than a feature. Every string a user can see is translatable, and a string that
ships untranslated is a defect.

## How it is set up

| Setting | Value |
| --- | --- |
| `LANGUAGE_CODE` | `en` |
| `LANGUAGES` | `en` (English), `fr` (Français) |
| `LOCALE_PATHS` | `locale/` |
| `TIME_ZONE` | `Europe/Paris`, with `USE_TZ` on |

`LocaleMiddleware` resolves the request language; `UserLanguageMiddleware`
overrides it from the signed-in user's preference, so a user's choice follows
them across devices rather than living in a cookie.

## The path of a string

```
source            _("Overall compliance")            Python
                  {% trans "Overall compliance" %}   template
   │
   ▼
extract           django-admin makemessages -l fr
   │
   ▼
translate         locale/fr/LC_MESSAGES/django.po
   │
   ▼
compile           python manage.py compilemessages   ->  django.mo
   │
   ▼
render            the user sees "Conformité globale"
```

Without the compile step there are no `.mo` files and the interface silently
falls back to English. That is the single most common cause of "the French is
gone" after a deployment. It needs `gettext` (`msgfmt`) installed; the image
already has it, a bare-metal install may not.

## Rules that are enforced

**Every user-facing string is wrapped.** `gettext_lazy` as `_()` in Python,
`{% trans %}` or `{% blocktrans %}` in templates. A literal in a template is a
bug even if it happens to be an English word that reads fine.

**Every new string gets its French translation in the same change.** Leaving an
empty `msgstr` ships an English string into a French interface.

**No duplicate `msgid`.** Two entries with the same `msgid` and no distinct
`msgctxt` make `compilemessages` fail, which fails CI. When a string already
exists in another context, disambiguate rather than duplicate :

```python
from django.utils.translation import pgettext_lazy

title = pgettext_lazy("dashboard widget title", "Summary")
```

```django
{% trans "Summary" context "dashboard widget title" %}
```

and give the `.po` entry a matching `msgctxt` line.

## What is not translated

Data is not. A framework requirement, a risk title and a supplier name are
stored in whatever language they were entered in, and the platform does not
attempt to translate them. Two organisations running Cairn in French and English
will see the same records; only the interface changes.

Stored enum *values* are English identifiers (`in_progress`, `validated`); only
their labels are translated. This is why a status must never be compared against
its label.

## Checking

```bash
python manage.py compilemessages          # fails loudly on a duplicate msgid
msgfmt --statistics locale/fr/LC_MESSAGES/django.po -o /dev/null
```

CI compiles the catalogues before running the suite, so a duplicate or malformed
entry fails the build rather than the deployment.
