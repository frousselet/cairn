# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""An evidence item is registered short, then completed and sealed on its page.

What every form of the usability standard owes (its size, its helpers, its
labels) is checked in ``core/tests/test_usability_standard.py``. The item is
created from the incident file, so its page is tested here : the dialog asks
what it is, when, by whom and from where it was collected, its type never
answered for the reader; it lands on the item; the registration of the
acquisition waits for its origin (GE-01) and the seal for the digest and the
collection method (GE-02), on every surface, and a refused seal stamps no
sealing time; each card opens its section; the texts typed in the editor are
shown formatted.
"""

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.tests.factories import UserFactory
from core.completeness import completeness_of
from core.lifecycle import DomainRefusalError
from incidents.forms import IncidentEvidenceCreateForm, IncidentEvidenceForm
from incidents.models import IncidentEvidence
from incidents.tests.factories import IncidentEvidenceFactory, IncidentFactory
from incidents.tests.helpers import EVIDENCE_COLLECTED, EVIDENCE_SECURED, collected_evidence, walk

pytestmark = pytest.mark.django_db

DRAWER = {"HTTP_HX_REQUEST": "true", "HTTP_HX_TARGET": "drawer-form-content"}


@pytest.fixture
def admin(client):
    user = UserFactory(is_superuser=True)
    client.force_login(user)
    return user


def _missing(record):
    report = completeness_of(record)
    return [item.key for item in report.blocking_missing], [item.key for item in report.advised_missing]


class TestAnItemIsRegisteredShort:
    def test_it_asks_what_when_by_whom_and_from_where(self, admin):
        form = IncidentEvidenceCreateForm(incident=IncidentFactory(), collected_by=admin, user=admin)
        evidence_type = form.fields["evidence_type"]

        assert sorted(form.fields) == [
            "collected_at", "collected_by", "evidence_type", "source_description", "source_support_asset", "title",
        ]
        assert form.is_multistep is False
        # Collected now, by whoever registers it, unless the reader says otherwise.
        assert form.initial["collected_at"] is not None and form.fields["collected_by"].initial == admin
        assert evidence_type.required and [value for value, _label in evidence_type.choices][0] == ""

    def test_the_dialog_lands_on_the_item(self, client, admin):
        incident = IncidentFactory()

        response = client.post(reverse("incidents:evidence-create", args=[incident.pk]), {
            "title": "Memory image - WEB-PRD-02", "evidence_type": "memory_dump",
            "collected_at": "2026-01-01T10:00", "collected_by": admin.pk,
            "source_description": "WEB-PRD-02, production web front end",
        }, **DRAWER)
        item = IncidentEvidence.objects.get()

        assert response.status_code == 204 and response["HX-Redirect"] == item.get_absolute_url()
        assert (item.incident, item.collected_by, item.workflow_state) == (incident, admin, "draft")
        # Ready to be registered; the seal's needs are asked once it is.
        assert _missing(item) == ([], ["retention_until"])


class TestWhatTheRegisterWaitsFor:
    def test_the_acquisition_is_not_registered_without_its_origin(self, admin):
        item = IncidentEvidenceFactory(collected_by=admin)

        with pytest.raises(DomainRefusalError) as refusal:
            item.transition_to(EVIDENCE_COLLECTED, admin)

        assert _missing(item)[0] == ["source"]
        assert "choose the source asset or fill in the source" in str(refusal.value)

    def test_the_seal_waits_for_the_hash_and_the_method_and_stamps_nothing(self, admin):
        item = collected_evidence(IncidentFactory(), admin)

        with pytest.raises(DomainRefusalError) as refusal:
            item.transition_to(EVIDENCE_SECURED, admin)

        assert _missing(item)[0] == ["content_hash", "collection_method"]
        assert "fill in the content hash" in str(refusal.value)
        # A refused seal leaves no sealing time on the record, saved or not.
        assert item.sealed_at is None
        item.refresh_from_db()
        assert item.sealed_at is None and item.workflow_state == EVIDENCE_COLLECTED

    def test_the_seal_is_reached_once_both_are_stated(self, admin):
        item = collected_evidence(IncidentFactory(), admin)
        item.content_hash = "a" * 64
        item.collection_method = "<p>dd 8.32 through a write blocker.</p>"
        item.save()

        walk(item, EVIDENCE_SECURED, user=admin)

        assert item.is_sealed and item.workflow_state == EVIDENCE_SECURED


class TestThePageOfTheItem:
    def test_it_lists_what_is_missing_and_opens_each_card(self, client, admin):
        item = collected_evidence(IncidentFactory(), admin)
        edit = reverse("incidents:evidence-update", args=[item.pk])

        html = client.get(item.get_absolute_url()).content.decode()

        assert "Fill in the content hash" in html and "Fill in the collection method" in html
        for key in IncidentEvidenceForm.section_keys():
            assert f'{edit}?section={key}"' in html, key

    def test_the_texts_typed_in_the_editor_are_shown_formatted(self, client, admin):
        item = IncidentEvidenceFactory(
            description="<p>The <b>attacker</b> session.</p><script>x()</script>",
            collection_method="<p>Imaged with <i>LiME</i>.</p>",
        )

        html = client.get(item.get_absolute_url()).content.decode()

        assert "<b>attacker</b>" in html and "<i>LiME</i>" in html
        assert "&lt;p&gt;" not in html and "<script>x()</script>" not in html

    def test_a_reader_is_offered_no_edit(self, client):
        item = IncidentEvidenceFactory()
        reader = UserFactory()
        reader.is_superuser = False
        reader.save()
        from accounts.models import Group, Permission

        group = Group.objects.create(name="Evidence readers")
        group.permissions.set(Permission.objects.filter(codename__in=["incidents.evidence.read", "incidents.incident.read"]))
        group.users.add(reader)
        client.force_login(reader)

        response = client.get(item.get_absolute_url())

        assert response.status_code == 200
        assert reverse("incidents:evidence-update", args=[item.pk]) not in response.content.decode()


class TestTheOtherSurfaces:
    def test_the_rest_api_and_the_mcp_server_say_what_the_seal_waits_for(self, admin):
        from mcp.server import McpServer
        from mcp.tools import register_all_tools

        item = collected_evidence(IncidentFactory(), admin)
        api = APIClient()
        api.force_authenticate(user=admin)
        server = McpServer()
        register_all_tools(server)

        body = api.get(f"/api/v1/incidents/evidence/{item.pk}/").json()
        body = body.get("data", body)
        sealed = api.post(
            f"/api/v1/incidents/evidence/{item.pk}/transition/", {"target_state": EVIDENCE_SECURED}, format="json",
        )
        read = server.get_tool("get_incident_evidence")["handler"](admin, {"id": str(item.pk)})

        blocking = ["content_hash", "collection_method"]
        assert [entry["key"] for entry in body["completeness"]["missing"] if entry["blocking"]] == blocking
        assert [entry["key"] for entry in read["completeness"]["missing"] if entry["blocking"]] == blocking
        assert sealed.status_code == 400 and "fill in the content hash" in sealed.content.decode()
