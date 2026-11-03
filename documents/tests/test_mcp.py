# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""The MCP surface of module 7 (README §6) : the same RG-DOC rules as the web
form and the REST API, with the MCP client acting as the authenticated user."""
import datetime

import pytest
from django.utils import timezone

from accounts.tests.factories import UserFactory
from context.tests.factories import ScopeFactory
from documents.constants import (
    CAMPAIGN_RUNNING,
    POLICY_ACTIVE,
    POLICY_RETIRED,
    VERSION_IN_FORCE,
    VERSION_IN_REVIEW,
    VERSION_SUPERSEDED,
    AcknowledgementChannel,
    AcknowledgementStatus,
)
from documents.models import AcknowledgementCampaign, Policy, PolicyVersion
from documents.tests.factories import (
    AcknowledgementCampaignFactory,
    PolicyFactory,
    PolicyVersionFactory,
    put_in_force,
)
from documents.tests.test_api import APPROVER, CAMPAIGN_ALL, CONTRIBUTOR, READ, make_user, scoped_policy

pytestmark = pytest.mark.django_db


@pytest.fixture(scope="module")
def server():
    from mcp.server import McpServer
    from mcp.tools import register_all_tools

    instance = McpServer()
    register_all_tools(instance)
    return instance


@pytest.fixture
def call(server):
    def _call(tool_name, user, /, **arguments):
        return server.get_tool(tool_name)["handler"](user, arguments)
    return _call


@pytest.fixture
def superuser():
    return UserFactory(is_superuser=True)


def is_error(result):
    return isinstance(result, dict) and result.get("isError") is True


def error_text(result):
    return result["content"][0]["text"]


def running_campaign(version, users):
    campaign = AcknowledgementCampaignFactory(policy_version=version)
    campaign.audience_users.set(users)
    campaign.transition_to(CAMPAIGN_RUNNING, version.policy.owner)
    return campaign


class TestRegistry:
    EXPECTED = {
        "list_policys", "get_policy", "create_policy", "batch_create_policys", "update_policy",
        "delete_policy", "transition_policy", "policy_allowed_transitions", "get_policy_history",
        "list_policy_versions", "get_policy_version", "create_policy_version",
        "batch_create_policy_versions", "update_policy_version", "delete_policy_version",
        "transition_policy_version", "policy_version_allowed_transitions", "get_policy_version_history",
        "list_acknowledgement_campaigns", "get_acknowledgement_campaign", "create_acknowledgement_campaign",
        "batch_create_acknowledgement_campaigns", "update_acknowledgement_campaign",
        "delete_acknowledgement_campaign", "transition_acknowledgement_campaign",
        "acknowledgement_campaign_allowed_transitions", "get_acknowledgement_campaign_history",
        "new_policy_version", "record_policy_review", "get_policy_in_force",
        "list_my_pending_acknowledgements", "acknowledge_policy_version", "list_policy_acknowledgements",
        "excuse_policy_acknowledgement", "add_campaign_newcomers", "get_campaign_progress",
    }

    def test_every_documents_tool_is_registered(self, server):
        names = {tool["name"] for tool in server.iter_tools()}
        assert self.EXPECTED <= names, sorted(self.EXPECTED - names)

    def test_every_tool_and_parameter_is_described(self, server):
        for name in self.EXPECTED:
            tool = server.get_tool(name)
            assert tool["description"].strip(), name
            for param, schema in tool["inputSchema"].get("properties", {}).items():
                assert schema.get("description"), (name, param)

    def test_no_tool_returns_the_pdf_bytes(self, call, superuser):
        version = PolicyVersionFactory()
        version.set_pdf(b"%PDF-1.7\n%x\n", "p.pdf")
        version.save()
        for name in ("get_policy_version", "list_policy_versions"):
            result = call(name, superuser, id=str(version.pk))
            assert "file_content" not in str(result)
        detail = call("get_policy_version", superuser, id=str(version.pk))
        assert detail["has_pdf"] is True and detail["pdf_sha256"] == version.file_sha256

    def test_help_has_a_documents_topic(self, call, superuser):
        assert "PLVR" in call("help", superuser)
        topic = call("help", superuser, topic="documents")
        assert "RG-DOC-02" in topic and "acknowledge_policy_version" in topic
        assert "documents" in call("help", superuser, topic="nope")


class TestPermissionsAndScopes:
    def test_tools_require_their_permission(self, call):
        nobody = make_user(scopes=[ScopeFactory()])
        assert "documents.policy.read" in error_text(call("list_policys", nobody))
        assert "documents.policy.create" in error_text(call("create_policy", nobody, title="x"))
        assert "documents.acknowledgement.read" in error_text(
            call("get_campaign_progress", nobody, campaign_id=str(AcknowledgementCampaignFactory().pk))
        )

    def test_lists_are_scope_filtered_including_versions(self, call):
        scope, other = ScopeFactory(), ScopeFactory()
        mine = scoped_policy(scope)
        theirs = scoped_policy(other)
        PolicyVersionFactory(policy=mine)
        theirs_version = PolicyVersionFactory(policy=theirs)
        reader = make_user(*READ, scopes=[scope])
        assert [i["id"] for i in call("list_policys", reader)["items"]] == [str(mine.pk)]
        versions = call("list_policy_versions", reader)["items"]
        assert [v["policy_id"] for v in versions] == [str(mine.pk)]
        assert is_error(call("get_policy_version", reader, id=str(theirs_version.pk)))
        assert is_error(call("get_policy_in_force", reader, policy_id=str(theirs.pk)))

    def test_a_version_cannot_be_created_under_a_document_out_of_scope(self, call):
        theirs = scoped_policy(ScopeFactory())
        contributor = make_user(*CONTRIBUTOR, scopes=[ScopeFactory()])
        result = call("create_policy_version", contributor, policy_id=str(theirs.pk), version_label="1.0")
        assert is_error(result)
        assert not PolicyVersion.objects.filter(policy=theirs).exists()
        batch = call("batch_create_policy_versions", contributor, items=[{"policy_id": str(theirs.pk), "version_label": "1.0"}])
        assert is_error(batch)


class TestDocumentTools:
    def test_create_policy_and_first_version_through_mcp(self, call, superuser):
        scope = ScopeFactory()
        created = call("create_policy", superuser, title="Backup procedure", document_type="procedure",
                       scope_ids=[str(scope.pk)])
        assert created["reference"].startswith("PLCY-")
        assert created["workflow_state"] == "draft"
        draft = call("new_policy_version", superuser, policy_id=created["id"])
        assert draft["version_label"] == "1.0" and draft["workflow_state"] == "draft"
        assert not is_error(call("update_policy_version", superuser, id=draft["id"], content="<p>Daily backups.</p>"))
        for target in (VERSION_IN_REVIEW, VERSION_IN_FORCE):
            result = call("transition_policy_version", superuser, id=draft["id"], target_state=target)
            assert not is_error(result), result
        in_force = call("get_policy_in_force", superuser, policy_id=created["id"])
        assert in_force["policy_state"] == POLICY_ACTIVE
        assert in_force["version_in_force"]["id"] == draft["id"]
        assert in_force["version_in_force"]["content"] == "<p>Daily backups.</p>"
        assert in_force["version_in_force"]["approved_by_id"] == str(superuser.pk)

    def test_rg_doc_02_update_refuses_a_frozen_field(self, call, superuser):
        version = put_in_force(PolicyVersionFactory())
        for field, value in (("content", "<p>Rewritten.</p>"), ("version_label", "9.9"), ("change_summary", "x")):
            result = call("update_policy_version", superuser, id=str(version.pk), **{field: value})
            assert is_error(result), field
            assert "RG-DOC-02" in error_text(result)
        version.refresh_from_db()
        assert version.content == PolicyVersionFactory._meta.declarations["content"]

    def test_a_version_cannot_be_moved(self, call, superuser):
        version = PolicyVersionFactory()
        result = call("update_policy_version", superuser, id=str(version.pk), policy_id=str(PolicyFactory().pk))
        assert is_error(result)

    def test_transition_refusals_carry_the_reason_and_the_permission(self, call):
        scope = ScopeFactory()
        version = PolicyVersionFactory(policy=scoped_policy(scope), content="")
        contributor = make_user(*CONTRIBUTOR, scopes=[scope])
        refused = call("transition_policy_version", contributor, id=str(version.pk), target_state=VERSION_IN_REVIEW)
        assert is_error(refused) and "content" in error_text(refused)
        version.content = "<p>Text.</p>"
        version.save()
        assert not is_error(call("transition_policy_version", contributor, id=str(version.pk), target_state=VERSION_IN_REVIEW))
        denied = call("transition_policy_version", contributor, id=str(version.pk), target_state=VERSION_IN_FORCE)
        assert is_error(denied)
        approver = make_user(*APPROVER, scopes=[scope])
        assert not is_error(call("transition_policy_version", approver, id=str(version.pk), target_state=VERSION_IN_FORCE))

    def test_new_version_supersedes_on_approval(self, call, superuser):
        first = put_in_force(PolicyVersionFactory(version_label="1.4"))
        draft = call("new_policy_version", superuser, policy_id=str(first.policy.pk), bump="minor")
        assert draft["version_label"] == "1.5" and draft["content"] == first.content
        assert is_error(call("transition_policy_version", superuser, id=draft["id"], target_state=VERSION_IN_REVIEW))
        call("update_policy_version", superuser, id=draft["id"], change_summary="Clarified scope.")
        call("transition_policy_version", superuser, id=draft["id"], target_state=VERSION_IN_REVIEW)
        call("transition_policy_version", superuser, id=draft["id"], target_state=VERSION_IN_FORCE)
        first.refresh_from_db()
        assert first.workflow_state == VERSION_SUPERSEDED

    def test_new_version_refusals(self, call, superuser):
        version = put_in_force(PolicyVersionFactory())
        assert is_error(call("new_policy_version", superuser, policy_id=str(version.policy.pk), bump="huge"))
        version.policy.transition_to(POLICY_RETIRED, superuser, comment="Obsolete.")
        assert is_error(call("new_policy_version", superuser, policy_id=str(version.policy.pk)))

    def test_record_policy_review(self, call, superuser):
        version = put_in_force(PolicyVersionFactory())
        result = call("record_policy_review", superuser, policy_id=str(version.policy.pk), comment="Still accurate.")
        assert not is_error(result), result
        assert result["last_reviewed_by_id"] == str(superuser.pk)
        refused = call("record_policy_review", superuser, policy_id=str(PolicyFactory().pk))
        assert is_error(refused) and "active" in error_text(refused)
        contributor = make_user(*CONTRIBUTOR)
        assert "documents.policy.approve" in error_text(
            call("record_policy_review", contributor, policy_id=str(version.policy.pk))
        )


class TestCampaignTools:
    def test_create_defaults_scopes_and_launch(self, call, superuser):
        scope = ScopeFactory()
        version = put_in_force(PolicyVersionFactory(policy=scoped_policy(scope)))
        addressee = UserFactory()
        created = call(
            "create_acknowledgement_campaign", superuser, name="All staff", policy_version_id=str(version.pk),
            due_date=str(timezone.localdate() + datetime.timedelta(days=7)), audience_user_ids=[str(addressee.pk)],
        )
        assert not is_error(created), created
        assert created["scopes"] == [str(scope.pk)]
        launched = call("transition_acknowledgement_campaign", superuser, id=created["id"], target_state=CAMPAIGN_RUNNING)
        assert not is_error(launched), launched
        progress = call("get_campaign_progress", superuser, campaign_id=created["id"])
        assert progress["counts"]["pending"] == 1 and progress["completion_rate"] == 0

    def test_a_launched_campaign_keeps_its_audience(self, call, superuser):
        campaign = running_campaign(put_in_force(PolicyVersionFactory()), [UserFactory()])
        refused = call("update_acknowledgement_campaign", superuser, id=str(campaign.pk),
                       audience_user_ids=[str(UserFactory().pk)])
        assert is_error(refused)
        assert not is_error(call("update_acknowledgement_campaign", superuser, id=str(campaign.pk), name="Renamed"))
        assert AcknowledgementCampaign.objects.get(pk=campaign.pk).name == "Renamed"

    def test_add_newcomers_and_excuse(self, call, superuser):
        first, newcomer = UserFactory(), UserFactory()
        campaign = running_campaign(put_in_force(PolicyVersionFactory()), [first])
        campaign.audience_users.add(newcomer)
        result = call("add_campaign_newcomers", superuser, campaign_id=str(campaign.pk))
        assert result["added"] == 1
        row = campaign.acknowledgements.get(user=first)
        assert is_error(call("excuse_policy_acknowledgement", superuser, acknowledgement_id=str(row.pk), reason=""))
        excused = call("excuse_policy_acknowledgement", superuser, acknowledgement_id=str(row.pk), reason="Leaver.")
        assert excused["status"] == AcknowledgementStatus.EXCUSED
        progress = call("get_campaign_progress", superuser, campaign_id=str(campaign.pk))
        assert progress["counts"]["excused"] == 1 and progress["counts"]["pending"] == 1

    def test_campaign_progress_is_scope_checked(self, call):
        scope = ScopeFactory()
        version = put_in_force(PolicyVersionFactory(policy=scoped_policy(ScopeFactory())))
        campaign = running_campaign(version, [UserFactory()])
        campaign.scopes.set(version.policy.scopes.all())
        reader = make_user(*CAMPAIGN_ALL, scopes=[scope])
        assert is_error(call("get_campaign_progress", reader, campaign_id=str(campaign.pk)))


class TestAcknowledgementTools:
    def test_the_addressee_lists_and_acknowledges_without_any_permission(self, call):
        addressee = make_user(scopes=[ScopeFactory()])
        campaign = running_campaign(put_in_force(PolicyVersionFactory()), [addressee])
        pending = call("list_my_pending_acknowledgements", addressee)
        assert pending["total"] == 1
        item = pending["items"][0]
        assert item["statement_to_confirm"] == campaign.statement_for()
        done = call("acknowledge_policy_version", addressee, acknowledgement_id=item["id"])
        assert not is_error(done), done
        assert done["status"] == AcknowledgementStatus.ACKNOWLEDGED
        assert done["channel"] == AcknowledgementChannel.MCP
        assert call("list_my_pending_acknowledgements", addressee)["total"] == 0
        again = call("acknowledge_policy_version", addressee, acknowledgement_id=item["id"])
        assert is_error(again)

    def test_rg_doc_17_nobody_acknowledges_for_someone_else(self, call, superuser):
        addressee, colleague = UserFactory(), UserFactory()
        campaign = running_campaign(put_in_force(PolicyVersionFactory()), [addressee, colleague])
        row = campaign.acknowledgements.get(user=addressee)
        refused = call("acknowledge_policy_version", superuser, acknowledgement_id=str(row.pk))
        assert is_error(refused) and "addressee" in error_text(refused)
        assert is_error(call("acknowledge_policy_version", colleague, acknowledgement_id=str(row.pk)))
        row.refresh_from_db()
        assert row.status == AcknowledgementStatus.PENDING

    def test_list_policy_acknowledgements_scopes(self, call):
        scope = ScopeFactory()
        version = put_in_force(PolicyVersionFactory(policy=scoped_policy(scope)))
        running_campaign(version, [UserFactory(), UserFactory()])
        outsider = UserFactory()
        running_campaign(put_in_force(PolicyVersionFactory(policy=scoped_policy(ScopeFactory()))), [outsider])
        reader = make_user("documents.acknowledgement.read", scopes=[scope])
        assert call("list_policy_acknowledgements", reader)["total"] == 2
        assert call("list_policy_acknowledgements", outsider)["total"] == 1


def test_policy_list_reports_the_version_in_force(call, superuser):
    version = put_in_force(PolicyVersionFactory())
    items = call("list_policys", superuser, workflow_state=POLICY_ACTIVE)["items"]
    assert items[0]["version_in_force"] == str(version.pk)
    assert Policy.objects.count() == 1
