# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""The RG-DOC rules held by the models (docs/specs/m7-documents/README.md §2)."""
import datetime

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from accounts.tests.factories import GroupFactory, UserFactory
from context.models import Role
from core.lifecycle import DomainRefusalError, LifecycleError
from core.models import LifecycleEvent
from documents.constants import (
    CAMPAIGN_CLOSED,
    CAMPAIGN_RUNNING,
    POLICY_ACTIVE,
    POLICY_RETIRED,
    VERSION_IN_FORCE,
    VERSION_IN_REVIEW,
    VERSION_SUPERSEDED,
    AcknowledgementStatus,
)
from documents.models import AcknowledgementCampaign, Policy, PolicyAcknowledgement, PolicyVersion
from documents.models.policy import add_months
from documents.models.policy_version import next_version_label
from documents.tests.factories import (
    AcknowledgementCampaignFactory,
    PolicyFactory,
    PolicyVersionFactory,
    put_in_force,
)

pytestmark = pytest.mark.django_db

PDF = b"%PDF-1.7\n%test\n"


class TestLifecycles:
    """An un-imported lifecycle silently falls back to the core one."""

    def test_each_model_runs_its_own_lifecycle(self):
        assert Policy().get_lifecycle().name == "policy"
        assert PolicyVersion().get_lifecycle().name == "policy_version"
        assert AcknowledgementCampaign().get_lifecycle().name == "acknowledgement_campaign"

    def test_no_restore_edge_out_of_archived(self):
        for model in (Policy, PolicyVersion, AcknowledgementCampaign):
            lifecycle = model().get_lifecycle()
            assert not [t for t in lifecycle.transitions if t.source == "archived"]
            assert all(t.permission_action for t in lifecycle.transitions)


class TestVersionInForce:
    def test_first_version_activates_the_document_and_stamps_approval(self):
        version = PolicyVersionFactory()
        approver = UserFactory()
        version.transition_to(VERSION_IN_REVIEW, approver)
        version.transition_to(VERSION_IN_FORCE, approver)
        version.refresh_from_db()
        assert version.approved_by == approver and version.approved_at is not None
        assert version.effective_from == timezone.localdate()
        version.policy.refresh_from_db()
        assert version.policy.workflow_state == POLICY_ACTIVE
        assert version.policy.next_review_date == add_months(timezone.localdate(), 12)

    def test_rg_doc_01_putting_a_version_in_force_supersedes_the_previous(self):
        first = put_in_force(PolicyVersionFactory(version_label="1.0"))
        second = PolicyVersionFactory(policy=first.policy, version_label="1.1", change_summary="Tighter rules.")
        put_in_force(second)
        first.refresh_from_db()
        assert first.workflow_state == VERSION_SUPERSEDED
        assert first.superseded_by == second and first.superseded_at is not None
        assert first.policy.versions.filter(workflow_state=VERSION_IN_FORCE).count() == 1
        event = LifecycleEvent.objects.filter(object_id=str(first.pk), to_step=VERSION_SUPERSEDED).first()
        assert event is not None and second.reference in (event.comment or "")

    def test_rg_doc_01_database_constraint(self):
        first = put_in_force(PolicyVersionFactory(version_label="1.0"))
        other = PolicyVersionFactory(policy=first.policy, version_label="2.0")
        with pytest.raises(IntegrityError), transaction.atomic():
            PolicyVersion.objects.filter(pk=other.pk).update(workflow_state=VERSION_IN_FORCE)


