# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""English display formats: day first, as in the French interface.

Django's ``en`` locale writes short numeric dates month first (11/03/2026),
which a European reader takes for the 11th of March. Cairn's users read both
languages, so the numeric forms put the day first in English too. Only display
formats change; parsing (``*_INPUT_FORMATS``) keeps Django's defaults.
"""

SHORT_DATE_FORMAT = "d/m/Y"
SHORT_DATETIME_FORMAT = "d/m/Y H:i"
