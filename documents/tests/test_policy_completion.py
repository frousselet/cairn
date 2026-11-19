# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""A document is created short, its versions are completed on their page.

What every entity of the usability standard does (the dialog on one screen,
the landing on the record, a card per section, a reader offered no edit) is
checked for the document in ``core/tests/test_usability_standard.py``. A
version has no creation dialog of its own (it is drafted with its document,
or from the version in force) : its page is checked here, with what is
particular to each :

- a document is created with its title, its type (asked, never preselected)
  and its owner; its first version is drafted with it, empty, and the page of
  the document leads to it;
- a version needs a content or a PDF, and from the second version on a change
  summary, before it is submitted for review (RG-DOC-02, RG-DOC-06), on every
  surface. A submitted version is frozen : nothing is left to complete on it.
"""

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.tests.factories import UserFactory
from core.completeness import completeness_of
from core.lifecycle import DomainRefusalError
from core.tests.test_usability_standard import _current_answers, _snapshot
from documents.constants import POLICY_ACTIVE, POLICY_RETIRED, VERSION_IN_REVIEW
from documents.forms import PolicyCreateForm, PolicyVersionForm
from documents.models import Policy
from documents.tests.factories import PolicyFactory, PolicyVersionFactory, put_in_force

pytestmark = pytest.mark.django_db

DRAWER = {"HTTP_HX_REQUEST": "true", "HTTP_HX_TARGET": "drawer-form-content"}
PDF = b"%PDF-1.4\n%test\n"


@pytest.fixture
def admin(client):
    user = UserFactory(is_superuser=True)
    client.force_login(user)
    return user


def _missing(record):
    report = completeness_of(record)
    return [item.key for item in report.blocking_missing], [item.key for item in report.advised_missing]


def _empty_draft(**kwargs):
    """A document as the dialog creates it, with its first version still empty."""
    policy = PolicyFactory(**kwargs)
    return policy, PolicyVersionFactory(policy=policy, version_label="1.0", content="", change_summary="")


def _reader(client):
    from accounts.models import Group, Permission

    reader = UserFactory()
    group = Group.objects.create(name=f"readers-{reader.pk}")
    group.permissions.add(Permission.objects.get(codename="documents.policy.read"))
    group.users.add(reader)
    client.force_login(reader)
    return reader


# ── The document ────────────────────────────────────────────────────────────


class TestADocumentIsCreatedShort:
    def test_it_asks_the_title_the_type_the_owner_and_the_summary(self, admin):
        from context.tests.factories import ScopeFactory

        ScopeFactory()
        ScopeFactory()

        form = PolicyCreateForm(user=admin)

        assert sorted(form.fields) == ["document_type", "owner", "scopes", "summary", "title"]
        assert form.is_multistep is False
        assert form.fields["owner"].initial == admin.pk
        assert form.fields["summary"].required is False

    def test_the_type_is_a_decision_of_the_reader(self, client, admin):
        """ "Policy" was saved for whoever did not choose, a procedure included."""
        document_type = PolicyCreateForm(user=admin).fields["document_type"]

        response = client.post(reverse("documents:policy-create"), {"title": "Backup procedure"}, **DRAWER)

        assert document_type.required and [value for value, _label in document_type.choices][0] == ""
        assert response.status_code == 200 and not Policy.objects.exists()

    def test_its_first_version_is_drafted_with_it_and_the_page_leads_to_it(self, client, admin):
        # The dialog opens with whoever creates the document as its owner.
        response = client.post(
            reverse("documents:policy-create"),
            {"title": "Backup procedure", "document_type": "procedure", "owner": admin.pk}, **DRAWER,
        )
        policy = Policy.objects.get()
        version = policy.versions.get()

        html = client.get(policy.get_absolute_url()).content.decode()

        assert response.status_code == 204 and response["HX-Redirect"] == policy.get_absolute_url()
        assert (version.version_label, version.content, version.has_pdf) == ("1.0", "", False)
        assert _missing(policy) == (["version"], ["requirements"])
        assert "Put a version in force" in html and f'href="{version.get_absolute_url()}"' in html

    def test_it_is_complete_once_a_version_is_in_force(self, admin):
        policy, version = _empty_draft()
        version.content = "<p>Backups run every night.</p>"
        version.save()

        put_in_force(version, admin)
        policy.refresh_from_db()

        assert policy.workflow_state == POLICY_ACTIVE
        assert "version" not in _missing(policy)[0]

    def test_a_retired_document_has_nothing_left_to_complete(self, client, admin):
        policy, _version = _empty_draft()
        policy.transition_to(POLICY_RETIRED, admin, comment="Never adopted.")

        html = client.get(policy.get_absolute_url()).content.decode()

        assert "?section=" not in html and "To complete" not in html


# ── The version ─────────────────────────────────────────────────────────────


class TestWhatAVersionStillNeeds:
    def test_it_is_not_submitted_before_its_content(self, admin):
        _policy, version = _empty_draft()

        with pytest.raises(DomainRefusalError) as refusal:
            version.transition_to(VERSION_IN_REVIEW, admin)
        version.content = "<p>Backups run every night.</p>"
        version.save()
        version.transition_to(VERSION_IN_REVIEW, admin)

        assert _missing(PolicyVersionFactory.build(content="<p><br></p>", change_summary=""))[0] == ["content"]
        assert "fill in the content or attach a PDF" in str(refusal.value)
        assert version.workflow_state == VERSION_IN_REVIEW

    def test_a_pdf_is_a_content_too(self, admin):
        _policy, version = _empty_draft()
        version.set_pdf(PDF, "backup.pdf")
        version.save()

        assert _missing(version)[0] == []

    def test_from_the_second_version_on_it_says_what_changed(self, admin):
        policy, version = _empty_draft()
        version.content = "<p>Backups run every night.</p>"
        version.save()
        put_in_force(version, admin)
        second = policy.new_version(admin)

        with pytest.raises(DomainRefusalError) as refusal:
            second.transition_to(VERSION_IN_REVIEW, admin)

        assert _missing(second)[0] == ["change_summary"]
        assert "fill in the change summary" in str(refusal.value)

    def test_the_page_lists_it_and_opens_each_card(self, client, admin):
        _policy, version = _empty_draft()
        edit = reverse("documents:policyversion-update", args=[version.pk])

        html = client.get(version.get_absolute_url()).content.decode()

        assert "Fill in the content or attach a PDF" in html
        for key in PolicyVersionForm.section_keys():
            assert f'{edit}?section={key}"' in html, key

    def test_saving_a_card_leaves_the_rest_of_the_version_alone(self, client, admin):
        _policy, version = _empty_draft()
        version.content = "<p>Backups run every night.</p>"
        version.change_summary = "First issue."
        version.save()
        edit = reverse("documents:policyversion-update", args=[version.pk])
        version.refresh_from_db()
        before = _snapshot(version)

        for key in PolicyVersionForm.section_keys():
            response = client.get(f"{edit}?section={key}", **DRAWER)
            assert response.status_code == 200 and 'name="_section"' in response.content.decode(), key
            form = PolicyVersionForm(instance=version, user=admin, section=key)
            response = client.post(edit, {**_current_answers(form), "_section": key}, **DRAWER)
            assert response.status_code == 204, f"{key} : {response.content.decode()[:600]}"
            version.refresh_from_db()
            assert _snapshot(version) == before, f"saving the section '{key}' changed something else"

    def test_a_reader_is_offered_no_edit(self, client):
        _policy, version = _empty_draft()
        _reader(client)

        html = client.get(version.get_absolute_url()).content.decode()

        assert "?section=" not in html and "To complete" in html

    def test_a_submitted_version_is_frozen_and_has_nothing_left_to_complete(self, client, admin):
        _policy, version = _empty_draft()
        version.content = "<p>Backups run every night.</p>"
        version.save()
        version.transition_to(VERSION_IN_REVIEW, admin)

        html = client.get(version.get_absolute_url()).content.decode()

        assert "?section=" not in html and "To complete" not in html


# ── The REST API and the MCP server ─────────────────────────────────────────


class TestTheOtherSurfaces:
    @staticmethod
    def _body(response):
        body = response.json()
        return body.get("data", body)

    def test_the_rest_api_says_what_a_document_and_a_version_need(self, admin):
        api = APIClient()
        api.force_authenticate(user=admin)
        policy, version = _empty_draft()

        read_policy = self._body(api.get(f"/api/v1/documents/policies/{policy.pk}/"))
        read_version = self._body(api.get(f"/api/v1/documents/policy-versions/{version.pk}/"))
        submitted = api.post(
            f"/api/v1/documents/policy-versions/{version.pk}/transition/", {"target_state": VERSION_IN_REVIEW},
            format="json",
        )

        assert [item["key"] for item in read_policy["completeness"]["missing"] if item["blocking"]] == ["version"]
        assert [item["key"] for item in read_version["completeness"]["missing"]] == ["content"]
        assert submitted.status_code == 400 and "fill in the content or attach a PDF" in submitted.content.decode()

    def test_the_mcp_server_says_what_a_document_and_a_version_need(self, admin):
        from mcp.server import McpServer
        from mcp.tools import register_all_tools

        server = McpServer()
        register_all_tools(server)
        policy, version = _empty_draft()

        read_policy = server.get_tool("get_policy")["handler"](admin, {"id": str(policy.pk)})
        read_version = server.get_tool("get_policy_version")["handler"](admin, {"id": str(version.pk)})

        assert [item["key"] for item in read_policy["completeness"]["missing"] if item["blocking"]] == ["version"]
        assert [item["key"] for item in read_version["completeness"]["missing"]] == ["content"]


class TestTheRegister:
    def test_the_empty_register_says_what_a_document_is_and_offers_the_first(self, client, admin):
        html = client.get(reverse("documents:policy-list")).content.decode()

        assert "A document is a written rule of the organisation" in html
        assert reverse("documents:policy-create") in html
