# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
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
        from core.lifecycle import reportable_states

        framework_states = list(reportable_states("compliance.Framework"))
        return (
            super()
            .published()
            .filter(framework__workflow_state__in=framework_states)
        )


class SubprocessorQuerySet(PublicationQuerySet):
    def published(self):
        # Publishable when the supplier is ACTIVE *and* in a reportable lifecycle
        # step. The supplier runs the new lifecycle engine, so reportability comes
        # from its lifecycle steps (onboarded, not draft / archived), not the
        # legacy workflow engine.
        from assets.constants import SupplierStatus
        from assets.lifecycles import SUPPLIER_LIFECYCLE

        supplier_states = list(SUPPLIER_LIFECYCLE.reportable_step_codes)
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
        """Second gate (RG-TC-08 / RG-TC-21 / RG-DOC-21).

        A report-backed entry needs a completed report. A policy-backed entry
        needs its document in a reportable step (active), still classified
        public, and holding a version in a reportable step (in force) : retiring
        the document, withdrawing its version or reclassifying it takes the
        entry off the public page with no action on the Trust Center side. The
        steps are read off the two lifecycles, never spelled out.
        """
        from assets.constants import DataClassification
        from core.lifecycle import reportable_states
        from documents.models import Policy, PolicyVersion
        from reports.constants import ReportStatus

        version_in_force = PolicyVersion.objects.filter(
            policy_id=models.OuterRef("policy_id"),
            workflow_state__in=list(reportable_states(PolicyVersion)),
        )
        return (
            super()
            .published()
            .filter(
                models.Q(report__isnull=True)
                | models.Q(report__status=ReportStatus.COMPLETED)
            )
            .filter(
                models.Q(policy__isnull=True)
                | models.Q(
                    models.Exists(version_in_force),
                    policy__workflow_state__in=list(reportable_states(Policy)),
                    policy__classification=DataClassification.PUBLIC,
                )
            )
        )
