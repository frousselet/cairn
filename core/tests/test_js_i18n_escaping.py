"""Guard against a class of i18n bug: a ``{% trans %}`` string dropped straight
into a single-quoted JavaScript string literal. When the translation contains an
apostrophe (very common in French, e.g. "l'URL", "d'audit"), the apostrophe
terminates the JS string and breaks the whole script with a SyntaxError. Such
strings must be wrapped in ``{% filter escapejs %}`` (which the regex below no
longer matches, so escaped usages are correctly ignored).
"""

import re

import pytest
from django.conf import settings
from django.utils import translation

# Matches `'{% trans "Some text" %}'` - a trans tag sitting inside a
# single-quoted JS string, WITHOUT an escapejs wrapper.
_PATTERN = re.compile(r"""'\{%\s*trans\s+"([^"]+)"\s*%\}'""")


def _iter_template_files():
    for tpl_dir in (settings.BASE_DIR,):
        for path in tpl_dir.rglob("*.html"):
            if "/.venv/" in str(path) or "/site-packages/" in str(path):
                continue
            yield path


@pytest.mark.django_db
def test_single_quoted_js_trans_have_no_apostrophe_in_french():
    offenders = []
    with translation.override("fr"):
        for path in _iter_template_files():
            try:
                text = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            for match in _PATTERN.finditer(text):
                msgid = match.group(1)
                french = translation.gettext(msgid)
                if "'" in french or "’" in french:
                    offenders.append(
                        f"{path.relative_to(settings.BASE_DIR)}: "
                        f'"{msgid}" -> "{french}"'
                    )
    assert not offenders, (
        "Translated strings with an apostrophe are placed in single-quoted JS "
        "strings without escapejs (they break the script). Wrap them in "
        "{% filter escapejs %}...{% endfilter %}:\n" + "\n".join(offenders)
    )
