"""Querysets implementing the public "published" gate for trust center entities.

``published()`` returns entries that are individually live (their publication
workflow is in a reportable state, i.e. ``published``) AND whose source object
is still valid. The global ``TrustCenterSettings.is_published`` kill switch is a
separate, page-level concern enforced in the view / serializer layer, so these
querysets stay pure (no settings read) and easy to test.
"""

from django.db import models

from trust_center.constants import PublicationState


class PublicationQuerySet(models.QuerySet):
    def published(self):
        return self.filter(workflow_state=PublicationState.PUBLISHED)


class CertificationQuerySet(PublicationQuerySet):
    def published(self):
        from core.workflow import reportable_states

        framework_states = list(reportable_states("compliance.Framework"))
        return (
            super()
            .published()
            .filter(framework__workflow_state__in=framework_states)
        )


class SubprocessorQuerySet(PublicationQuerySet):
    def published(self):
        from assets.constants import SupplierStatus
        from core.workflow import reportable_states

        supplier_states = list(reportable_states("assets.Supplier"))
        return (
            super()
            .published()
            .filter(
                supplier__workflow_state__in=supplier_states,
                supplier__status=SupplierStatus.ACTIVE,
            )
        )


class MeasureQuerySet(PublicationQuerySet):
    """Measures carry no internal source; the base publish gate is sufficient."""


class DocumentQuerySet(PublicationQuerySet):
    def published(self):
        from reports.constants import ReportStatus

        return (
            super()
            .published()
            .filter(
                models.Q(report__isnull=True)
                | models.Q(report__status=ReportStatus.COMPLETED)
            )
        )
