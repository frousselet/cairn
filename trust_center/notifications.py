"""Outbound email to external (non-user) Trust Center requesters.

The requester is not a Cairn user, so these messages bypass the in-app
:class:`~accounts.models.Notification` model and the per-user language override:
they are plain ``send_mail`` calls rendered in the instance's default language.
"""

import logging

from django.conf import settings
from django.core.mail import send_mail
from django.utils import translation
from django.utils.translation import gettext as _

logger = logging.getLogger(__name__)


def _absolute(url):
    site = getattr(settings, "SITE_URL", "") or ""
    if url.startswith("http://") or url.startswith("https://"):
        return url
    return f"{site}{url}"


def send_gated_link_email(instance, download_url):
    """Email the approved requester a (time-limited) signed download link."""
    full_url = _absolute(download_url)
    with translation.override(settings.LANGUAGE_CODE):
        subject = _('Your access to "%(doc)s"') % {"doc": str(instance.document)}
        body = _(
            'Your request to access "%(doc)s" has been approved.\n\n'
            "Use the link below to download the document. The link is personal "
            "and expires after a limited time:\n\n%(url)s"
        ) % {"doc": str(instance.document), "url": full_url}
    try:
        send_mail(subject, body, None, [instance.email], fail_silently=False)
    except Exception:
        logger.exception("Failed to send gated download link to %s", instance.email)
        return False
    return True