class TestFrozenContent:
    def test_rg_doc_02_submitted_content_is_frozen(self):
        version = PolicyVersionFactory()
        version.transition_to(VERSION_IN_REVIEW, UserFactory())
        version.content = "<p>Changed after submission</p>"
        with pytest.raises(ValidationError):
            version.save()

    def test_rg_doc_02_draft_is_editable_and_sanitized(self):
        version = PolicyVersionFactory()
        version.content = '<p onclick="x()">Hello</p><script>alert(1)</script>'
        version.save()
        version.refresh_from_db()
        assert "script" not in version.content and "onclick" not in version.content

    def test_rg_doc_03_a_version_needs_content(self):
        version = PolicyVersionFactory(content="")
        with pytest.raises(DomainRefusalError):
            version.transition_to(VERSION_IN_REVIEW, UserFactory())
        version.set_pdf(PDF, "policy.pdf")
        version.save()
        version.transition_to(VERSION_IN_REVIEW, UserFactory())

    def test_rg_doc_04_pdf_rules_and_sha256(self):
        version = PolicyVersionFactory()
        with pytest.raises(ValidationError):
            version.set_pdf(b"not a pdf", "policy.pdf")
        with pytest.raises(ValidationError):
            version.set_pdf(PDF, "policy.docx")
        version.set_pdf(PDF, "policy.pdf")
        assert len(version.file_sha256) == 64

    def test_rg_doc_06_change_summary_required_from_the_second_version(self):
        first = put_in_force(PolicyVersionFactory(version_label="1.0", change_summary=""))
        second = PolicyVersionFactory(policy=first.policy, version_label="1.1", change_summary="")
        with pytest.raises(DomainRefusalError):
            second.transition_to(VERSION_IN_REVIEW, UserFactory())

    def test_rg_doc_07_no_future_effective_date(self):
        version = PolicyVersionFactory(effective_from=timezone.localdate() + datetime.timedelta(days=3))
        version.transition_to(VERSION_IN_REVIEW, UserFactory())
        with pytest.raises(DomainRefusalError):
            version.transition_to(VERSION_IN_FORCE, UserFactory())


class TestNewVersion:
    @pytest.mark.parametrize("current,bump,expected", [
        (None, "minor", "1.0"), ("1.2", "minor", "1.3"), ("1.2", "major", "2.0"), ("3", "minor", "3.1"),
    ])
    def test_next_label(self, current, bump, expected):
        assert next_version_label(current, bump) == expected

    def test_rg_doc_05_new_version_copies_the_version_in_force(self):
        current = PolicyVersionFactory(version_label="1.0")
        current.set_pdf(PDF, "v1.pdf")
        current.save()
        put_in_force(current)
        draft = current.policy.new_version(UserFactory(), bump="major")
        assert draft.version_label == "2.0"
        assert draft.content == current.content and draft.file_sha256 == current.file_sha256
        assert draft.change_summary == "" and draft.workflow_state == "draft"


class TestDocument:
    def test_rg_doc_09_activation_needs_a_version_in_force(self):
        policy = PolicyFactory()
        with pytest.raises(LifecycleError):
            policy.transition_to(POLICY_ACTIVE, UserFactory())

    def test_rg_doc_09_retiring_supersedes_and_closes_campaigns(self):
        version = put_in_force(PolicyVersionFactory())
        campaign = AcknowledgementCampaignFactory(policy_version=version)
        campaign.audience_users.add(UserFactory())
        campaign.transition_to(CAMPAIGN_RUNNING, UserFactory())
        policy = version.policy
        policy.refresh_from_db()
        policy.transition_to(POLICY_RETIRED, UserFactory(), comment="Replaced by the group policy")
        version.refresh_from_db()
        campaign.refresh_from_db()
        assert version.workflow_state == VERSION_SUPERSEDED
        assert campaign.workflow_state == CAMPAIGN_CLOSED
        assert campaign.acknowledgements.get().status == AcknowledgementStatus.EXPIRED
        policy.refresh_from_db()
        assert policy.next_review_date is None

    def test_rg_doc_10_no_cycle(self):
        parent = PolicyFactory()
        child = PolicyFactory(parent=parent)
        parent.parent = child
        with pytest.raises(ValidationError):
            parent.full_clean()

    def test_rg_doc_11_and_13_review_date(self):
        version = put_in_force(PolicyVersionFactory(effective_from=datetime.date(2025, 1, 31)))
        policy = version.policy
        policy.refresh_from_db()
        policy.last_reviewed_at = None
        policy.save()
        assert policy.next_review_date == datetime.date(2026, 1, 31)
        assert policy.is_review_overdue
        policy.record_review(UserFactory(), "Still accurate")
        assert policy.next_review_date == add_months(timezone.localdate(), 12)
        assert not policy.is_review_overdue
        policy.next_review_override = datetime.date(2030, 6, 1)
        policy.save()
        assert policy.next_review_date == datetime.date(2030, 6, 1)


