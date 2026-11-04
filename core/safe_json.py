# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""JSON that is safe to place inside a ``<script>`` element.

``json.dumps`` leaves ``<``, ``>`` and ``&`` as they are, so a value such as an
asset named ``</script><script>...`` ends the script element and injects
markup. The escapes below are those Django's ``json_script`` applies; use this
when a template embeds JSON with ``|safe`` instead of ``json_script``.
"""

import json

_SCRIPT_ESCAPES = {ord("<"): "\\u003C", ord(">"): "\\u003E", ord("&"): "\\u0026"}


def dumps_for_script(value, **kwargs):
    return json.dumps(value, **kwargs).translate(_SCRIPT_ESCAPES)
