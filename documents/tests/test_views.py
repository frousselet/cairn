# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""The web interface of module 7 (documents) : pages, acts, tenancy and RG-DOC-17."""
import hashlib
from unittest import mock

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.template.loader import render_to_string
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from accounts.tests.factories import GroupFactory, PermissionFactory, UserFactory
from context.tests.factories import ScopeFactory
from documents.constants import (
    CAMPAIGN_RUNNING,
    VERSION_DRAFT,
    VERSION_IN_REVIEW,
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

PDF = b"%PDF-1.7\n%test document\n"
HTMX_DRAWER = {"HTTP_HX_REQUEST": "true", "HTTP_HX_TARGET": "drawer-form-content"}


def _user(*codenames, scopes=()):
    user = UserFactory()
    group = GroupFactory()
    for codename in codenames:
        group.permissions.add(PermissionFactory(codename=codename))
    if scopes:
        group.allowed_scopes.add(*scopes)
    group.users.add(user)
    return user


def _client(user):
    client = Client()
    client.force_login(user)
    return client


@pytest.fixture
def admin():
    return UserFactory(is_superuser=True)


@pytest.fixture
def admin_client(admin):
    return _client(admin)


@pytest.fixture
def policy_in_force(admin):
    policy = PolicyFactory(title="Information security policy", owner=admin)
    version = PolicyVersionFactory(policy=policy, version_label="1.0")
    put_in_force(version, admin)
    policy.refresh_from_db()
    return policy


def _running_campaign(version, users, launcher):
    campaign = AcknowledgementCampaignFactory(policy_version=version)
    campaign.audience_users.set(users)
    campaign.transition_to(CAMPAIGN_RUNNING, launcher)
    return campaign


# --- Pages ------------------------------------------------------------------


class TestPagesRender:
    def test_every_page_renders(self, admin_client, admin, policy_in_force):
        version = policy_in_force.version_in_force
        campaign = _running_campaign(version, [admin, UserFactory()], admin)
        row = campaign.acknowledgements.get(user=admin)
        draft = policy_in_force.new_version(admin)
        urls = [
            reverse("documents:policy-list"),
            reverse("documents:policy-table-body"),
            reverse("documents:policy-detail", args=[policy_in_force.pk]),
            reverse("documents:policy-create"),
            reverse("documents:policy-update", args=[policy_in_force.pk]),
            reverse("documents:policy-record-review", args=[policy_in_force.pk]),
            reverse("documents:policy-new-version", args=[policy_in_force.pk]),
            reverse("documents:policy-delete", args=[policy_in_force.pk]),
            reverse("documents:policyversion-detail", args=[version.pk]),
            reverse("documents:policyversion-update", args=[draft.pk]),
            reverse("documents:policyversion-delete", args=[draft.pk]),
            reverse("documents:campaign-list"),
            reverse("documents:campaign-table-body"),
            reverse("documents:campaign-create") + f"?version={version.pk}",
            reverse("documents:acknowledgementcampaign-detail", args=[campaign.pk]),
            reverse("documents:campaign-update", args=[campaign.pk]),
            reverse("documents:campaign-delete", args=[campaign.pk]),
            reverse("documents:acknowledgement-excuse", args=[campaign.acknowledgements.exclude(user=admin).get().pk]),
            reverse("documents:acknowledge-list"),
            reverse("documents:acknowledge", args=[row.pk]),
        ]
        for url in urls:
            response = admin_client.get(url)
            assert response.status_code == 200, url
            drawer = admin_client.get(url, **HTMX_DRAWER)
            assert drawer.status_code == 200, url

    def test_pages_carry_the_documents_accent_and_breadcrumb(self, admin_client, policy_in_force):
        html = admin_client.get(reverse("documents:policy-detail", args=[policy_in_force.pk])).content.decode()
        assert "page-header--accent-documents" in html
        assert reverse("documents:policy-list") in html
        assert "lifecycle" in html  # the shared stepper

    def test_detail_shows_the_version_in_force_with_its_hash_and_approval(self, admin_client, admin, policy_in_force):
        version = policy_in_force.version_in_force
        version_with_pdf = policy_in_force.new_version(admin)
        version_with_pdf.change_summary = "Signed copy."
        version_with_pdf.set_pdf(PDF, "signed.pdf")
        version_with_pdf.save()
        put_in_force(version_with_pdf, admin)
        html = admin_client.get(reverse("documents:policy-detail", args=[policy_in_force.pk])).content.decode()
        assert hashlib.sha256(PDF).hexdigest() in html
        assert admin.display_name in html
        assert version.reference in html  # the superseded version stays listed

    def test_list_flags_an_overdue_review_and_filters_on_it(self, admin_client, policy_in_force):
        Policy.objects.filter(pk=policy_in_force.pk).update(next_review_date=timezone.localdate() - timezone.timedelta(days=3))
        fresh = PolicyFactory(title="Fresh draft")
        url = reverse("documents:policy-list")
        overdue = admin_client.get(reverse("documents:policy-table-body") + "?review=overdue").content.decode()
        assert policy_in_force.title in overdue and fresh.title not in overdue
        assert "Review overdue" in admin_client.get(url).content.decode()

    def test_reader_without_permission_is_refused(self, policy_in_force):
        client = _client(UserFactory())
        for url in (
            reverse("documents:policy-list"),
            reverse("documents:policy-detail", args=[policy_in_force.pk]),
            reverse("documents:campaign-list"),
        ):
            assert client.get(url).status_code == 302


# --- Tenancy ----------------------------------------------------------------


class TestScopes:
    def test_documents_outside_the_scopes_are_hidden(self, admin, policy_in_force):
        mine, other = ScopeFactory(), ScopeFactory()
        policy_in_force.scopes.set([other])
        visible = PolicyFactory(title="Visible document")
        visible.scopes.set([mine])
        client = _client(_user("documents.policy.read", scopes=[mine]))
        html = client.get(reverse("documents:policy-list")).content.decode()
        assert visible.title in html and policy_in_force.title not in html
        assert client.get(reverse("documents:policy-detail", args=[policy_in_force.pk])).status_code == 404
        version = policy_in_force.version_in_force
        assert client.get(reverse("documents:policyversion-detail", args=[version.pk])).status_code == 404
        assert client.get(reverse("documents:policyversion-pdf", args=[version.pk])).status_code == 404

    def test_acts_resolve_the_document_through_its_scopes(self, policy_in_force):
        other = ScopeFactory()
        policy_in_force.scopes.set([other])
        client = _client(_user("documents.policy.read", "documents.policy.update", "documents.policy.approve", scopes=[ScopeFactory()]))
        assert client.get(reverse("documents:policy-new-version", args=[policy_in_force.pk])).status_code == 404
        assert client.post(reverse("documents:policy-record-review", args=[policy_in_force.pk])).status_code == 404


# --- Document and versions ---------------------------------------------------


class TestPolicyForms:
    def test_create_makes_the_document_and_its_first_draft_version(self, admin_client, admin):
        upload = SimpleUploadedFile("policy.pdf", PDF, content_type="application/pdf")
        response = admin_client.post(reverse("documents:policy-create"), {
            "title": "Backup procedure", "document_type": "procedure", "classification": "internal",
            "review_frequency_months": 12, "version_label": "1.0", "content": "<p>Daily backups.</p>",
            "upload": upload,
        })
        assert response.status_code == 302, response.content.decode()[:2000]
        policy = Policy.objects.get(title="Backup procedure")
        version = policy.versions.get()
        assert version.workflow_state == VERSION_DRAFT and version.version_label == "1.0"
        assert version.file_sha256 == hashlib.sha256(PDF).hexdigest()
        assert version.created_by == admin and policy.created_by == admin

    def test_create_refuses_a_file_that_is_not_a_pdf(self, admin_client):
        upload = SimpleUploadedFile("policy.pdf", b"not a pdf", content_type="application/pdf")
        response = admin_client.post(reverse("documents:policy-create"), {
            "title": "Broken", "document_type": "policy", "classification": "internal",
            "review_frequency_months": 12, "version_label": "1.0", "upload": upload,
        })
        assert response.status_code == 200
        assert not Policy.objects.filter(title="Broken").exists()

    def test_a_draft_version_takes_a_pdf_through_set_pdf(self, admin_client, policy_in_force, admin):
        draft = policy_in_force.new_version(admin)
        response = admin_client.post(reverse("documents:policyversion-update", args=[draft.pk]), {
            "version_label": draft.version_label, "content": "<p>New text</p>", "change_summary": "Rewritten.",
            "upload": SimpleUploadedFile("v.pdf", PDF, content_type="application/pdf"),
        })
        assert response.status_code == 302
        draft.refresh_from_db()
        assert draft.has_pdf and draft.file_sha256 == hashlib.sha256(PDF).hexdigest()
        assert draft.change_summary == "Rewritten."

    def test_a_submitted_version_is_frozen_in_the_form(self, admin_client, policy_in_force, admin):
        draft = policy_in_force.new_version(admin)
        draft.change_summary = "Reviewed."
        draft.save()
        draft.transition_to(VERSION_IN_REVIEW, admin)
        original = draft.content
        response = admin_client.post(reverse("documents:policyversion-update", args=[draft.pk]), {
            "version_label": "9.9", "content": "<p>Tampered</p>", "change_summary": "Tampered",
        })
        assert response.status_code == 200
        assert "frozen" in response.content.decode()
        draft.refresh_from_db()
        assert draft.content == original and draft.version_label != "9.9"

    def test_new_version_opens_the_new_draft(self, admin_client, policy_in_force):
        response = admin_client.post(
            reverse("documents:policy-new-version", args=[policy_in_force.pk]), {"bump": "major"}, **HTMX_DRAWER,
        )
        assert response.status_code == 204
        draft = policy_in_force.versions.get(workflow_state=VERSION_DRAFT)
        assert draft.version_label == "2.0"
        assert response["HX-Redirect"] == reverse("documents:policyversion-detail", args=[draft.pk])

    def test_record_review_needs_the_approve_permission(self, policy_in_force):
        reader = _client(_user("documents.policy.read", "documents.policy.update"))
        url = reverse("documents:policy-record-review", args=[policy_in_force.pk])
        assert reader.post(url, {"comment": "x"}).status_code == 302
        policy_in_force.refresh_from_db()
        before = policy_in_force.last_reviewed_at
        approver = _user("documents.policy.read", "documents.policy.approve")
        response = _client(approver).post(url, {"comment": "Checked against the 2026 risk review."})
        assert response.status_code == 302
        policy_in_force.refresh_from_db()
        assert policy_in_force.last_reviewed_by == approver and policy_in_force.last_reviewed_at != before

    def test_an_active_document_cannot_be_deleted(self, admin_client, policy_in_force):
        admin_client.post(reverse("documents:policy-delete", args=[policy_in_force.pk]))
        assert Policy.objects.filter(pk=policy_in_force.pk).exists()

    def test_a_draft_document_is_deleted_with_its_draft_versions(self, admin_client):
        version = PolicyVersionFactory()
        admin_client.post(reverse("documents:policy-delete", args=[version.policy.pk]))
        assert not Policy.objects.filter(pk=version.policy.pk).exists()
        assert not PolicyVersion.objects.filter(pk=version.pk).exists()


class TestPdfDownload:
    def test_attached_pdf_is_served_as_an_attachment(self, admin_client, policy_in_force, admin):
        version = policy_in_force.new_version(admin)
        version.set_pdf(PDF, 'signed "copy".pdf')
        version.save()
        response = admin_client.get(reverse("documents:policyversion-pdf", args=[version.pk]))
        assert response.status_code == 200
        assert response["Content-Type"] == "application/pdf"
        assert response["Content-Disposition"].startswith("attachment;")
        assert '"copy"' not in response["Content-Disposition"]
        assert response.content == PDF

    def test_rich_text_is_rendered_when_no_pdf_is_attached(self, admin_client, policy_in_force):
        version = policy_in_force.version_in_force
        with mock.patch("documents.rendering.render_version_pdf", return_value=b"%PDF-rendered") as render:
            response = admin_client.get(reverse("documents:policyversion-pdf", args=[version.pk]))
        render.assert_called_once()
        assert response.content == b"%PDF-rendered"
        assert f"{policy_in_force.reference}-v{version.version_label}.pdf" in response["Content-Disposition"]

    def test_a_missing_renderer_is_a_message_not_a_500(self, admin_client, policy_in_force):
        version = policy_in_force.version_in_force
        with mock.patch("documents.rendering.render_version_pdf", side_effect=OSError("no pango")):
            response = admin_client.get(reverse("documents:policyversion-pdf", args=[version.pk]))
        assert response.status_code == 302

    def test_the_addressee_may_download_what_they_must_acknowledge(self, admin, policy_in_force):
        addressee = UserFactory()
        version = policy_in_force.version_in_force
        version_pk = version.pk
        _running_campaign(version, [addressee], admin)
        with mock.patch("documents.rendering.render_version_pdf", return_value=b"%PDF-x"):
            assert _client(addressee).get(reverse("documents:policyversion-pdf", args=[version_pk])).status_code == 200
            assert _client(UserFactory()).get(reverse("documents:policyversion-pdf", args=[version_pk])).status_code == 404

    def test_the_pdf_template_renders(self, policy_in_force):
        version = policy_in_force.version_in_force
        html = render_to_string("documents/pdf/version.html", {"version": version, "policy": policy_in_force, "content": "<p>x</p>"})
        assert policy_in_force.title in html and version.version_label in html and "running-ref" in html


# --- Campaigns ----------------------------------------------------------------


class TestCampaigns:
    def test_create_defaults_to_the_document_scopes(self, admin_client, policy_in_force):
        scope = ScopeFactory()
        policy_in_force.scopes.set([scope])
        version = policy_in_force.version_in_force
        response = admin_client.post(reverse("documents:campaign-create"), {
            "name": "All staff", "policy_version": version.pk,
            "due_date": (timezone.localdate() + timezone.timedelta(days=10)).isoformat(),
            "statement": "I have read {title} version {label}.",
            "audience_users": [UserFactory().pk],
        })
        assert response.status_code == 302, response.content.decode()[:2000]
        campaign = AcknowledgementCampaign.objects.get(name="All staff")
        assert list(campaign.scopes.all()) == [scope]

    def test_the_picker_offers_only_versions_in_force(self, admin_client, policy_in_force, admin):
        draft = policy_in_force.new_version(admin)
        html = admin_client.get(reverse("documents:campaign-create")).content.decode()
        assert str(policy_in_force.version_in_force.pk) in html and str(draft.pk) not in html

    def test_a_launched_campaign_is_frozen(self, admin_client, admin, policy_in_force):
        campaign = _running_campaign(policy_in_force.version_in_force, [admin], admin)
        response = admin_client.post(reverse("documents:campaign-update", args=[campaign.pk]), {
            "name": "Renamed", "policy_version": campaign.policy_version_id, "due_date": campaign.due_date.isoformat(),
            "statement": campaign.statement,
        })
        assert response.status_code == 200
        campaign.refresh_from_db()
        assert campaign.name != "Renamed"

    def test_add_newcomers_creates_the_missing_rows(self, admin, policy_in_force):
        group = GroupFactory()
        first = UserFactory()
        group.users.add(first)
        campaign = AcknowledgementCampaignFactory(policy_version=policy_in_force.version_in_force)
        campaign.audience_groups.set([group])
        campaign.transition_to(CAMPAIGN_RUNNING, admin)
        group.users.add(UserFactory())
        client = _client(_user("documents.acknowledgement.read", "documents.acknowledgement.update"))
        response = client.post(reverse("documents:campaign-add-newcomers", args=[campaign.pk]))
        assert response.status_code == 302
        assert campaign.acknowledgements.count() == 2
        assert client.get(reverse("documents:campaign-add-newcomers", args=[campaign.pk])).status_code == 405

    def test_excuse_records_the_reason_and_needs_the_update_permission(self, admin, policy_in_force):
        person = UserFactory()
        campaign = _running_campaign(policy_in_force.version_in_force, [person], admin)
        row = campaign.acknowledgements.get()
        url = reverse("documents:acknowledgement-excuse", args=[row.pk])
        assert _client(_user("documents.acknowledgement.read")).post(url, {"reason": "x"}).status_code == 302
        row.refresh_from_db()
        assert row.status == AcknowledgementStatus.PENDING
        owner = _user("documents.acknowledgement.read", "documents.acknowledgement.update")
        assert _client(owner).post(url, {"reason": ""}).status_code == 200
        response = _client(owner).post(url, {"reason": "Left the company."}, **HTMX_DRAWER)
        assert response.status_code == 204
        row.refresh_from_db()
        assert row.status == AcknowledgementStatus.EXCUSED and row.excused_by == owner

    def test_campaign_detail_filters_the_audience(self, admin_client, admin, policy_in_force):
        people = [UserFactory(first_name="Ackno"), UserFactory(first_name="Pendi")]
        campaign = _running_campaign(policy_in_force.version_in_force, people, admin)
        campaign.acknowledgements.get(user=people[0]).acknowledge(people[0])
        url = reverse("documents:acknowledgementcampaign-detail", args=[campaign.pk])
        everyone = admin_client.get(url).content.decode()
        pending = admin_client.get(url + "?ack_status=pending").content.decode()
        # Each person is named once in the audience definition, once per table row.
        assert everyone.count(people[0].display_name) == 2
        assert pending.count(people[0].display_name) == 1
        assert pending.count(people[1].display_name) == 2


# --- To acknowledge (RG-DOC-16, RG-DOC-17, RG-DOC-22) -------------------------


class TestAcknowledge:
    def test_a_user_without_any_permission_acknowledges_their_own_row(self, admin, policy_in_force):
        person = UserFactory()
        campaign = _running_campaign(policy_in_force.version_in_force, [person], admin)
        row = campaign.acknowledgements.get()
        client = _client(person)
        html = client.get(reverse("documents:acknowledge-list")).content.decode()
        assert policy_in_force.title in html
        page = client.get(reverse("documents:acknowledge", args=[row.pk])).content.decode()
        assert campaign.statement_for() in page
        response = client.post(reverse("documents:acknowledge", args=[row.pk]))
        assert response.status_code == 302
        row.refresh_from_db()
        assert row.status == AcknowledgementStatus.ACKNOWLEDGED
        assert row.channel == AcknowledgementChannel.WEB and row.statement == campaign.statement_for()
        # Write-once : a second acknowledgement is refused, the row is unchanged.
        stamped = row.acknowledged_at
        client.post(reverse("documents:acknowledge", args=[row.pk]))
        row.refresh_from_db()
        assert row.acknowledged_at == stamped

    def test_someone_else_row_is_a_404_even_for_an_administrator(self, admin, admin_client, policy_in_force):
        person = UserFactory()
        campaign = _running_campaign(policy_in_force.version_in_force, [person], admin)
        row = campaign.acknowledgements.get()
        assert admin_client.get(reverse("documents:acknowledge", args=[row.pk])).status_code == 404
        assert admin_client.post(reverse("documents:acknowledge", args=[row.pk])).status_code == 404
        row.refresh_from_db()
        assert row.is_pending

    def test_own_rows_are_visible_outside_the_user_scopes(self, admin, policy_in_force):
        policy_in_force.scopes.set([ScopeFactory()])
        person = _user("documents.policy.read", scopes=[ScopeFactory()])
        campaign = _running_campaign(policy_in_force.version_in_force, [person], admin)
        client = _client(person)
        assert policy_in_force.title in client.get(reverse("documents:acknowledge-list")).content.decode()
        row = campaign.acknowledgements.get()
        assert client.get(reverse("documents:acknowledge", args=[row.pk])).status_code == 200

    def test_the_user_menu_counts_pending_rows(self, admin, policy_in_force):
        person = UserFactory()
        _running_campaign(policy_in_force.version_in_force, [person], admin)
        html = _client(person).get(reverse("documents:acknowledge-list")).content.decode()
        assert reverse("documents:acknowledge-list") in html
        assert "1 document to acknowledge" in html
        assert PolicyAcknowledgement.objects.filter(user=person, status=AcknowledgementStatus.PENDING).count() == 1


class TestNavigation:
    def test_sidebar_section_is_permission_gated(self, policy_in_force):
        reader = _client(_user("documents.policy.read"))
        html = reader.get(reverse("documents:acknowledge-list")).content.decode()
        assert reverse("documents:policy-list") in html
        assert reverse("documents:campaign-list") not in html
        nobody = _client(UserFactory()).get(reverse("documents:acknowledge-list")).content.decode()
        assert reverse("documents:policy-list") not in nobody
