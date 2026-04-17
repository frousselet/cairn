from django.db import models
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

from context.constants import (
    FeedbackChannel,
    FeedbackSentiment,
    FeedbackSeverity,
    FeedbackStatus,
)
from .base import ScopedModel


class StakeholderFeedback(ScopedModel):
    """Formal feedback received from an interested party.

    Distinct from StakeholderExpectation (which captures permanent
    requirements). This model logs discrete interactions (surveys, meetings,
    complaints, etc.) that must be considered during the management review
    per ISO 27001:2022 clause 9.3.2.e.
    """

    REFERENCE_PREFIX = "FBCK"

    stakeholder = models.ForeignKey(
        "context.Stakeholder",
        on_delete=models.CASCADE,
        related_name="feedback_items",
        verbose_name=_("Stakeholder"),
    )
    channel = models.CharField(
        _("Channel"), max_length=20, choices=FeedbackChannel.choices,
    )
    received_date = models.DateField(_("Received date"))
    subject = models.CharField(_("Subject"), max_length=255)
    content = models.TextField(_("Content"))
    sentiment = models.CharField(
        _("Sentiment"),
        max_length=20,
        choices=FeedbackSentiment.choices,
        blank=True,
        default="",
    )
    severity = models.CharField(
        _("Severity"),
        max_length=20,
        choices=FeedbackSeverity.choices,
        blank=True,
        default="",
    )
    status = models.CharField(
        _("Status"),
        max_length=20,
        choices=FeedbackStatus.choices,
        default=FeedbackStatus.NEW,
    )
    response = models.TextField(_("Response"), blank=True, default="")
    linked_issues = models.ManyToManyField(
        "context.Issue",
        blank=True,
        related_name="stakeholder_feedback",
        verbose_name=_("Linked issues"),
    )
    linked_expectations = models.ManyToManyField(
        "context.StakeholderExpectation",
        blank=True,
        related_name="stakeholder_feedback",
        verbose_name=_("Linked expectations"),
    )

    history = HistoricalRecords()

    class Meta(ScopedModel.Meta):
        verbose_name = _("Stakeholder feedback")
        verbose_name_plural = _("Stakeholder feedback")

    def __str__(self):
        return f"{self.reference} : {self.subject}"
