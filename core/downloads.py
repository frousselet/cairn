# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""The content type a stored file is served with.

The type recorded with an upload is the one the uploading browser declared :
it is whatever the uploader wanted it to be. Served back as is, from the
instance's own origin, a file declared ``text/javascript`` is a script the
Content Security Policy accepts (``script-src 'self'``), and one declared
``text/html`` is a page of the instance. A download is therefore served with
its recorded type only when that type is inert, and as opaque bytes otherwise.
Together with ``Content-Disposition: attachment`` and ``nosniff``, the browser
saves it and never interprets it.
"""

# Types a browser neither executes nor renders as a document of the origin.
INERT_CONTENT_TYPES = frozenset({
    "application/pdf",
    "image/png", "image/jpeg", "image/gif", "image/webp",
    "text/plain", "text/csv",
    "application/zip",
    "application/msword",
    "application/vnd.ms-excel",
    "application/vnd.ms-powerpoint",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "application/vnd.oasis.opendocument.text",
    "application/vnd.oasis.opendocument.spreadsheet",
})
OPAQUE = "application/octet-stream"


def safe_content_type(recorded):
    """``recorded`` when it is inert, ``application/octet-stream`` otherwise."""
    declared = (recorded or "").split(";", 1)[0].strip().lower()
    return declared if declared in INERT_CONTENT_TYPES else OPAQUE
