from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy


class DocumentAccess(models.TextChoices):
    PUBLIC = "public", pgettext_lazy("trust center", "Public")
    GATED = "gated", pgettext_lazy("trust center", "Gated")


class MeasureCategory(models.TextChoices):
    ORGANIZATIONAL = "organizational", _("Organizational")
    TECHNICAL = "technical", _("Technical")
    PHYSICAL = "physical", _("Physical")


# Bootstrap Icons name per file extension, for document type badges.
FILE_TYPE_ICONS = {
    "pdf": "bi-filetype-pdf",
    "doc": "bi-filetype-doc",
    "docx": "bi-filetype-docx",
    "ppt": "bi-filetype-ppt",
    "pptx": "bi-filetype-pptx",
    "xls": "bi-filetype-xls",
    "xlsx": "bi-filetype-xlsx",
    "csv": "bi-filetype-csv",
    "txt": "bi-filetype-txt",
    "json": "bi-filetype-json",
    "xml": "bi-filetype-xml",
    "zip": "bi-file-earmark-zip",
    "png": "bi-filetype-png",
    "jpg": "bi-filetype-jpg",
    "jpeg": "bi-filetype-jpg",
    "svg": "bi-filetype-svg",
}
DEFAULT_FILE_ICON = "bi-file-earmark-text"


# --- Publication workflow ---------------------------------------------------
# Shared by certifications, subprocessors, measures and documents. "published"
# is the only state that counts in reports (i.e. is live on the public page);
# "archived" is the terminal off-ramp.


class PublicationState:
    """State codes for the ``trust_center_publication`` workflow."""

    DRAFT = "draft"
    PUBLISHED = "published"
    UNPUBLISHED = "unpublished"
    ARCHIVED = "archived"


# code -> (label, counts_in_reports, linkable, deletable, is_initial, is_terminal, tone, branch)
PUBLICATION_STATES = [
    (PublicationState.DRAFT, _("Draft"), False, False, True, True, False, "secondary", False),
    (PublicationState.PUBLISHED, pgettext_lazy("trust center", "Published"), True, False, False, False, False, "success", False),
    (PublicationState.UNPUBLISHED, _("Unpublished"), False, False, True, False, False, "warning", False),
    (PublicationState.ARCHIVED, _("Archived"), False, False, False, False, True, "dark", True),
]

# (source, target, verb, permission action) - single source of truth for the
# publication transitions. Going live or hiding requires the "approve" action
# (only RSSI/DPO and admins); archiving a draft is a plain update.
PUBLICATION_TRANSITIONS = [
    (PublicationState.DRAFT, PublicationState.PUBLISHED, _("Publish"), "approve"),
    (PublicationState.DRAFT, PublicationState.ARCHIVED, _("Archive"), "update"),
    (PublicationState.PUBLISHED, PublicationState.UNPUBLISHED, _("Unpublish"), "approve"),
    (PublicationState.PUBLISHED, PublicationState.ARCHIVED, _("Archive"), "approve"),
    (PublicationState.UNPUBLISHED, PublicationState.PUBLISHED, _("Publish"), "approve"),
    (PublicationState.UNPUBLISHED, PublicationState.ARCHIVED, _("Archive"), "update"),
]


# --- Document request workflow ----------------------------------------------
# A visitor's request for a gated document. "approved" issues a time-limited
# signed download link; "rejected" is the single off-ramp reachable both from
# "pending" (decline) and from "approved" (revoke access). Link expiry itself is
# enforced by the signed-token max age, not a separate state.


class DocumentRequestState:
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


# code -> (label, counts_in_reports, linkable, deletable, is_initial, is_terminal, tone, branch)
DOCUMENT_REQUEST_STATES = [
    (DocumentRequestState.PENDING, _("Pending review"), False, False, True, True, False, "warning", False),
    (DocumentRequestState.APPROVED, _("Approved"), True, False, False, False, False, "success", False),
    (DocumentRequestState.REJECTED, _("Rejected"), False, False, False, False, True, "danger", True),
]

# (source, target, verb, permission action, requires_comment)
DOCUMENT_REQUEST_TRANSITIONS = [
    (DocumentRequestState.PENDING, DocumentRequestState.APPROVED, _("Approve"), "approve", False),
    (DocumentRequestState.PENDING, DocumentRequestState.REJECTED, _("Reject"), "approve", True),
    (DocumentRequestState.APPROVED, DocumentRequestState.REJECTED, _("Revoke access"), "approve", True),
]
