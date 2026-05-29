import uuid

from django.db import models
from django.utils.translation import gettext_lazy as _

from risks.constants import MitreAttackTactic


class MitreAttackTechnique(models.Model):
    """MITRE ATT&CK Enterprise Matrix catalogue entry.

    Seeded from `risks/fixtures/mitre_attack_v15.json` via data migration and
    refreshable through `python manage.py refresh_mitre_attack <path>`. The
    natural key is `mitre_id` (e.g. "T1566", "T1566.001"). Sub-techniques
    reference their parent through `parent_technique`.

    This catalogue is shared across the whole platform (no scope) so multiple
    assessments can reference the same FK without duplication.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    mitre_id = models.CharField(_("MITRE identifier"), max_length=32, unique=True)
    name = models.CharField(_("Name"), max_length=255)
    description = models.TextField(_("Description"), blank=True)
    tactic = models.CharField(
        _("Tactic"),
        max_length=32,
        choices=MitreAttackTactic.choices,
        db_index=True,
    )
    parent_technique = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sub_techniques",
        verbose_name=_("Parent technique"),
    )
    version = models.CharField(_("MITRE version"), max_length=16, default="15.1")
    url = models.CharField(_("URL"), max_length=500, blank=True)
    is_active = models.BooleanField(_("Active"), default=True)
    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated at"), auto_now=True)

    class Meta:
        ordering = ["tactic", "mitre_id"]
        verbose_name = _("MITRE ATT&CK technique")
        verbose_name_plural = _("MITRE ATT&CK techniques")

    def __str__(self):
        return f"{self.mitre_id} {self.name}"
