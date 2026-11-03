# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""The REST surface of module 7 (README §5) : permissions, tenancy and the
RG-DOC rules as a client meets them."""
import datetime

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import Group, Permission
from accounts.tests.factories import UserFactory
from context.tests.factories import ScopeFactory
from documents.constants import (
    CAMPAIGN_CLOSED,
    CAMPAIGN_RUNNING,
    POLICY_ACTIVE,
    POLICY_RETIRED,
    VERSION_IN_FORCE,
    VERSION_IN_REVIEW,
    VERSION_SUPERSEDED,
    AcknowledgementChannel,
    AcknowledgementStatus,
)
from documents.models import AcknowledgementCampaign, Policy, PolicyAcknowledgement, PolicyVersion
from documents.tests.factories import (
    AcknowledgementCampaignFactory,
    PolicyFactory,
    PolicyVersionFactory,
    put_in_force,
)

pytestmark = pytest.mark.django_db

BASE = "/api/v1/documents"
PDF = b"%PDF-1.7\n%test\n"

READ = ("documents.policy.read",)
CONTRIBUTOR = ("documents.policy.read", "documents.policy.create", "documents.policy.update")
APPROVER = CONTRIBUTOR + ("documents.policy.approve",)
CAMPAIGN_ALL = tuple(
    f"documents.acknowledgement.{a}" for a in ("read", "create", "update", "approve", "delete")
)


def make_user(*codenames, scopes=()):
    """A user whose only group grants ``codenames`` within ``scopes``.

    A group with no allowed scope is unrestricted, so a test that wants a
    restricted user always passes at least one scope.
    """
    user = UserFactory()
    group = Group.objects.create(name=f"g-{user.pk}")
    group.permissions.set(Permission.objects.filter(codename__in=codenames))
    if scopes:
        group.allowed_scopes.set(scopes)
    group.users.add(user)
    return user


def api(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def data(response):
    """The payload, unwrapped from the success envelope.

    ``StandardJSONRenderer`` leaves a dict that already carries a ``status``
    key unwrapped, which every lifecycle entity does (``status`` is its step).
    """
    body = response.json()
    if isinstance(body, dict) and "data" in body and set(body) <= {"status", "data", "meta"}:
        return body["data"]
    return body


def error(response):
    return response.json()["error"]


@pytest.fixture
def superuser():
    return UserFactory(is_superuser=True)


@pytest.fixture
def scope():
    return ScopeFactory()


def scoped_policy(scope, **kwargs):
    policy = PolicyFactory(**kwargs)
    policy.scopes.add(scope)
    return policy


def running_campaign(version, users, scope=None):
    campaign = AcknowledgementCampaignFactory(policy_version=version)
    campaign.audience_users.set(users)
    if scope is not None:
        campaign.scopes.add(scope)
    campaign.transition_to(CAMPAIGN_RUNNING, version.policy.owner)
    return campaign


class TestRouting:
    def test_the_rest_api_is_mounted(self):
        assert reverse("documents-api:policy-list") == f"{BASE}/policies/"
        assert reverse("documents-api:policyversion-list") == f"{BASE}/policy-versions/"
        assert reverse("documents-api:acknowledgementcampaign-list") == f"{BASE}/acknowledgement-campaigns/"
        assert reverse("documents-api:policyacknowledgement-mine") == f"{BASE}/acknowledgements/mine/"

    def test_acknowledgement_rows_publish_no_write_route(self, superuser):
        row = running_campaign(put_in_force(PolicyVersionFactory()), [UserFactory()]).acknowledgements.get()
        client = api(superuser)
        assert client.post(f"{BASE}/acknowledgements/", {}, format="json").status_code == 405
        assert client.patch(f"{BASE}/acknowledgements/{row.pk}/", {}, format="json").status_code == 405
        assert client.delete(f"{BASE}/acknowledgements/{row.pk}/").status_code == 405


class TestPolicyEndpoints:
    def test_create_is_a_draft_with_read_only_stamps(self, superuser, scope):
        response = api(superuser).post(f"{BASE}/policies/", {
            "title": "Access control policy", "scopes": [str(scope.pk)],
            "status": POLICY_ACTIVE, "next_review_date": "2020-01-01",
        }, format="json")
        assert response.status_code == 201, response.content
        body = data(response)
        assert body["status"] == "draft"
        assert body["reference"].startswith("PLCY-")
        assert body["next_review_date"] is None
        assert body["version_in_force"] is None
        assert Policy.objects.get(pk=body["id"]).created_by == superuser

    def test_permissions_gate_each_verb(self, scope):
        policy = scoped_policy(scope)
        reader = make_user(*READ, scopes=[scope])
        assert api(reader).get(f"{BASE}/policies/").status_code == 200
        assert api(reader).post(f"{BASE}/policies/", {"title": "x"}, format="json").status_code == 403
        assert api(reader).patch(f"{BASE}/policies/{policy.pk}/", {"title": "y"}, format="json").status_code == 403
        nobody = make_user(scopes=[scope])
        assert api(nobody).get(f"{BASE}/policies/").status_code == 403

    def test_scope_tenancy_on_documents_and_versions(self, scope):
        other = ScopeFactory()
        mine = scoped_policy(scope)
        theirs = scoped_policy(other)
        theirs_version = PolicyVersionFactory(policy=theirs)
        reader = make_user(*READ, scopes=[scope])
        client = api(reader)
        ids = {row["id"] for row in data(client.get(f"{BASE}/policies/"))}
        assert ids == {str(mine.pk)}
        assert client.get(f"{BASE}/policies/{theirs.pk}/").status_code == 404
        assert client.get(f"{BASE}/policy-versions/{theirs_version.pk}/").status_code == 404
        assert str(theirs_version.pk) not in {row["id"] for row in data(client.get(f"{BASE}/policy-versions/"))}

    def test_filters(self, superuser):
        overdue = put_in_force(PolicyVersionFactory(policy=PolicyFactory(review_frequency_months=1))).policy
        Policy.objects.filter(pk=overdue.pk).update(next_review_date=timezone.localdate() - datetime.timedelta(days=1))
        PolicyFactory(document_type="charter")
        client = api(superuser)
        assert [r["id"] for r in data(client.get(f"{BASE}/policies/?overdue=true"))] == [str(overdue.pk)]
        assert len(data(client.get(f"{BASE}/policies/?type=charter"))) == 1
        assert [r["id"] for r in data(client.get(f"{BASE}/policies/?status={POLICY_ACTIVE}"))] == [str(overdue.pk)]

    def test_a_parent_cycle_is_a_400(self, superuser):
        parent = PolicyFactory()
        child = PolicyFactory(parent=parent)
        response = api(superuser).patch(f"{BASE}/policies/{parent.pk}/", {"parent": str(child.pk)}, format="json")
        assert response.status_code == 400
        assert "parent" in error(response)

    def test_record_review_needs_approve_and_an_active_document(self, scope):
        version = put_in_force(PolicyVersionFactory(policy=scoped_policy(scope)))
        draft = scoped_policy(scope)
        contributor = make_user(*CONTRIBUTOR, scopes=[scope])
        approver = make_user(*APPROVER, scopes=[scope])
        url = f"{BASE}/policies/{version.policy.pk}/record-review/"
        assert api(contributor).post(url, {"comment": "ok"}, format="json").status_code == 403
        response = api(approver).post(url, {"comment": "Still accurate."}, format="json")
        assert response.status_code == 200, response.content
        version.policy.refresh_from_db()
        assert version.policy.last_reviewed_by == approver
        refused = api(approver).post(f"{BASE}/policies/{draft.pk}/record-review/", {}, format="json")
        assert refused.status_code == 400
        assert "active" in error(refused)["detail"]

    def test_new_version_copies_the_version_in_force(self, scope):
        current = put_in_force(PolicyVersionFactory(policy=scoped_policy(scope), version_label="1.2"))
        contributor = make_user(*CONTRIBUTOR, scopes=[scope])
        url = f"{BASE}/policies/{current.policy.pk}/new-version/"
        assert api(contributor).post(url, {"bump": "sideways"}, format="json").status_code == 400
        response = api(contributor).post(url, {"bump": "major"}, format="json")
        assert response.status_code == 201, response.content
        body = data(response)
        assert body["version_label"] == "2.0"
        assert body["content"] == current.content
        assert body["change_summary"] == ""
        assert body["status"] == "draft"

    def test_new_version_of_a_retired_document_is_refused(self, superuser):
        version = put_in_force(PolicyVersionFactory())
        version.policy.transition_to(POLICY_RETIRED, superuser, comment="Replaced.")
        response = api(superuser).post(f"{BASE}/policies/{version.policy.pk}/new-version/", {}, format="json")
        assert response.status_code == 400

    def test_retire_through_the_transition_endpoint(self, superuser):
        version = put_in_force(PolicyVersionFactory())
        url = f"{BASE}/policies/{version.policy.pk}/transition/"
        assert api(superuser).post(url, {"target_state": POLICY_RETIRED}, format="json").status_code == 400
        response = api(superuser).post(url, {"target_state": POLICY_RETIRED, "comment": "Obsolete."}, format="json")
        assert response.status_code == 200, response.content
        assert data(response)["status"] == POLICY_RETIRED
        assert data(response)["version_in_force"] is None
        version.refresh_from_db()
        assert version.workflow_state == VERSION_SUPERSEDED


class TestVersionEndpoints:
    def test_no_payload_carries_the_pdf_bytes(self, superuser):
        version = PolicyVersionFactory()
        version.set_pdf(PDF, "policy.pdf")
        version.save()
        client = api(superuser)
        for url in (f"{BASE}/policy-versions/", f"{BASE}/policy-versions/{version.pk}/"):
            response = client.get(url)
            body = data(response)
            row = body[0] if isinstance(body, list) else body
            assert "file_content" not in row
            assert row["has_pdf"] is True
            assert row["pdf_sha256"] == version.file_sha256
            assert row["document_url"] == reverse("documents:policyversion-pdf", kwargs={"pk": version.pk})

    def test_a_version_cannot_be_attached_to_a_document_out_of_scope(self, scope):
        theirs = scoped_policy(ScopeFactory())
        contributor = make_user(*CONTRIBUTOR, scopes=[scope])
        response = api(contributor).post(f"{BASE}/policy-versions/", {
            "policy": str(theirs.pk), "version_label": "1.0", "content": "<p>x</p>",
        }, format="json")
        assert response.status_code == 400
        assert "policy" in error(response)

    def test_duplicate_label_is_a_400(self, superuser):
        version = PolicyVersionFactory(version_label="1.0")
        response = api(superuser).post(f"{BASE}/policy-versions/", {
            "policy": str(version.policy.pk), "version_label": "1.0",
        }, format="json")
        assert response.status_code == 400

    def test_rg_doc_02_a_submitted_version_refuses_a_content_patch(self, superuser):
        version = PolicyVersionFactory()
        client = api(superuser)
        url = f"{BASE}/policy-versions/{version.pk}/"
        assert client.patch(url, {"content": "<p>Draft edit.</p>"}, format="json").status_code == 200
        response = client.post(f"{url}transition/", {"target_state": VERSION_IN_REVIEW}, format="json")
        assert response.status_code == 200, response.content
        for field, value in (("content", "<p>Rewritten.</p>"), ("version_label", "9.9"), ("change_summary", "x")):
            refused = client.patch(url, {field: value}, format="json")
            assert refused.status_code == 400, (field, refused.status_code)
            assert field in error(refused)
        version.refresh_from_db()
        assert version.content == "<p>Draft edit.</p>"
        # The stored value, replayed, is not a change; nor is a non-frozen field.
        same = client.patch(url, {"content": version.content, "effective_from": str(timezone.localdate())}, format="json")
        assert same.status_code == 200, same.content

    def test_a_version_cannot_be_moved_to_another_document(self, superuser):
        version = PolicyVersionFactory()
        other = PolicyFactory()
        api(superuser).patch(f"{BASE}/policy-versions/{version.pk}/", {"policy": str(other.pk)}, format="json")
        version.refresh_from_db()
        assert version.policy_id != other.pk

    def test_submitting_without_content_shows_the_reason(self, superuser):
        version = PolicyVersionFactory(content="")
        response = api(superuser).post(
            f"{BASE}/policy-versions/{version.pk}/transition/", {"target_state": VERSION_IN_REVIEW}, format="json",
        )
        assert response.status_code == 400
        assert "content" in error(response)["detail"]

    def test_approval_needs_approve_and_stamps_the_caller(self, scope):
        first = put_in_force(PolicyVersionFactory(policy=scoped_policy(scope), version_label="1.0"))
        second = PolicyVersionFactory(policy=first.policy, version_label="1.1", change_summary="Stricter.")
        contributor = make_user(*CONTRIBUTOR, scopes=[scope])
        approver = make_user(*APPROVER, scopes=[scope])
        url = f"{BASE}/policy-versions/{second.pk}/transition/"
        assert api(contributor).post(url, {"target_state": VERSION_IN_REVIEW}, format="json").status_code == 200
        assert api(contributor).post(url, {"target_state": VERSION_IN_FORCE}, format="json").status_code == 403
        allowed = data(api(approver).get(url))["allowed_transitions"]
        assert VERSION_IN_FORCE in {t["target"] for t in allowed}
        response = api(approver).post(url, {"target_state": VERSION_IN_FORCE}, format="json")
        assert response.status_code == 200, response.content
        body = data(response)
        assert body["status"] == VERSION_IN_FORCE
        assert body["approved_by"] == str(approver.pk)
        first.refresh_from_db()
        assert first.workflow_state == VERSION_SUPERSEDED and first.superseded_by_id == second.pk
        assert PolicyVersion.objects.filter(policy=first.policy, workflow_state=VERSION_IN_FORCE).count() == 1

    def test_approval_stamps_are_not_writable(self, superuser):
        version = PolicyVersionFactory()
        api(superuser).patch(f"{BASE}/policy-versions/{version.pk}/", {
            "approved_by": str(superuser.pk), "approved_at": "2020-01-01T00:00:00Z", "status": VERSION_IN_FORCE,
        }, format="json")
        version.refresh_from_db()
        assert version.approved_by is None and version.approved_at is None
        assert version.workflow_state == "draft"

    def test_only_a_draft_version_is_deletable(self, superuser):
        version = put_in_force(PolicyVersionFactory())
        draft = PolicyVersionFactory(policy=version.policy, version_label="9.0")
        client = api(superuser)
        assert client.delete(f"{BASE}/policy-versions/{version.pk}/").status_code == 409
        assert client.delete(f"{BASE}/policy-versions/{draft.pk}/").status_code == 204

    def test_history(self, superuser):
        version = put_in_force(PolicyVersionFactory())
        response = api(superuser).get(f"{BASE}/policy-versions/{version.pk}/history/")
        assert response.status_code == 200
        assert data(response)["results"]


class TestCampaignEndpoints:
    def test_create_defaults_to_the_document_scopes(self, superuser, scope):
        version = put_in_force(PolicyVersionFactory(policy=scoped_policy(scope)))
        response = api(superuser).post(f"{BASE}/acknowledgement-campaigns/", {
            "name": "All staff", "policy_version": str(version.pk),
            "due_date": str(timezone.localdate() + datetime.timedelta(days=10)),
        }, format="json")
        assert response.status_code == 201, response.content
        assert data(response)["scopes"] == [str(scope.pk)]

    def test_launch_needs_approve_and_resolves_the_audience(self, scope):
        version = put_in_force(PolicyVersionFactory(policy=scoped_policy(scope)))
        campaign = AcknowledgementCampaignFactory(policy_version=version)
        campaign.scopes.add(scope)
        campaign.audience_users.set([UserFactory(), UserFactory()])
        url = f"{BASE}/acknowledgement-campaigns/{campaign.pk}/transition/"
        updater = make_user("documents.acknowledgement.read", "documents.acknowledgement.update", scopes=[scope])
        assert api(updater).post(url, {"target_state": CAMPAIGN_RUNNING}, format="json").status_code == 403
        owner = make_user(*CAMPAIGN_ALL, scopes=[scope])
        response = api(owner).post(url, {"target_state": CAMPAIGN_RUNNING}, format="json")
        assert response.status_code == 200, response.content
        assert data(response)["counts"]["pending"] == 2

    def test_launching_a_version_not_in_force_is_refused_with_its_reason(self, superuser):
        campaign = AcknowledgementCampaignFactory()
        campaign.audience_users.set([UserFactory()])
        response = api(superuser).post(
            f"{BASE}/acknowledgement-campaigns/{campaign.pk}/transition/", {"target_state": CAMPAIGN_RUNNING},
            format="json",
        )
        assert response.status_code == 400
        assert "in force" in error(response)["detail"]

    def test_a_launched_campaign_keeps_its_audience_and_version(self, superuser):
        campaign = running_campaign(put_in_force(PolicyVersionFactory()), [UserFactory()])
        url = f"{BASE}/acknowledgement-campaigns/{campaign.pk}/"
        client = api(superuser)
        refused = client.patch(url, {"audience_users": [str(UserFactory().pk)]}, format="json")
        assert refused.status_code == 400
        assert "audience_users" in error(refused)
        assert client.patch(url, {"statement": "Other."}, format="json").status_code == 400
        assert client.patch(url, {"name": "Renamed"}, format="json").status_code == 200

    def test_add_newcomers(self, superuser):
        first, newcomer = UserFactory(), UserFactory()
        campaign = running_campaign(put_in_force(PolicyVersionFactory()), [first])
        campaign.audience_users.add(newcomer)
        response = api(superuser).post(f"{BASE}/acknowledgement-campaigns/{campaign.pk}/add-newcomers/")
        assert response.status_code == 200, response.content
        assert data(response)["added"] == 1
        assert data(response)["added_user_ids"] == [str(newcomer.pk)]
        assert campaign.acknowledgements.count() == 2

    def test_add_newcomers_to_a_draft_is_refused(self, superuser):
        campaign = AcknowledgementCampaignFactory()
        response = api(superuser).post(f"{BASE}/acknowledgement-campaigns/{campaign.pk}/add-newcomers/")
        assert response.status_code == 400

    def test_superseding_the_version_closes_the_campaign(self, superuser):
        version = put_in_force(PolicyVersionFactory(version_label="1.0"))
        campaign = running_campaign(version, [UserFactory()])
        put_in_force(PolicyVersionFactory(policy=version.policy, version_label="1.1", change_summary="New."))
        body = data(api(superuser).get(f"{BASE}/acknowledgement-campaigns/{campaign.pk}/"))
        assert body["status"] == CAMPAIGN_CLOSED
        assert body["counts"]["expired"] == 1


class TestAcknowledgementEndpoints:
    def test_the_addressee_sees_their_rows_without_any_permission(self, scope):
        addressee = make_user(scopes=[ScopeFactory()])
        version = put_in_force(PolicyVersionFactory(policy=scoped_policy(scope)))
        campaign = running_campaign(version, [addressee, UserFactory()], scope)
        client = api(addressee)
        rows = data(client.get(f"{BASE}/acknowledgements/"))
        assert [r["user"] for r in rows] == [str(addressee.pk)]
        mine = data(client.get(f"{BASE}/acknowledgements/mine/"))
        assert len(mine) == 1 and mine[0]["status"] == AcknowledgementStatus.PENDING
        assert mine[0]["statement_to_confirm"] == campaign.statement_for()
        # Their own row is readable; the campaign itself is not.
        assert client.get(f"{BASE}/acknowledgement-campaigns/{campaign.pk}/").status_code == 403

    def test_campaign_readers_see_the_rows_of_their_scopes(self, scope):
        version = put_in_force(PolicyVersionFactory(policy=scoped_policy(scope)))
        running_campaign(version, [UserFactory(), UserFactory()], scope)
        out = put_in_force(PolicyVersionFactory(policy=scoped_policy(ScopeFactory())))
        running_campaign(out, [UserFactory()])
        reader = make_user("documents.acknowledgement.read", scopes=[scope])
        assert len(data(api(reader).get(f"{BASE}/acknowledgements/"))) == 2

    def test_mine_lists_pending_first(self):
        user = UserFactory()
        done = running_campaign(put_in_force(PolicyVersionFactory()), [user]).acknowledgements.get()
        done.acknowledge(user)
        pending = running_campaign(put_in_force(PolicyVersionFactory()), [user]).acknowledgements.get()
        rows = data(api(user).get(f"{BASE}/acknowledgements/mine/"))
        assert [r["id"] for r in rows] == [str(pending.pk), str(done.pk)]

    def test_rg_doc_17_only_the_addressee_acknowledges(self, superuser):
        addressee, colleague = UserFactory(), UserFactory()
        campaign = running_campaign(put_in_force(PolicyVersionFactory()), [addressee, colleague])
        row = campaign.acknowledgements.get(user=addressee)
        url = f"{BASE}/acknowledgements/{row.pk}/acknowledge/"
        # An administrator sees the row, and is still refused.
        refused = api(superuser).post(url)
        assert refused.status_code == 400
        assert "addressee" in error(refused)["detail"]
        # A colleague does not even see it.
        assert api(colleague).post(url).status_code == 404
        response = api(addressee).post(url)
        assert response.status_code == 200, response.content
        body = data(response)
        assert body["status"] == AcknowledgementStatus.ACKNOWLEDGED
        assert body["channel"] == AcknowledgementChannel.API
        assert body["statement"] == campaign.statement_for()
        assert body["acknowledged_at"]
        # Write-once : a second acknowledgement is refused.
        assert api(addressee).post(url).status_code == 400

    def test_excuse_needs_update_and_a_reason(self, scope):
        version = put_in_force(PolicyVersionFactory(policy=scoped_policy(scope)))
        leaver = UserFactory()
        row = running_campaign(version, [leaver], scope).acknowledgements.get()
        url = f"{BASE}/acknowledgements/{row.pk}/excuse/"
        reader = make_user("documents.acknowledgement.read", scopes=[scope])
        assert api(reader).post(url, {"reason": "Left."}, format="json").status_code == 403
        owner = make_user(*CAMPAIGN_ALL, scopes=[scope])
        assert api(owner).post(url, {"reason": "  "}, format="json").status_code == 400
        response = api(owner).post(url, {"reason": "Left the company."}, format="json")
        assert response.status_code == 200, response.content
        assert data(response)["status"] == AcknowledgementStatus.EXCUSED
        assert data(response)["excused_by"] == str(owner.pk)
        row.refresh_from_db()
        assert row.excuse_reason == "Left the company."

    def test_excusing_outside_ones_scopes_is_refused(self, scope):
        owner = make_user(*CAMPAIGN_ALL, scopes=[scope])
        version = put_in_force(PolicyVersionFactory(policy=scoped_policy(ScopeFactory())))
        row = running_campaign(version, [owner]).acknowledgements.get()
        response = api(owner).post(f"{BASE}/acknowledgements/{row.pk}/excuse/", {"reason": "Me."}, format="json")
        assert response.status_code == 403
        assert PolicyAcknowledgement.objects.get(pk=row.pk).status == AcknowledgementStatus.PENDING



def test_every_campaign_counts_shape(superuser):
    campaign = running_campaign(put_in_force(PolicyVersionFactory()), [UserFactory()])
    body = data(api(superuser).get(f"{BASE}/acknowledgement-campaigns/"))
    assert body[0]["id"] == str(campaign.pk)
    assert set(body[0]["counts"]) == {"pending", "acknowledged", "excused", "expired", "total"}
    assert AcknowledgementCampaign.objects.count() == 1