class TestCampaign:
    def _running(self, users=1):
        version = put_in_force(PolicyVersionFactory())
        campaign = AcknowledgementCampaignFactory(policy_version=version)
        people = [UserFactory() for _ in range(users)]
        campaign.audience_users.add(*people)
        campaign.transition_to(CAMPAIGN_RUNNING, UserFactory())
        return campaign, people

    def test_rg_doc_14_only_a_version_in_force(self):
        campaign = AcknowledgementCampaignFactory()
        campaign.audience_users.add(UserFactory())
        with pytest.raises(DomainRefusalError):
            campaign.transition_to(CAMPAIGN_RUNNING, UserFactory())

    def test_rg_doc_15_audience_resolved_once_from_users_groups_roles(self):
        version = put_in_force(PolicyVersionFactory())
        campaign = AcknowledgementCampaignFactory(policy_version=version)
        named, member, assignee, inactive = UserFactory(), UserFactory(), UserFactory(), UserFactory(is_active=False)
        group = GroupFactory()
        group.users.add(member, named, inactive)
        role = Role.objects.create(name="DPO", type="governance")
        role.assigned_users.add(assignee)
        campaign.audience_users.add(named)
        campaign.audience_groups.add(group)
        campaign.audience_roles.add(role)
        campaign.transition_to(CAMPAIGN_RUNNING, UserFactory())
        assert set(campaign.acknowledgements.values_list("user_id", flat=True)) == {named.pk, member.pk, assignee.pk}
        late = UserFactory()
        group.users.add(late)
        assert campaign.acknowledgements.count() == 3
        added = campaign.add_newcomers(UserFactory())
        assert [r.user_id for r in added] == [late.pk] and campaign.acknowledgements.count() == 4

    def test_rg_doc_16_17_only_the_addressee_and_only_once(self):
        campaign, (person,) = self._running()
        row = campaign.acknowledgements.get()
        with pytest.raises(DomainRefusalError):
            row.acknowledge(UserFactory(is_superuser=True))
        row.acknowledge(person)
        row.refresh_from_db()
        assert row.status == AcknowledgementStatus.ACKNOWLEDGED
        assert campaign.policy_version.policy.title in row.statement
        with pytest.raises(DomainRefusalError):
            row.acknowledge(person)
        row.excuse_reason = "tampered"
        with pytest.raises(ValidationError):
            row.save()
        with pytest.raises(ValidationError):
            row.delete()

    def test_rg_doc_18_superseding_the_version_closes_the_campaign(self):
        campaign, _ = self._running()
        version = campaign.policy_version
        put_in_force(PolicyVersionFactory(policy=version.policy, version_label="9.0", change_summary="New"))
        campaign.refresh_from_db()
        assert campaign.workflow_state == CAMPAIGN_CLOSED
        assert campaign.acknowledgements.get().status == AcknowledgementStatus.EXPIRED

    def test_rg_doc_19_rate_excludes_excused_rows(self):
        campaign, (a, b, c) = self._running(users=3)
        rows = {r.user_id: r for r in campaign.acknowledgements.all()}
        rows[a.pk].acknowledge(a)
        rows[b.pk].excuse(UserFactory(), "Left the company")
        assert campaign.completion_rate == 50
        with pytest.raises(DomainRefusalError):
            rows[c.pk].excuse(UserFactory(), "  ")

    def test_launch_notifies_every_addressee(self):
        from accounts.models import Notification

        campaign, people = self._running(users=2)
        assert Notification.objects.filter(recipient__in=people, notification_type="acknowledgement_requested").count() == 2

    def test_acknowledgement_rows_cannot_be_created_twice(self):
        campaign, (person,) = self._running()
        with pytest.raises(IntegrityError), transaction.atomic():
            PolicyAcknowledgement.objects.create(campaign=campaign, user=person)


class TestIntegrationFindings:
    """Gaps found while wiring the API and MCP surfaces."""

    def test_acknowledgement_rows_have_a_creation_history(self):
        version = put_in_force(PolicyVersionFactory())
        campaign = AcknowledgementCampaignFactory(policy_version=version)
        campaign.audience_users.add(UserFactory())
        campaign.transition_to(CAMPAIGN_RUNNING, UserFactory())
        row = campaign.acknowledgements.get()
        assert row.history.filter(history_type="+").exists()

    def test_retired_document_refuses_a_new_version(self):
        version = put_in_force(PolicyVersionFactory())
        policy = version.policy
        policy.refresh_from_db()
        policy.transition_to(POLICY_RETIRED, UserFactory(), comment="Withdrawn")
        with pytest.raises(DomainRefusalError):
            policy.new_version(UserFactory())

    def test_effective_date_of_an_approved_version_is_frozen(self):
        version = put_in_force(PolicyVersionFactory())
        version.effective_from = datetime.date(2020, 1, 1)
        with pytest.raises(ValidationError):
            version.save()
