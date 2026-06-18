import uuid

from django.core.validators import RegexValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

HEX_COLOR_VALIDATOR = RegexValidator(
    r"^#[0-9A-Fa-f]{6}$",
    message=_("Enter a colour as a 6-digit hex code, e.g. #1E3A8A."),
)


class CompanySettings(models.Model):
    """Singleton model storing company-wide settings (name, address, logo)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_("Company name"), max_length=255, blank=True, default="")
    address = models.TextField(_("Address"), blank=True, default="")
    app_name = models.CharField(
        _("Application name"),
        max_length=100,
        blank=True,
        default="",
        help_text=_(
            "Custom name shown in the sidebar and the browser tab titles. "
            "Defaults to Cairn when left empty."
        ),
    )
    accent_color = models.CharField(
        _("Accent colour"),
        max_length=7,
        blank=True,
        default="",
        validators=[HEX_COLOR_VALIDATOR],
        help_text=_(
            "Hex colour (e.g. #1E3A8A) used as the accent throughout the "
            "application. Defaults to the Cairn navy when left empty."
        ),
    )
    logo = models.TextField(_("Logo"), blank=True, default="")
    logo_32 = models.TextField(_("Logo 32×32"), blank=True, default="")
    logo_64 = models.TextField(_("Logo 64×64"), blank=True, default="")
    logo_128 = models.TextField(_("Logo 128×128"), blank=True, default="")
    use_logo_as_app_brand = models.BooleanField(
        _("Use the company logo as the application logo"),
        default=False,
        help_text=_(
            "Replace the Cairn logo in the sidebar with the company logo. "
            "The About dialog always keeps the Cairn logo."
        ),
    )
    updated_at = models.DateTimeField(_("Updated at"), auto_now=True)

    class Meta:
        verbose_name = _("Company settings")
        verbose_name_plural = _("Company settings")

    def __str__(self):
        return self.name or str(_("Company settings"))

    def save(self, *args, **kwargs):
        # Enforce singleton: always use the same PK
        if not CompanySettings.objects.exists():
            super().save(*args, **kwargs)
        else:
            existing = CompanySettings.objects.first()
            self.pk = existing.pk
            super().save(*args, **kwargs)

    @classmethod
    def get(cls):
        """Return the singleton instance, creating it if necessary."""
        obj, _ = cls.objects.get_or_create(
            pk=cls.objects.values_list("pk", flat=True).first()
            or uuid.uuid4()
        )
        return obj
