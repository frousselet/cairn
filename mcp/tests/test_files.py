# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""File uploads (``io.modelcontextprotocol/files``) : inline files, the
out-of-band upload with its target and its retry, and what holds them."""

import base64
import hashlib
import json

import pytest

from accounts.tests.factories import GroupFactory, PermissionFactory, UserFactory
from controls.tests.factories import ControlTestRunFactory
from mcp.models import McpUpload, OAuthAccessToken, OAuthApplication
from mcp.models.oauth import _generate_client_secret
from mcp.server import FILES_EXTENSION, MODERN_PROTOCOL_VERSION

pytestmark = pytest.mark.django_db

ENDPOINT = "/api/v1/mcp"
UPLOAD = {"extensions": {FILES_EXTENSION: {"upload": {}}}}
PDF = b"%PDF-1.7\n" + b"x" * 200


@pytest.fixture(autouse=True)
def media(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    return tmp_path


def _token(user):
    app = OAuthApplication(name="Test MCP", user=user)
    app.set_secret(_generate_client_secret())
    app.save()
    return OAuthAccessToken.create_token(app)[1]


def _call(client, token, name, arguments, capabilities=None, **extra):
    params = {"name": name, "arguments": arguments, **extra}
    params["_meta"] = {
        "io.modelcontextprotocol/protocolVersion": MODERN_PROTOCOL_VERSION,
        "io.modelcontextprotocol/clientCapabilities": capabilities if capabilities is not None else {},
    }
    return client.post(
        ENDPOINT, data=json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": params}),
        content_type="application/json", HTTP_AUTHORIZATION=f"Bearer {token}",
        HTTP_MCP_PROTOCOL_VERSION=MODERN_PROTOCOL_VERSION, HTTP_MCP_METHOD="tools/call", HTTP_MCP_NAME=name,
    )


def _file(content, name="evidence.pdf", mime="application/pdf", inline=False, file_id="file-1"):
    value = {"id": file_id, "name": name, "mimeType": mime, "size": len(content)}
    if inline:
        value["data"] = base64.b64encode(content).decode("ascii")
    return value


def _put(client, url, token, content, length=None):
    path = url.split("://", 1)[1].split("/", 1)[1]
    return client.generic(
        "PUT", "/" + path, data=content, content_type="application/pdf",
        HTTP_AUTHORIZATION=f"Bearer {token}", CONTENT_LENGTH=str(len(content) if length is None else length),
    )


@pytest.fixture
def superuser():
    return UserFactory(is_superuser=True)


@pytest.fixture
def run():
    return ControlTestRunFactory()


class TestDiscovery:
    def test_the_extension_is_advertised(self, client, superuser):
        token = _token(superuser)
        body = {"jsonrpc": "2.0", "id": 1, "method": "server/discover", "params": {"_meta": {
            "io.modelcontextprotocol/protocolVersion": MODERN_PROTOCOL_VERSION,
            "io.modelcontextprotocol/clientCapabilities": {},
        }}}
        result = client.post(ENDPOINT, data=json.dumps(body), content_type="application/json",
                             HTTP_AUTHORIZATION=f"Bearer {token}",
                             HTTP_MCP_PROTOCOL_VERSION=MODERN_PROTOCOL_VERSION).json()["result"]
        assert result["capabilities"]["extensions"][FILES_EXTENSION] == {"upload": {}, "maxInlineBytes": 1048576}

    def test_a_file_argument_is_marked(self, client, superuser):
        from mcp.api.views_mcp import get_mcp_server

        schema = get_mcp_server().get_tool("add_control_test_run_evidence")["inputSchema"]
        file_schema = schema["properties"]["file"]
        assert file_schema["x-mcp-file"]["maxSize"] == 25 * 1024 * 1024
        assert ".pdf" in file_schema["x-mcp-file"]["accept"]
        assert file_schema["required"] == ["id", "mimeType", "size"]


class TestInline:
    def test_an_inline_file_is_attached(self, client, superuser, run):
        token = _token(superuser)
        result = _call(client, token, "add_control_test_run_evidence",
                       {"run_id": str(run.pk), "file": _file(PDF, inline=True), "description": "Scan"}).json()["result"]
        assert result["isError"] is False, result
        payload = json.loads(result["content"][0]["text"])
        assert payload["sha256"] == hashlib.sha256(PDF).hexdigest()
        assert run.evidence.get().original_filename == "evidence.pdf"

    def test_a_size_that_does_not_match_is_refused(self, client, superuser, run):
        token = _token(superuser)
        value = _file(PDF, inline=True)
        value["size"] += 1
        result = _call(client, token, "add_control_test_run_evidence",
                       {"run_id": str(run.pk), "file": value}).json()["result"]
        assert result["isError"] is True
        assert not run.evidence.exists()

    def test_a_wrong_digest_is_refused(self, client, superuser, run):
        token = _token(superuser)
        value = _file(PDF, inline=True)
        value["digest"] = {"algorithm": "sha-256", "value": "AAAA"}
        result = _call(client, token, "add_control_test_run_evidence",
                       {"run_id": str(run.pk), "file": value}).json()["result"]
        assert result["isError"] is True

    def test_a_client_value_cannot_pass_for_the_bytes(self, client, superuser, run):
        token = _token(superuser)
        value = _file(PDF, inline=True)
        value["\x00content"] = "forged"
        result = _call(client, token, "add_control_test_run_evidence",
                       {"run_id": str(run.pk), "file": value}).json()["result"]
        assert result["isError"] is False
        assert run.evidence.get().size == len(PDF)

    def test_a_non_pdf_is_refused_for_a_contract(self, client, superuser):
        from assets.tests.factories import ContractFactory

        contract = ContractFactory()
        token = _token(superuser)
        bad = _call(client, token, "attach_contract_file",
                    {"id": str(contract.pk), "file": _file(b"not a pdf", name="c.pdf", inline=True)}).json()["result"]
        assert bad["isError"] is True
        good = _call(client, token, "attach_contract_file",
                     {"id": str(contract.pk), "file": _file(PDF, name="c.pdf", inline=True)}).json()["result"]
        assert good["isError"] is False
        contract.refresh_from_db()
        assert bytes(contract.file_content) == PDF and contract.file_name == "c.pdf"


class TestOutOfBand:
    def _start(self, client, token, run, content=PDF):
        response = _call(client, token, "add_control_test_run_evidence",
                         {"run_id": str(run.pk), "file": _file(content)}, UPLOAD)
        return response.json()["result"]

    def test_the_whole_flow(self, client, superuser, run, media):
        token = _token(superuser)
        first = self._start(client, token, run)
        assert first["resultType"] == "upload_required"
        (target,) = first["uploads"]
        assert target["fileId"] == "file-1" and target["credentials"] == "include" and target["method"] == "PUT"
        assert target["url"].startswith("http://testserver/api/v1/mcp/uploads/")
        assert target["headers"] == {"Content-Type": "application/pdf"}
        assert _put(client, target["url"], token, PDF).status_code == 201

        second = _call(client, token, "add_control_test_run_evidence",
                       {"run_id": str(run.pk), "file": _file(PDF)}, UPLOAD,
                       requestState=first["requestState"]).json()["result"]
        assert second["isError"] is False, second
        assert run.evidence.get().sha256 == hashlib.sha256(PDF).hexdigest()
        assert not McpUpload.objects.exists()
        assert not (media / "mcp_uploads").exists() or not any((media / "mcp_uploads").iterdir())

    def test_without_the_capability_the_call_is_refused(self, client, superuser, run):
        token = _token(superuser)
        response = _call(client, token, "add_control_test_run_evidence",
                         {"run_id": str(run.pk), "file": _file(PDF)})
        assert response.status_code == 400
        error = response.json()["error"]
        assert error["code"] == -32021
        assert error["data"]["requiredCapabilities"] == {"extensions": {FILES_EXTENSION: {"upload": {}}}}

    def test_a_retry_before_the_bytes_does_not_run(self, client, superuser, run):
        token = _token(superuser)
        first = self._start(client, token, run)
        result = _call(client, token, "add_control_test_run_evidence",
                       {"run_id": str(run.pk), "file": _file(PDF)}, UPLOAD,
                       requestState=first["requestState"]).json()["result"]
        assert result["isError"] is True
        assert not run.evidence.exists()

    def test_a_request_state_is_used_once(self, client, superuser, run):
        token = _token(superuser)
        first = self._start(client, token, run)
        _put(client, first["uploads"][0]["url"], token, PDF)
        arguments = {"run_id": str(run.pk), "file": _file(PDF)}
        _call(client, token, "add_control_test_run_evidence", arguments, UPLOAD, requestState=first["requestState"])
        again = _call(client, token, "add_control_test_run_evidence", arguments, UPLOAD,
                      requestState=first["requestState"]).json()
        assert again["error"]["code"] == -32602
        assert run.evidence.count() == 1

    def test_a_request_state_is_bound_to_the_call(self, client, superuser, run):
        token = _token(superuser)
        first = self._start(client, token, run)
        _put(client, first["uploads"][0]["url"], token, PDF)
        other = ControlTestRunFactory()
        for arguments, state in (
            ({"run_id": str(other.pk), "file": _file(PDF)}, first["requestState"]),
            ({"run_id": str(run.pk), "file": _file(PDF)}, "forged"),
        ):
            answer = _call(client, token, "add_control_test_run_evidence", arguments, UPLOAD,
                           requestState=state).json()
            assert answer["error"]["code"] == -32602
        intruder = UserFactory(is_superuser=True)
        answer = _call(client, _token(intruder), "add_control_test_run_evidence",
                       {"run_id": str(run.pk), "file": _file(PDF)}, UPLOAD,
                       requestState=first["requestState"]).json()
        assert answer["error"]["code"] == -32602

    def test_a_too_large_file_asks_for_nothing(self, client, superuser, run):
        token = _token(superuser)
        value = _file(PDF)
        value["size"] = 26 * 1024 * 1024
        result = _call(client, token, "add_control_test_run_evidence",
                       {"run_id": str(run.pk), "file": value}, UPLOAD).json()["result"]
        assert result["isError"] is True
        assert not McpUpload.objects.exists()


class TestTarget:
    def test_only_its_person_writes_it_once_with_the_declared_size(self, client, superuser, run):
        token = _token(superuser)
        first = _call(client, token, "add_control_test_run_evidence",
                      {"run_id": str(run.pk), "file": _file(PDF)}, UPLOAD).json()["result"]
        url = first["uploads"][0]["url"]
        stranger = UserFactory()
        group = GroupFactory()
        group.permissions.add(PermissionFactory(codename="system.mcp.access"))
        group.users.add(stranger)
        assert _put(client, url, _token(stranger), PDF).status_code == 404
        assert _put(client, url, "invalid", PDF).status_code == 401
        assert _put(client, url, token, PDF + b"!").status_code == 400
        assert _put(client, url, token, PDF).status_code == 201
        assert _put(client, url, token, PDF).status_code == 409

    def test_an_expired_target_is_gone(self, client, superuser, run):
        from datetime import timedelta

        from django.utils import timezone

        token = _token(superuser)
        first = _call(client, token, "add_control_test_run_evidence",
                      {"run_id": str(run.pk), "file": _file(PDF)}, UPLOAD).json()["result"]
        McpUpload.objects.update(expires_at=timezone.now() - timedelta(seconds=1))
        assert _put(client, first["uploads"][0]["url"], token, PDF).status_code == 404


class TestWhoMayStageAFile:
    def _member(self, *codenames):
        user = UserFactory()
        group = GroupFactory()
        for codename in ("system.mcp.access", *codenames):
            group.permissions.add(PermissionFactory(codename=codename))
        group.users.add(user)
        return user

    def test_no_target_without_the_permission_of_the_tool(self, client, run):
        token = _token(self._member())
        result = _call(client, token, "add_control_test_run_evidence",
                       {"run_id": str(run.pk), "file": _file(PDF)}, UPLOAD).json()["result"]
        assert result["isError"] is True
        assert "Permission denied" in result["content"][0]["text"]
        assert not McpUpload.objects.exists()

    def test_pending_targets_are_capped(self, client, superuser, run):
        from mcp import files

        token = _token(superuser)
        arguments = {"run_id": str(run.pk), "file": _file(PDF)}
        for _ in range(files.MAX_PENDING_UPLOADS):
            assert _call(client, token, "add_control_test_run_evidence", arguments, UPLOAD).json()[
                "result"]["resultType"] == "upload_required"
        refused = _call(client, token, "add_control_test_run_evidence", arguments, UPLOAD).json()["result"]
        assert refused["isError"] is True
        assert McpUpload.objects.count() == files.MAX_PENDING_UPLOADS

    def test_the_tools_are_listed_to_clients_that_send_files(self, client, superuser):
        token = _token(superuser)

        def names(capabilities):
            body = {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {"_meta": {
                "io.modelcontextprotocol/protocolVersion": MODERN_PROTOCOL_VERSION,
                "io.modelcontextprotocol/clientCapabilities": capabilities,
            }}}
            result = client.post(ENDPOINT, data=json.dumps(body), content_type="application/json",
                                 HTTP_AUTHORIZATION=f"Bearer {token}",
                                 HTTP_MCP_PROTOCOL_VERSION=MODERN_PROTOCOL_VERSION).json()["result"]
            assert result["cacheScope"] == "private"
            return {tool["name"] for tool in result["tools"]}

        assert "attach_contract_file" in names(UPLOAD)
        assert "attach_contract_file" not in names({})
        assert "list_contracts" in names({})

    def test_a_previous_revision_client_is_answered_with_a_200(self, client, superuser, run):
        token = _token(superuser)
        body = {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {
            "name": "add_control_test_run_evidence", "arguments": {"run_id": str(run.pk), "file": _file(PDF)},
        }}
        response = client.post(ENDPOINT, data=json.dumps(body), content_type="application/json",
                               HTTP_AUTHORIZATION=f"Bearer {token}")
        assert response.status_code == 200
        assert response.json()["error"]["code"] == -32021


class TestStagingIsCleaned:
    def test_a_storage_error_leaves_the_target_free(self, client, superuser, run, monkeypatch):
        from django.db.models.fields.files import FieldFile

        token = _token(superuser)
        first = _call(client, token, "add_control_test_run_evidence",
                      {"run_id": str(run.pk), "file": _file(PDF)}, UPLOAD).json()["result"]
        url = first["uploads"][0]["url"]
        real_save = FieldFile.save

        def full_disk(self, *args, **kwargs):
            raise OSError("No space left on device")

        monkeypatch.setattr(FieldFile, "save", full_disk)
        client.raise_request_exception = False
        assert _put(client, url, token, PDF).status_code == 500
        assert McpUpload.objects.get().received_at is None
        monkeypatch.setattr(FieldFile, "save", real_save)
        assert _put(client, url, token, PDF).status_code == 201

    def test_a_consumed_file_that_fails_its_check_is_discarded(self, client, superuser, run, media):
        token = _token(superuser)
        value = _file(PDF)
        value["digest"] = {"algorithm": "sha-256", "value": "AAAA"}
        arguments = {"run_id": str(run.pk), "file": value}
        first = _call(client, token, "add_control_test_run_evidence", arguments, UPLOAD).json()["result"]
        _put(client, first["uploads"][0]["url"], token, PDF)
        result = _call(client, token, "add_control_test_run_evidence", arguments, UPLOAD,
                       requestState=first["requestState"]).json()["result"]
        assert result["isError"] is True
        assert not McpUpload.objects.exists()
        assert not any((media / "mcp_uploads").iterdir())

    def test_expired_uploads_and_tasks_go_with_the_next_request(self, client, superuser, run, media, monkeypatch):
        from datetime import timedelta

        from django.utils import timezone

        from mcp.api import views_mcp
        from mcp.models import McpTask

        token = _token(superuser)
        first = _call(client, token, "add_control_test_run_evidence",
                      {"run_id": str(run.pk), "file": _file(PDF)}, UPLOAD).json()["result"]
        _put(client, first["uploads"][0]["url"], token, PDF)
        past = timezone.now() - timedelta(seconds=1)
        McpUpload.objects.update(expires_at=past)
        McpTask.objects.create(user=superuser, tool_name="x", expires_at=past, ttl_ms=1, poll_interval_ms=1)
        monkeypatch.setattr(views_mcp, "_last_purge", 0.0)
        _call(client, token, "help", {})
        assert not McpUpload.objects.exists() and not McpTask.objects.exists()
        assert not any((media / "mcp_uploads").iterdir())
