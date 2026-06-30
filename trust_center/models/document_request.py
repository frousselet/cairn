from datetime import timedelta

from django.conf import settings
from django.core import signing
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

from context.models.base import BaseModel
from core.query_params import parse_uuid
from trust_center.constants import DocumentRequestState
from trust_center.lifecycles import DOCUMENT_REQUEST_LIFECYCLE_NAME as DOCUMENT_REQUEST_WORKFLOW_NAME

DOWNLOAD_TOKEN_SALT = "trust_center.document_request.download"


class DocumentRequest(BaseModel):
    """An external visitor's request for access to a gated Trust Center document.

    The flow is request -> admin approval -> a time-limited, signed download
    link emailed to the requester. The token is a :class:`TimestampSigner`
    signature over the request UUID, never stored; the gated download view
    validates it statelessly and additionally checks the request is still in the
    ``approved`` state (so a later revoke kills the link before it expires).
    """

    REFERENCE_PREFIX = "DREQ"
    LIFECYCLE_NAME = DOCUMENT_REQUEST_WORKFLOW_NAME

    # Override the BaseModel default ("draft") so requests start in "pending".
    workflow_state = models.CharField(
        _("Lifecycle state"),
        max_length=32,
        default=DocumentRequestState.PENDING,
        db_index=True,
    )

    document = models.ForeignKey(
        "trust_center.TrustCenterDocument",
        on_delete=models.PROTECT,
        related_name="requests",
        verbose_name=_("Document"),
    )
    email = models.EmailField(_("Email"))
    requester_name = models.CharField(_("Name"), max_length=255)
    company = models.CharField(_("Company"), max_length=255, blank=True, default="")
    reason = models.TextField(_("Reason"), blank=True, default="")
    nda_accepted = models.BooleanField(_("NDA accepted"), default=False)
    nda_accepted_at = models.DateTimeField(_("NDA accepted at"), null=True, blank=True)
    ip_address = models.GenericIPAddressField(_("IP address"), null=True, blank=True)
    user_agent = models.TextField(_("User agent"), blank=True, default="")
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_document_requests",
        verbose_name=_("Reviewed by"),
    )
    reviewed_at = models.DateTimeField(_("Reviewed at"), null=True, blank=True)
    decision_note = models.TextField(_("Decision note"), blank=True, default="")
    download_token_issued_at = models.DateTimeField(
        _("Token issued at"), null=True, blank=True
    )
    download_link_expires_at = models.DateTimeField(
        _("Link expires at"), null=True, blank=True
    )
    download_count = models.PositiveIntegerField(_("Download count"), default=0)

    history = HistoricalRecords()

    class Meta(BaseModel.Meta):
        verbose_name = _("Document request")
        verbose_name_plural = _("Document requests")

    def __str__(self):
        return f"{self.reference} : {self.email}"

    @property
    def workflow_perm_namespace(self):
        return "trust_center.document_request"

    @property
    def is_granted(self):
        return self.workflow_state == DocumentRequestState.APPROVED

    # --- Signed download link -------------------------------------------
    @staticmethod
    def _signer():
        return signing.TimestampSigner(salt=DOWNLOAD_TOKEN_SALT)

    def make_download_token(self):
        return self._signer().sign(str(self.pk))

    @classmethod
    def resolve_token(cls, token, max_age):
        """Return the request for a valid, unexpired token.

        Propagates :class:`signing.SignatureExpired` / :class:`signing.BadSignature`
        so the caller can distinguish an expired link from a tampered one.
        """
        pk = parse_uuid(cls._signer().unsign(token, max_age=max_age))
        if pk is None:
            # Validly signed but with a non-UUID payload (a forged token built
            # with a leaked SECRET_KEY); filtering would raise ValidationError.
            return None
        return cls.objects.filter(pk=pk).first()

    def issue_download_link(self, ttl_seconds):
        """Stamp the link lifecycle fields and return a fresh signed token."""
        now = timezone.now()
        self.download_token_issued_at = now
        self.download_link_expires_at = now + timedelta(seconds=ttl_seconds)
        self.save(
            update_fields=[
                "download_token_issued_at",
                "download_link_expires_at",
                "updated_at",
            ]
        )
        return self.make_download_token()
