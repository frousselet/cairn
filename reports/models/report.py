# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
import uuid

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

from reports.constants import ReportStatus, ReportType


def _scope_ids_of(sources):
    """The scopes the records in `sources` are filed under."""
    found = set()
    for source in sources or ():
        scopes = getattr(source, "scopes", None)
        if scopes is not None:
            found.update(scopes.values_list("pk", flat=True))
    return found


def scopes_of_risks(risks):
    """The scopes of the risk assessments a set of risks belongs to : what a register was drawn from."""
    from django.apps import apps

    assessments = apps.get_model("risks", "RiskAssessment")._base_manager.filter(
        pk__in=risks.order_by().values("assessment_id")
    )
    return {pk for pk in assessments.values_list("scopes", flat=True) if pk is not None}


class ReportManager(models.Manager):
    def record(self, author, *, sources=(), scope_ids=None, **fields):
        """Create a report, filed under the scopes its content was drawn from.

        ``sources`` are the records it was generated from (an assessment,
        frameworks, the assessments of the risks of a register); ``scope_ids``
        the scopes it covers when it was generated from scopes directly (a
        management review). The filing is what the author saw : for an author
        limited to some scopes, the scopes of the sources that are theirs
        (or all of theirs when the sources name none), since a report holds
        what its author could read and nothing else. An author nothing
        restricts files it under the scopes of its sources, and under none
        when it covers the whole instance : it is then read by those nothing
        restricts (``scope_requires_every_scope``).
        """
        covered = set(scope_ids or ()) | _scope_ids_of(sources)
        allowed = author.get_allowed_scope_ids() if author is not None and not author.is_superuser else None
        if allowed is not None:
            covered = (covered & set(allowed)) or set(allowed)
        report = self.create(created_by=author, **fields)
        if covered:
            report.scopes.set(covered)
        return report


class Report(models.Model):
    # A report is made from what one or several scopes hold : it is read by
    # who is given every scope it is filed under, and one filed under none
    # (the whole instance) by those nothing restricts. Every surface resolves
    # it through core.scoping (lists, records, history, API, MCP).
    scope_requires_every_scope = True

    objects = ReportManager()

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    scopes = models.ManyToManyField(
        "context.Scope",
        related_name="reports",
        verbose_name=_("Scopes"),
        blank=True,
        help_text=_("The scopes its content was drawn from. Empty : the whole instance."),
    )
    report_type = models.CharField(
        _("Report type"),
        max_length=30,
        choices=ReportType.choices,
    )
    name = models.CharField(_("Name"), max_length=255)
    status = models.CharField(
        _("Status"),
        max_length=20,
        choices=ReportStatus.choices,
        default=ReportStatus.COMPLETED,
    )
    assessment = models.ForeignKey(
        "compliance.ComplianceAssessment",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reports",
        verbose_name=_("Assessment"),
    )
    frameworks = models.ManyToManyField(
        "compliance.Framework",
        related_name="reports",
        verbose_name=_("Frameworks"),
        blank=True,
    )
    file = models.FileField(
        _("File"),
        upload_to="reports/%Y/%m/",
        blank=True,
    )
    file_content = models.BinaryField(
        _("File content"),
        blank=True,
        null=True,
        editable=False,
    )
    file_name = models.CharField(
        _("File name"),
        max_length=255,
        blank=True,
        default="",
    )
    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reports_created",
        verbose_name=_("Created by"),
    )

    history = HistoricalRecords()

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("Report")
        verbose_name_plural = _("Reports")

    def __str__(self):
        return self.name
