import uuid

from django.core.validators import RegexValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

HEX_COLOR_VALIDATOR = RegexValidator(
    r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$",
    _("Enter a valid hex colour, e.g. #1E3A8A."),
)


class TrustCenterSettings(models.Model):
    """Singleton storing the public Trust Center configuration.

    Mirrors :class:`accounts.models.CompanySettings`: a single row, accessed via
    :meth:`get`, with the ``save`` override enforcing the singleton invariant.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    is_published = models.BooleanField(
        _("Trust Center published"),
        default=False,
        help_text=_("When off, the public Trust Center returns a 404 for everyone."),
    )
    headline = models.CharField(_("Headline"), max_length=255, blank=True, default="")
    intro = models.TextField(_("Introduction"), blank=True, default="")
    contact_email = models.EmailField(
        _("Security contact email"), blank=True, default=""
    )
    show_compliance_percentages = models.BooleanField(
        _("Show compliance percentages"),
        default=True,
        help_text=_("Global toggle for numeric compliance percentages on certifications."),
    )
    theme_accent = models.CharField(
        _("Accent colour"),
        max_length=7,
        blank=True,
        default="#1E3A8A",
        validators=[HEX_COLOR_VALIDATOR],
    )
    custom_domain = models.CharField(
        _("Custom domain"),
        max_length=255,
        blank=True,
        default="",
        help_text=_(
            "Informational only. Routing on a separate domain is configured via "
            "the TRUST_CENTER_HOST environment variable."
        ),
    )
    custom_css = models.TextField(
        _("Custom CSS"),
        blank=True,
        default="",
        help_text=_("Optional CSS injected into the public page to override the theme."),
    )
    updated_at = models.DateTimeField(_("Updated at"), auto_now=True)

    class Meta:
        verbose_name = _("Trust Center settings")
        verbose_name_plural = _("Trust Center settings")

    def __str__(self):
        return self.headline or str(_("Trust Center settings"))

    def save(self, *args, **kwargs):
        # Enforce singleton: always reuse the same PK.
        if not TrustCenterSettings.objects.exists():
            super().save(*args, **kwargs)
        else:
            existing = TrustCenterSettings.objects.first()
            self.pk = existing.pk
            super().save(*args, **kwargs)

    @classmethod
    def get(cls):
        """Return the singleton instance, creating it if necessary."""
        obj, _created = cls.objects.get_or_create(
            pk=cls.objects.values_list("pk", flat=True).first() or uuid.uuid4()
        )
        return obj
