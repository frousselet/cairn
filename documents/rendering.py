# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""Render a document version's rich text to PDF (WeasyPrint), for versions
without an attached PDF (Trust Center download, version export)."""

from django.template.loader import render_to_string
from django.utils import translation


def render_version_pdf(version):
    from weasyprint import HTML

    from trust_center.sanitizers import clean_html

    with translation.override(translation.get_language()):
        html = render_to_string(
            "documents/pdf/version.html",
            {"version": version, "policy": version.policy, "content": clean_html(version.content or "")},
        )
    return HTML(string=html).write_pdf()
