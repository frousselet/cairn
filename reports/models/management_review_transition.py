import uuid

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class ManagementReviewTransition(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    review = models.ForeignKey(
        "reports.ManagementReview",
        on_delete=models.CASCADE,
        related_name="transitions",
        verbose_name=_("Review"),
    )
    from_status = models.CharField(_("From status"), max_length=20)
    to_status = models.CharField(_("To status"), max_length=20)
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="management_review_transitions",
        verbose_name=_("Performed by"),
    )
    comment = models.TextField(_("Comment"), blank=True, default="")
    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("Management review transition")
        verbose_name_plural = _("Management review transitions")

    def __str__(self):
        return f"{self.review} : {self.from_status} -> {self.to_status}"
