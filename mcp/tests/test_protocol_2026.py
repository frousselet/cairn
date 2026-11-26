# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""The MCP 2026-07-28 revision : discovery, per-request metadata, headers,
elicitation (multi round-trip requests) and the tasks extension."""

import json
from datetime import timedelta

import pytest
from django.utils import timezone

from accounts.tests.factories import GroupFactory, PermissionFactory, UserFactory
from context.models import Tag
from context.tests.factories import ScopeFactory
from mcp import tasks
from mcp.models import McpTask, McpTaskStatus, OAuthAccessToken, OAuthApplication
from mcp.models.oauth import _generate_client_secret
from mcp.server import MODERN_PROTOCOL_VERSION, PROTOCOL_VERSION, TASKS_EXTENSION, McpServer
from mcp.tools import register_all_tools

pytestmark = pytest.mark.django_db

ENDPOINT = "/api/v1/mcp"


def _meta(capabilities=None):
    return {
        "io.modelcontextprotocol/protocolVersion": MODERN_PROTOCOL_VERSION,
        "io.modelcontextprotocol/clientInfo": {"name": "test", "version": "1.0"},
        "io.modelcontextprotocol/clientCapabilities": capabilities if capabilities is not None else {},
    }


FORM = {"elicitation": {"form": {}}}
TASKS = {"extensions": {TASKS_EXTENSION: {}}}


def _user(*codenames, superuser=False):
    user = UserFactory(is_superuser=superuser)
    if codenames:
        group = GroupFactory()
        for codename in codenames:
            group.permissions.add(PermissionFactory(codename=codename))
        group.users.add(user)
    return user


def _token(user):
    app = OAuthApplication(name="Test MCP", user=user)
    app.set_secret(_generate_client_secret())
    app.save()
    return OAuthAccessToken.create_token(app)[1]


def _post(client, token, body, *, version=MODERN_PROTOCOL_VERSION, **headers):
    extra = {"HTTP_AUTHORIZATION": f"Bearer {token}"}
    if version is not None:
        extra["HTTP_MCP_PROTOCOL_VERSION"] = version
    if isinstance(body, dict) and "method" in body:
        extra["HTTP_MCP_METHOD"] = body["method"]
    for name, value in headers.items():
        extra[f"HTTP_{name.upper()}"] = value
    return client.post(ENDPOINT, data=json.dumps(body), content_type="application/json", **extra)


def _rpc(method, params=None, capabilities=None, req_id=1):
    params = dict(params or {})
    params["_meta"] = _meta(capabilities)
    return {"jsonrpc": "2.0", "id": req_id, "method": method, "params": params}


@pytest.fixture
def server():
    srv = McpServer()
    register_all_tools(srv)
    return srv


def _call(srv, user, name, arguments, capabilities=None, **extra):
    params = {"name": name, "arguments": arguments, **extra}
    return srv.handle_request(_rpc("tools/call", params, capabilities), user)


def _text(result):
    return json.loads(result["result"]["content"][0]["text"])


# ── Discovery, metadata and headers ───────────────────────


class TestDiscoveryAndHeaders:
    def test_discover_describes_the_server(self, client):
        token = _token(_user("system.mcp.access"))
        response = _post(client, token, _rpc("server/discover"))
        assert response.status_code == 200
        result = response.json()["result"]
        assert result["resultType"] == "complete"
        assert result["supportedVersions"] == [MODERN_PROTOCOL_VERSION]
        assert result["capabilities"]["extensions"][TASKS_EXTENSION] == {}
        assert "tools" in result["capabilities"]
        assert result["ttlMs"] > 0 and result["cacheScope"] in ("public", "private")
        assert result["_meta"]["io.modelcontextprotocol/serverInfo"]["name"] == "Cairn MCP Server"
        assert "help" in result["instructions"]

    def test_tools_list_is_cacheable_and_typed(self, client):
        token = _token(_user("system.mcp.access"))
        result = _post(client, token, _rpc("tools/list")).json()["result"]
        assert result["resultType"] == "complete"
        assert result["ttlMs"] > 0
        assert len(result["tools"]) > 100

    def test_unsupported_version_is_refused_with_the_supported_ones(self, client):
        token = _token(_user("system.mcp.access"))
        body = _rpc("tools/list")
        body["params"]["_meta"]["io.modelcontextprotocol/protocolVersion"] = "1900-01-01"
        response = _post(client, token, body, version="1900-01-01")
        assert response.status_code == 400
        error = response.json()["error"]
        assert error["code"] == -32022
        assert error["data"] == {"supported": [MODERN_PROTOCOL_VERSION], "requested": "1900-01-01"}

    def test_missing_client_capabilities_is_malformed(self, client):
        token = _token(_user("system.mcp.access"))
        body = _rpc("tools/list")
        del body["params"]["_meta"]["io.modelcontextprotocol/clientCapabilities"]
        response = _post(client, token, body)
        assert response.status_code == 400
        assert response.json()["error"]["code"] == -32602

    def test_version_header_must_match_the_body(self, client):
        token = _token(_user("system.mcp.access"))
        response = _post(client, token, _rpc("tools/list"), version=None)
        assert response.status_code == 400
        assert response.json()["error"]["code"] == -32020

    def test_method_and_name_headers_must_match_the_body(self, client):
        token = _token(_user("system.mcp.access"))
        body = _rpc("tools/call", {"name": "help", "arguments": {}})
        response = _post(client, token, body, mcp_name="get_glossary")
        assert response.status_code == 400
        assert response.json()["error"]["code"] == -32020
        response = _post(client, token, body, mcp_name="help")
        assert response.status_code == 200
        assert response.json()["result"]["resultType"] == "complete"

    def test_unknown_method_answers_404(self, client):
        token = _token(_user("system.mcp.access"))
        response = _post(client, token, _rpc("ping"))
        assert response.status_code == 404
        assert response.json()["error"]["code"] == -32601

    def test_no_session_identifier_is_echoed(self, client):
        token = _token(_user("system.mcp.access"))
        response = _post(client, token, _rpc("tools/list"), mcp_session_id="abc")
        assert "Mcp-Session-Id" not in response

    def test_previous_revision_is_served_as_before(self, client):
        token = _token(_user("system.mcp.access"))
        body = {
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {"protocolVersion": PROTOCOL_VERSION, "capabilities": {},
                       "clientInfo": {"name": "old", "version": "1"}},
        }
        response = _post(client, token, body, version=None, mcp_session_id="abc")
        assert response.status_code == 200
        result = response.json()["result"]
        assert result["protocolVersion"] == PROTOCOL_VERSION
        assert "resultType" not in result
        assert response["Mcp-Session-Id"] == "abc"

    def test_notification_is_accepted_without_a_body(self, client):
        token = _token(_user("system.mcp.access"))
        body = {"jsonrpc": "2.0", "method": "notifications/initialized"}
        response = _post(client, token, body, version=None)
        assert response.status_code == 202
        assert response.content == b""


class TestOrigin:
    def test_a_foreign_origin_is_refused(self, client):
        token = _token(_user("system.mcp.access"))
        response = _post(client, token, _rpc("tools/list"), origin="https://evil.example")
        assert response.status_code == 403

    def test_the_instance_origin_is_admitted(self, client):
        token = _token(_user("system.mcp.access"))
        response = _post(client, token, _rpc("tools/list"), origin="http://testserver")
        assert response.status_code == 200

    def test_a_trusted_origin_is_admitted(self, client, settings):
        settings.CSRF_TRUSTED_ORIGINS = ["https://inspector.example"]
        token = _token(_user("system.mcp.access"))
        response = _post(client, token, _rpc("tools/list"), origin="https://inspector.example")
        assert response.status_code == 200


# ── Elicitation ───────────────────────────────────────────


class TestDeletionConfirmation:
    def test_the_user_is_asked_before_a_record_is_deleted(self, server):
        user = _user(superuser=True)
        tag = Tag.objects.create(name="Obsolete")
        result = _call(server, user, "delete_tag", {"id": str(tag.pk)}, FORM)["result"]
        assert result["resultType"] == "input_required"
        request = result["inputRequests"]["confirm_deletion"]
        assert request["method"] == "elicitation/create"
        assert request["params"]["mode"] == "form"
        assert "Obsolete" in request["params"]["message"]
        assert request["params"]["requestedSchema"]["required"] == ["confirm"]
        assert result["requestState"]
        assert Tag.objects.filter(pk=tag.pk).exists()

    def test_a_confirmed_deletion_runs(self, server):
        user = _user(superuser=True)
        tag = Tag.objects.create(name="Obsolete")
        first = _call(server, user, "delete_tag", {"id": str(tag.pk)}, FORM)["result"]
        second = _call(
            server, user, "delete_tag", {"id": str(tag.pk)}, FORM,
            inputResponses={"confirm_deletion": {"action": "accept", "content": {"confirm": True}}},
            requestState=first["requestState"],
        )
        assert second["result"]["resultType"] == "complete"
        assert _text(second)["deleted"] is True
        assert not Tag.objects.filter(pk=tag.pk).exists()

    @pytest.mark.parametrize("answer", [
        {"action": "decline"},
        {"action": "cancel"},
        {"action": "accept", "content": {"confirm": False}},
    ])
    def test_a_refused_deletion_changes_nothing(self, server, answer):
        user = _user(superuser=True)
        tag = Tag.objects.create(name="Kept")
        first = _call(server, user, "delete_tag", {"id": str(tag.pk)}, FORM)["result"]
        second = _call(
            server, user, "delete_tag", {"id": str(tag.pk)}, FORM,
            inputResponses={"confirm_deletion": answer}, requestState=first["requestState"],
        )
        assert second["result"]["isError"] is True
        assert Tag.objects.filter(pk=tag.pk).exists()

    def test_a_confirmation_is_bound_to_its_call(self, server):
        user = _user(superuser=True)
        kept, other = Tag.objects.create(name="Kept"), Tag.objects.create(name="Other")
        state = _call(server, user, "delete_tag", {"id": str(other.pk)}, FORM)["result"]["requestState"]
        accept = {"confirm_deletion": {"action": "accept", "content": {"confirm": True}}}
        for forged in (state, "forged", None):
            result = _call(
                server, user, "delete_tag", {"id": str(kept.pk)}, FORM,
                inputResponses=accept, requestState=forged,
            )["result"]
            assert result["resultType"] == "input_required"
        assert Tag.objects.filter(pk=kept.pk).exists()

    def test_a_confirmation_is_bound_to_its_person(self, server):
        first_user, second_user = _user(superuser=True), _user(superuser=True)
        tag = Tag.objects.create(name="Kept")
        state = _call(server, first_user, "delete_tag", {"id": str(tag.pk)}, FORM)["result"]["requestState"]
        result = _call(
            server, second_user, "delete_tag", {"id": str(tag.pk)}, FORM,
            inputResponses={"confirm_deletion": {"action": "accept", "content": {"confirm": True}}},
            requestState=state,
        )["result"]
        assert result["resultType"] == "input_required"

    def test_a_client_without_elicitation_is_served_as_before(self, server):
        user = _user(superuser=True)
        tag = Tag.objects.create(name="Obsolete")
        result = _call(server, user, "delete_tag", {"id": str(tag.pk)}, {"elicitation": {"url": {}}})
        assert _text(result)["deleted"] is True

    def test_no_question_without_the_permission(self, server):
        user = _user("context.scope.read")
        tag = Tag.objects.create(name="Kept")
        result = _call(server, user, "delete_tag", {"id": str(tag.pk)}, FORM)["result"]
        assert result["resultType"] == "complete"
        assert result["isError"] is True
        assert "Permission denied" in result["content"][0]["text"]
        assert Tag.objects.filter(pk=tag.pk).exists()

    def test_no_question_about_a_record_out_of_reach(self, server):
        from assets.tests.factories import SupportAssetFactory

        reachable, foreign = ScopeFactory(), ScopeFactory()
        user = UserFactory()
        group = GroupFactory()
        group.permissions.add(PermissionFactory(codename="assets.support_asset.delete"))
        group.allowed_scopes.add(reachable)
        group.users.add(user)
        asset = SupportAssetFactory(scope=foreign, name="Hidden server")
        result = _call(server, user, "delete_support_asset", {"id": str(asset.pk)}, FORM)["result"]
        assert result["resultType"] == "complete"
        assert result["isError"] is True
        assert "Hidden server" not in json.dumps(result)
        assert asset.__class__.objects.filter(pk=asset.pk).exists()


class TestTransitionQuestions:
    def test_a_required_comment_is_asked_and_recorded(self, server):
        from incidents.tests.factories import SecurityEventFactory

        user = _user(superuser=True)
        event = SecurityEventFactory()
        event.workflow_state = "under_assessment"
        event.save()
        arguments = {"id": str(event.pk), "target_state": "discarded"}
        first = _call(server, user, "transition_security_event", arguments, FORM)["result"]
        assert first["resultType"] == "input_required"
        request = first["inputRequests"]["transition_comment"]["params"]
        assert request["requestedSchema"]["required"] == ["comment"]

        second = _call(
            server, user, "transition_security_event", arguments, FORM,
            inputResponses={"transition_comment": {"action": "accept", "content": {"comment": "A false positive."}}},
            requestState=first["requestState"],
        )
        assert _text(second)["workflow_state"] == "discarded"
        event.refresh_from_db()
        assert event.workflow_state == "discarded"

    def test_a_comment_given_with_the_call_asks_nothing(self, server):
        from incidents.tests.factories import SecurityEventFactory

        user = _user(superuser=True)
        event = SecurityEventFactory()
        event.workflow_state = "under_assessment"
        event.save()
        result = _call(server, user, "transition_security_event", {
            "id": str(event.pk), "target_state": "discarded", "comment": "A false positive.",
        }, FORM)
        assert _text(result)["workflow_state"] == "discarded"

    def test_a_confirm_trigger_asks_for_a_confirmation(self, server):
        from assets.tests.factories import SupportAssetFactory

        user = _user(superuser=True)
        asset = SupportAssetFactory()
        lifecycle = asset.get_lifecycle()
        sources = [t.source for t in lifecycle.transitions if t.target == "decommissioned"]
        source = next(s for s in sources if s != "*")
        asset.workflow_state = source
        asset.save()
        result = _call(server, user, "transition_support_asset", {
            "id": str(asset.pk), "target_state": "decommissioned",
        }, FORM)["result"]
        assert result["resultType"] == "input_required"
        assert "confirm_transition" in result["inputRequests"]

    def test_a_plain_transition_asks_nothing(self, server):
        from incidents.tests.factories import SecurityEventFactory

        user = _user(superuser=True)
        event = SecurityEventFactory()
        lifecycle = event.get_lifecycle()
        current = event.workflow_state or lifecycle.initial_step.code
        plain = next(t for t in lifecycle.transitions_from(current) if not t.requires_comment
                     and lifecycle.step(t.target).confirm_trigger is None)
        result = _call(server, user, "transition_security_event", {
            "id": str(event.pk), "target_state": plain.target,
        }, FORM)["result"]
        assert result["resultType"] == "complete"


# ── Tasks ─────────────────────────────────────────────────


@pytest.fixture
def inline_tasks(monkeypatch, django_capture_on_commit_callbacks):
    """Run a task where it is created, once its record is committed."""
    monkeypatch.setattr(tasks, "spawn", lambda task_id: tasks.execute(task_id, heartbeat=False))
    return django_capture_on_commit_callbacks


class TestTasks:
    def _create(self, server, user, inline_tasks):
        with inline_tasks(execute=True):
            result = _call(server, user, "generate_risk_register", {}, TASKS)["result"]
        return result

    def test_a_long_tool_answers_with_a_task(self, server, inline_tasks):
        user = _user(superuser=True)
        with inline_tasks(execute=False) as callbacks:
            result = _call(server, user, "generate_risk_register", {}, TASKS)["result"]
        assert result["resultType"] == "task"
        assert result["status"] == "working"
        assert result["ttlMs"] == tasks.TASK_TTL_MS
        assert result["pollIntervalMs"] == tasks.POLL_INTERVAL_MS
        assert result["createdAt"].endswith("Z") and result["lastUpdatedAt"].endswith("Z")
        assert McpTask.objects.filter(pk=result["taskId"], user=user).exists()
        assert len(callbacks) == 1

    def test_the_task_reports_the_tool_result(self, server, inline_tasks):
        user = _user(superuser=True)
        created = self._create(server, user, inline_tasks)
        polled = server.handle_request(_rpc("tasks/get", {"taskId": created["taskId"]}, TASKS), user)["result"]
        assert polled["resultType"] == "complete"
        assert polled["status"] == "completed"
        assert polled["result"]["isError"] is False
        assert "pollIntervalMs" not in polled

    def test_without_the_extension_the_tool_answers_at_once(self, server):
        user = _user(superuser=True)
        result = _call(server, user, "generate_risk_register", {}, {})["result"]
        assert result["resultType"] == "complete"
        assert "content" in result
        assert not McpTask.objects.exists()

    def test_a_refused_call_creates_no_task(self, server):
        user = _user("system.mcp.access")
        result = _call(server, user, "generate_risk_register", {}, TASKS)["result"]
        assert result["isError"] is True
        assert not McpTask.objects.exists()

    def test_a_task_belongs_to_its_person(self, server, inline_tasks):
        owner, other = _user(superuser=True), _user(superuser=True)
        created = self._create(server, owner, inline_tasks)
        for method in ("tasks/get", "tasks/update", "tasks/cancel"):
            answer = server.handle_request(_rpc(method, {"taskId": created["taskId"]}, TASKS), other)
            assert answer["error"]["code"] == -32602

    def test_an_unknown_or_malformed_identifier_is_not_found(self, server):
        user = _user(superuser=True)
        for task_id in ("00000000-0000-0000-0000-000000000000", "not-a-uuid"):
            answer = server.handle_request(_rpc("tasks/get", {"taskId": task_id}, TASKS), user)
            assert answer["error"]["code"] == -32602

    def test_the_task_methods_need_the_extension(self, client, inline_tasks):
        user = _user("system.mcp.access")
        token = _token(user)
        body = _rpc("tasks/get", {"taskId": "00000000-0000-0000-0000-000000000000"}, {})
        response = _post(client, token, body, mcp_name="00000000-0000-0000-0000-000000000000")
        assert response.status_code == 400
        error = response.json()["error"]
        assert error["code"] == -32021
        assert error["data"]["requiredCapabilities"] == {"extensions": {TASKS_EXTENSION: {}}}

    def test_a_task_whose_worker_stopped_fails(self, server, inline_tasks):
        user = _user(superuser=True)
        with inline_tasks(execute=False):
            created = _call(server, user, "generate_risk_register", {}, TASKS)["result"]
        McpTask.objects.filter(pk=created["taskId"]).update(
            heartbeat_at=timezone.now() - timedelta(seconds=tasks.STALE_AFTER_SECONDS + 1)
        )
        polled = server.handle_request(_rpc("tasks/get", {"taskId": created["taskId"]}, TASKS), user)["result"]
        assert polled["status"] == "failed"
        assert polled["error"]["code"] == -32603
        assert polled["statusMessage"]

    def test_an_expired_task_is_forgotten(self, server, inline_tasks):
        user = _user(superuser=True)
        created = self._create(server, user, inline_tasks)
        McpTask.objects.filter(pk=created["taskId"]).update(expires_at=timezone.now() - timedelta(seconds=1))
        answer = server.handle_request(_rpc("tasks/get", {"taskId": created["taskId"]}, TASKS), user)
        assert answer["error"]["code"] == -32602
        assert "expired" in answer["error"]["message"]
        assert not McpTask.objects.filter(pk=created["taskId"]).exists()

    def test_cancel_and_update_are_acknowledged(self, server, inline_tasks):
        user = _user(superuser=True)
        with inline_tasks(execute=False):
            created = _call(server, user, "generate_risk_register", {}, TASKS)["result"]
        for method in ("tasks/update", "tasks/cancel"):
            answer = server.handle_request(_rpc(method, {"taskId": created["taskId"]}, TASKS), user)
            assert answer["result"] == {"resultType": "complete"}
        task = McpTask.objects.get(pk=created["taskId"])
        assert task.cancel_requested is True
        assert task.status == McpTaskStatus.WORKING

    def test_a_tool_that_raises_fails_without_its_message(self, server, inline_tasks, monkeypatch):
        user = _user(superuser=True)
        tool = server.get_tool("generate_risk_register")

        def explode(user, arguments):
            raise RuntimeError("secret detail")

        monkeypatch.setitem(tool, "handler", explode)
        monkeypatch.setattr("mcp.api.views_mcp.get_mcp_server", lambda: server)
        created = self._create(server, user, inline_tasks)
        polled = server.handle_request(_rpc("tasks/get", {"taskId": created["taskId"]}, TASKS), user)["result"]
        assert polled["status"] == "failed"
        assert polled["error"] == {"code": -32603, "message": "Internal error"}
        assert "secret" not in json.dumps(polled)


@pytest.mark.django_db(transaction=True)
def test_a_task_runs_on_a_thread_of_the_worker(client):
    """The real executor : the call answers at once, the thread finishes the work."""
    import time

    user = _user(superuser=True)
    token = _token(user)
    body = _rpc("tools/call", {"name": "generate_risk_register", "arguments": {}}, TASKS)
    created = _post(client, token, body, mcp_name="generate_risk_register").json()["result"]
    assert created["resultType"] == "task"
    deadline = time.monotonic() + 30
    status = "working"
    while status == "working" and time.monotonic() < deadline:
        time.sleep(0.2)
        status = McpTask.objects.get(pk=created["taskId"]).status
    assert status == "completed"


class TestManagementReviewTransition:
    def test_a_cancellation_asks_for_its_comment(self, server):
        from reports.tests.factories import ManagementReviewFactory

        user = _user(superuser=True)
        review = ManagementReviewFactory()
        review.workflow_state = review.status = "planned"
        review.save()
        arguments = {"id": str(review.pk), "target_status": "cancelled"}
        first = _call(server, user, "transition_management_review", arguments, FORM)["result"]
        assert first["resultType"] == "input_required"
        assert "transition_comment" in first["inputRequests"]
        second = _call(
            server, user, "transition_management_review", arguments, FORM,
            inputResponses={"transition_comment": {"action": "accept", "content": {"comment": "Postponed to Q2."}}},
            requestState=first["requestState"],
        )["result"]
        assert second["isError"] is False
        review.refresh_from_db()
        assert review.status == "cancelled"
