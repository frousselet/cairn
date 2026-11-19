# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""Workshop 0 of an EBIOS RM study : the study framework.

What every form of the usability standard does is checked for all of them in
``core/tests/test_usability_standard.py``, and what a workshop page does in
``test_ebios_w1_completion.py``. This file holds what is particular to
workshop 0 : the study framework is edited one card at a time, the people from
outside are typed one per line and held to their shape on every surface, and
the workshop is validated once the study says what it is for and how far it
goes.
"""

import json

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import Permission
from accounts.tests.factories import GroupFactory, UserFactory
from compliance.tests.factories import FrameworkFactory
from core.completeness import completeness_of
from risks.constants import EbiosWorkshopNumber
from risks.forms_ebios import (
    StudyFrameworkForm,
    external_participants_as_lines,
    external_participants_from_lines,
)
from risks.models import StudyFramework
from risks.tests.factories import EbiosAssessmentFactory

pytestmark = pytest.mark.django_db

DRAWER = {"HTTP_HX_REQUEST": "true", "HTTP_HX_TARGET": "drawer-form-content"}

RENARD = {"name": "C. Renard", "role": "facilitator", "organization": "Astreinte Conseil"}


@pytest.fixture
def admin(client):
    user = UserFactory(is_superuser=True)
    client.force_login(user)
    return user


def _user_with(*codenames):
    user = UserFactory(is_superuser=False)
    group = GroupFactory()
    group.permissions.set(Permission.objects.filter(codename__in=codenames))
    group.users.add(user)
    return user


def _study(**kwargs):
    """A study, its study framework and the page of its workshop 0."""
    assessment = EbiosAssessmentFactory(**kwargs)
    workshop = assessment.ebios_workshops.get(workshop_number=EbiosWorkshopNumber.W0)
    return assessment, assessment.ebios_study_framework, workshop


def _edit(framework):
    return reverse("risks:ebios-study-framework-update", kwargs={"pk": framework.pk})


def _mcp(user, tool, arguments):
    from mcp.server import McpServer
    from mcp.tools import register_all_tools

    server = McpServer()
    register_all_tools(server)
    answer = server.handle_request(json.dumps({
        "jsonrpc": "2.0", "id": 1, "method": "tools/call",
        "params": {"name": tool, "arguments": arguments},
    }), user)
    return json.loads(answer["result"]["content"][0]["text"])


class TestTheStudyFramework:
    def test_its_form_has_a_section_for_each_card_of_the_page(self, admin):
        _assessment, framework, _workshop = _study()

        assert StudyFrameworkForm.section_keys() == ["mission", "perimeters", "participants", "conditions"]
        assert list(StudyFrameworkForm(instance=framework, user=admin, section="participants").fields) == [
            "participants", "applicable_frameworks", "external_participants",
        ]

    def test_a_card_sets_its_own_fields_and_leaves_the_others(self, client, admin):
        _assessment, framework, workshop = _study()
        framework.business_perimeter = "<p>Electricity generation.</p>"
        framework.save()

        response = client.post(
            _edit(framework),
            {"_section": "mission", "mission_statement": "<p>Know what could <strong>stop</strong> production.</p>"},
            **DRAWER,
        )
        html = client.get(workshop.get_absolute_url()).content.decode()

        framework.refresh_from_db()
        assert response.status_code == 204, response.content.decode()[:400]
        assert framework.business_perimeter == "<p>Electricity generation.</p>"
        # What was typed in the editor is shown formatted, not with its tags.
        assert "Know what could <strong>stop</strong> production." in html and "&lt;p&gt;" not in html
        for section in ("mission", "perimeters", "participants", "conditions"):
            assert f'?section={section}"' in html

    def test_the_internal_participants_are_picked_among_the_active_accounts(self, admin):
        _assessment, framework, _workshop = _study()
        here, gone, former = UserFactory(), UserFactory(is_active=False), UserFactory(is_active=False)
        framework.participants.add(former)

        offered = set(StudyFrameworkForm(instance=framework, user=admin).fields["participants"].queryset)

        # Whoever already takes part stays, even once their account is closed.
        assert here in offered and former in offered and gone not in offered

    def test_the_applicable_frameworks_are_picked_among_the_validated_ones(self, admin):
        _assessment, framework, _workshop = _study()
        draft, validated, held = FrameworkFactory(), FrameworkFactory(workflow_state="validated"), FrameworkFactory()
        framework.applicable_frameworks.add(held)

        offered = set(StudyFrameworkForm(instance=framework, user=admin).fields["applicable_frameworks"].queryset)

        assert validated in offered and held in offered and draft not in offered


class TestTheExternalParticipants:
    def test_they_are_typed_one_per_line(self, client, admin):
        """The field was written by the REST API alone : the page neither showed nor set it."""
        _assessment, framework, workshop = _study()

        response = client.post(
            _edit(framework),
            {"_section": "participants",
             "external_participants": "C. Renard, facilitator, Astreinte Conseil\r\n\r\nM. Petit\r\n"},
            **DRAWER,
        )
        html = client.get(workshop.get_absolute_url()).content.decode()

        framework.refresh_from_db()
        assert response.status_code == 204, response.content.decode()[:400]
        assert framework.participants_external == [RENARD, {"name": "M. Petit", "role": "", "organization": ""}]
        assert "C. Renard" in html and "facilitator" in html and "(Astreinte Conseil)" in html

    def test_what_is_shown_reads_back_as_it_was(self):
        people = [
            RENARD,
            {"name": "Renard, Claire", "role": "", "organization": "Astreinte Conseil"},
            {"name": 'Jean "Jeannot" Petit', "role": "expert, industrial systems", "organization": ""},
            {"name": "M. Petit", "role": "", "organization": ""},
            {"name": "A. Roux", "role": "auditor", "organization": "Cabinet Roux, Paris"},
        ]

        lines = external_participants_as_lines(people)

        assert lines.splitlines()[0] == "C. Renard, facilitator, Astreinte Conseil"
        assert lines.splitlines()[3] == "M. Petit"
        assert external_participants_from_lines(lines) == people

    def test_what_follows_the_second_comma_is_the_organisation(self):
        assert external_participants_from_lines("A. Roux, auditor, Cabinet Roux, Paris\n \n") == [
            {"name": "A. Roux", "role": "auditor", "organization": "Cabinet Roux, Paris"},
        ]

    def test_saving_the_card_as_it_is_leaves_a_list_set_through_the_api(self, client, admin):
        _assessment, framework, _workshop = _study()
        stored = [{"name": "  C. Renard ", "role": "facilitator"}]
        StudyFramework.objects.filter(pk=framework.pk).update(participants_external=stored)
        framework.refresh_from_db()
        shown = StudyFrameworkForm(instance=framework, user=admin, section="participants").initial["external_participants"]

        response = client.post(_edit(framework), {"_section": "participants", "external_participants": shown}, **DRAWER)

        framework.refresh_from_db()
        assert shown == "C. Renard, facilitator"
        assert response.status_code == 204, response.content.decode()[:400]
        assert framework.participants_external == stored

    @pytest.mark.parametrize("typed, message", [
        (", facilitator, Astreinte Conseil", "An external participant needs a name."),
        ('"C. Renard, facilitator', "The quotation marks of a line do not match"),
        ('"C. Renard" (Astreinte Conseil), facilitator', "The quotation marks of a line do not match"),
        ("C. Renard, " + "x" * 151, "are limited to 150 characters."),
    ])
    def test_a_line_that_cannot_be_read_is_refused(self, client, admin, typed, message):
        _assessment, framework, _workshop = _study()

        response = client.post(
            _edit(framework), {"_section": "participants", "external_participants": typed}, **DRAWER,
        )

        framework.refresh_from_db()
        assert response.status_code == 200 and message in response.content.decode()
        assert framework.participants_external == []

    def test_the_page_reads_a_list_of_another_shape_without_failing(self, client, admin):
        """A row written before the shape was held is read for what it has."""
        _assessment, framework, workshop = _study()
        StudyFramework.objects.filter(pk=framework.pk).update(participants_external=[
            "C. Renard", {"role": "facilitator"}, {"name": 5}, {"name": "<b>Eve</b>", "role": ["x"]}, None,
        ])

        response = client.get(workshop.get_absolute_url())
        html = response.content.decode()

        assert response.status_code == 200
        assert "&lt;b&gt;Eve&lt;/b&gt;" in html and "<b>Eve</b>" not in html

    def test_the_rest_api_holds_them_to_their_shape(self, admin):
        _assessment, framework, _workshop = _study()
        api = APIClient()
        api.force_authenticate(user=admin)
        url = f"/api/v1/risks/ebios/study-frameworks/{framework.pk}/"

        for refused in (
            "C. Renard",
            [["C. Renard"]],
            [{"role": "facilitator"}],
            [{"name": "  "}],
            [{"name": 5}],
            [{"name": "C. Renard", "email": "c.renard@example.org"}],
            [{"name": "C. Renard", "role": "x" * 151}],
            [{"name": f"Person {n}"} for n in range(51)],
        ):
            response = api.patch(url, {"participants_external": refused}, format="json")
            assert response.status_code == 400, refused
            assert "participants_external" in response.json()["error"], refused
        accepted = api.patch(url, {"participants_external": [RENARD, {"name": "M. Petit"}]}, format="json")

        framework.refresh_from_db()
        assert accepted.status_code == 200, accepted.content
        assert framework.participants_external == [RENARD, {"name": "M. Petit"}]
        assert framework.external_participant_list[1] == {"name": "M. Petit", "role": "", "organization": ""}

    def test_the_mcp_server_sets_who_takes_part_and_what_applies(self, admin):
        """The participants and the applicable frameworks were set by the page and the REST API only."""
        _assessment, framework, _workshop = _study()
        person, applied = UserFactory(), FrameworkFactory(workflow_state="validated")

        answer = _mcp(admin, "update_ebios_study_framework", {
            "id": str(framework.pk), "participant_ids": [str(person.pk)],
            "participants_external": [RENARD], "applicable_framework_ids": [str(applied.pk)],
        })
        refused = _mcp(admin, "update_ebios_study_framework", {
            "id": str(framework.pk), "participants_external": [{"role": "facilitator"}],
        })

        framework.refresh_from_db()
        assert "error" not in json.dumps(answer).lower(), answer
        assert list(framework.participants.all()) == [person]
        assert list(framework.applicable_frameworks.all()) == [applied]
        assert "An external participant needs a name." in json.dumps(refused)
        assert framework.participants_external == [RENARD]


class TestThePageOfTheWorkshop:
    def test_each_card_names_what_it_holds(self, client, admin):
        _assessment, framework, workshop = _study()
        person, applied = UserFactory(first_name="Elise", last_name="Moreau"), FrameworkFactory(name="ISO 27001")
        framework.participants.add(person)
        framework.applicable_frameworks.add(applied)

        html = client.get(workshop.get_absolute_url()).content.decode()

        for title in ("Mission statement", "Perimeters of the study", "Participants and applicable frameworks",
                      "Assumptions, constraints and expected deliverables"):
            assert title in html
        assert framework.reference in html
        assert "Elise Moreau" in html and "ISO 27001" in html

    def test_a_reader_is_offered_nothing_to_change(self, client):
        _assessment, framework, workshop = _study()
        client.force_login(_user_with("risks.ebios_assessment.read"))

        response = client.get(workshop.get_absolute_url())
        refused = client.get(_edit(framework))

        assert response.status_code == 200
        assert "/edit/" not in response.content.decode().split('id="mission-statement"')[1]
        # Sent back with a message, the way every page of the product refuses.
        assert refused.status_code == 302


class TestWhatTheWorkshopStillNeeds:
    def test_a_new_study_lists_what_workshop_0_needs(self, client, admin):
        _assessment, _framework, workshop = _study()

        report = completeness_of(workshop)
        html = client.get(workshop.get_absolute_url()).content.decode()

        assert [item.key for item in report.blocking_missing] == ["w0_mission", "w0_perimeters"]
        assert [item.key for item in report.advised_missing] == ["w0_participants", "w0_frameworks"]
        for anchor in ("mission-statement", "perimeters", "participants"):
            assert f'href="{workshop.get_absolute_url()}#{anchor}"' in html and f'id="{anchor}"' in html

    def test_the_three_perimeters_are_asked(self):
        _assessment, framework, workshop = _study()
        framework.mission_statement = "<p>Know what could stop production.</p>"
        framework.business_perimeter = "<p>Electricity generation.</p>"
        framework.technical_perimeter = "<p>Supervision and plant networks.</p>"
        framework.temporal_perimeter = "<p><br></p>"  # an emptied editor
        framework.save()

        still = [item.key for item in completeness_of(workshop).blocking_missing]
        framework.temporal_perimeter = "<p>The strategic cycle 2026-2027.</p>"
        framework.save()

        assert still == ["w0_perimeters"]
        assert completeness_of(workshop).blocking_missing == []

    def test_a_person_from_outside_is_a_participant(self):
        _assessment, framework, workshop = _study()
        framework.participants_external = [RENARD]
        framework.save()

        assert "w0_participants" not in [item.key for item in completeness_of(workshop).advised_missing]

    def test_it_is_not_validated_before_the_study_says_what_it_is_for_and_how_far_it_goes(self, client, admin):
        assessment, framework, workshop = _study()
        type(workshop).objects.filter(pk=workshop.pk).update(workflow_state="under_review")
        url = reverse("risks:ebios-workshop-validate", kwargs={"assessment_pk": assessment.pk, "workshop_pk": workshop.pk})

        refused = client.post(url, follow=True)
        workshop.refresh_from_db()
        state = workshop.workflow_state
        framework.mission_statement = "<p>Know what could stop production.</p>"
        framework.business_perimeter = "<p>Electricity generation.</p>"
        framework.technical_perimeter = "<p>Supervision and plant networks.</p>"
        framework.temporal_perimeter = "<p>The strategic cycle 2026-2027.</p>"
        framework.save()
        client.post(url)
        workshop.refresh_from_db()

        assert state == "under_review"
        assert "fill in the mission statement" in refused.content.decode()
        assert workshop.workflow_state == "validated"
