from django.core.validators import RegexValidator
from django.db import models
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

from context.models.base import BaseModel
from trust_center.constants import MeasureCategory
from trust_center.managers import MeasureQuerySet
from trust_center.lifecycles import PUBLICATION_LIFECYCLE_NAME as PUBLICATION_WORKFLOW_NAME

BOOTSTRAP_ICON_VALIDATOR = RegexValidator(
    r"^bi-[a-z0-9-]+$",
    _("Enter a Bootstrap Icons name, e.g. bi-shield-check."),
)


class TrustCenterMeasure(BaseModel):
    """A security measure advertised on the public Trust Center (curator copy).

    Free-form marketing content under workflow control; not linked to internal
    data, so nothing sensitive can leak through it.
    """

    REFERENCE_PREFIX = "TCME"
    LIFECYCLE_NAME = PUBLICATION_WORKFLOW_NAME

    title = models.CharField(_("Title"), max_length=255)
    description = models.TextField(_("Description"), blank=True, default="")
    icon = models.CharField(
        _("Icon"),
        max_length=50,
        blank=True,
        default="bi-shield-check",
        validators=[BOOTSTRAP_ICON_VALIDATOR],
        help_text=_("Bootstrap Icons name, e.g. bi-shield-check."),
    )
    category = models.CharField(
        _("Category"),
        max_length=20,
        choices=MeasureCategory.choices,
        default=MeasureCategory.ORGANIZATIONAL,
    )
    display_order = models.PositiveIntegerField(_("Display order"), default=0)

    history = HistoricalRecords()

    objects = MeasureQuerySet.as_manager()

    class Meta(BaseModel.Meta):
        verbose_name = _("Trust Center measure")
        verbose_name_plural = _("Trust Center measures")
        ordering = ["display_order", "title"]

    def __str__(self):
        return self.title

    @property
    def workflow_perm_namespace(self):
        return "trust_center.measure"
