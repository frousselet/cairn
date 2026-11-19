# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""Workshop 2 of an EBIOS RM study : risk sources, their targeted objectives and the pairs.

What every form of the usability standard does is checked for all of them in
``core/tests/test_usability_standard.py``, and what a workshop page does in
``test_ebios_w1_completion.py``. This file holds what is particular to
workshop 2 : the three ratings of a risk source read by name, an objective
targets what its own study holds, and a pair is named by its objective alone,
since an objective belongs to one risk source.
"""

import json

import pytest
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils import translation
from rest_framework.test import APIClient

from accounts.models import Permission
from accounts.tests.factories import GroupFactory, UserFactory
from assets.tests.factories import EssentialAssetFactory
from context.tests.factories import ScopeFactory
from core.completeness import completeness_of
from risks.constants import EbiosWorkshopNumber
from risks.forms_ebios import (
    RiskSourceCreateForm,
    RiskSourceForm,
    RiskSourceObjectivePairCreateForm,
    RiskSourceObjectivePairForm,
    TargetedObjectiveCreateForm,
    TargetedObjectiveForm,
)
from risks.models import RiskSource, RiskSourceObjectivePair, TargetedObjective
from risks.tests.factories import (
    EbiosAssessmentFactory,
    FearedEventFactory,
    RiskAssessmentFactory,
    RiskSourceFactory,
    RiskSourceObjectivePairFactory,
    TargetedObjectiveFactory,
)

pytestmark = pytest.mark.django_db

DRAWER = {"HTTP_HX_REQUEST": "true", "HTTP_HX_TARGET": "drawer-form-content"}


@pytest.fixture
def admin(client):
    user = UserFactory(is_superuser=True)
    client.force_login(user)
    return user


def _user_with(*codenames, scopes=()):
    user = UserFactory(is_superuser=False)
    group = GroupFactory()
    group.permissions.set(Permission.objects.filter(codename__in=codenames))
    for scope in scopes:
        group.allowed_scopes.add(scope)
    group.users.add(user)
    return user


def _study(**kwargs):
    """A study and the page of its workshop 2."""
    assessment = EbiosAssessmentFactory(**kwargs)
    return assessment, assessment.ebios_workshops.get(workshop_number=EbiosWorkshopNumber.W2)


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


class TestARiskSource:
    def test_creation_asks_its_name_its_category_and_its_three_ratings(self, admin):
        assessment, _workshop = _study()

        form = RiskSourceCreateForm(assessment=assessment, user=admin)

        assert list(form.fields) == ["name", "category", "motivation_level", "resources_level", "activity_level"]
        assert form.is_multistep is False
        # The category says what kind of attacker it is : "Other" is not chosen for the reader.
        assert form.fields["category"].required and form.fields["category"].choices[0][0] == ""
        assert not form.initial.get("category")

    def test_a_rating_reads_by_the_name_of_its_level_and_may_wait(self, admin):
        assessment, _workshop = _study()

        form = RiskSourceCreateForm(assessment=assessment, user=admin)

        assert [label for _value, label in form.fields["motivation_level"].choices] == [
            "Not assessed", "1 - Low", "2 - Moderate", "3 - High", "4 - Very high",
        ]
        assert [label for _value, label in form.fields["resources_level"].choices] == [
            "Not assessed", "1 - Limited", "2 - Moderate", "3 - Significant", "4 - Unlimited",
        ]
        assert not form.fields["activity_level"].required

    def test_the_levels_have_their_own_french(self):
        from risks.constants import MotivationLevel, ResourcesLevel

        with translation.override("fr"):
            assert str(MotivationLevel.MODERATE.label) == "2 - Modérée"
            assert str(ResourcesLevel.MODERATE.label) == "2 - Modérées"

    def test_it_is_added_from_the_side_panel_and_its_threat_level_follows(self, client, admin):
        assessment, _workshop = _study()

        response = client.post(
            reverse("risks:ebios-risk-source-create", kwargs={"assessment_pk": assessment.pk}),
            {"name": "A ransomware group", "category": "organized_crime", "motivation_level": "4",
             "resources_level": "3", "activity_level": ""},
            **DRAWER,
        )

        source = RiskSource.objects.get()
        assert response.status_code == 204, response.content.decode()[:400]
        assert response.headers["HX-Trigger"] == "formSaved"
        assert (source.assessment, source.created_by, source.threat_level, source.is_retained) == (
            assessment, admin, 4, True,
        )

    def test_one_without_ratings_is_not_assessed(self, client, admin):
        assessment, workshop = _study()

        client.post(
            reverse("risks:ebios-risk-source-create", kwargs={"assessment_pk": assessment.pk}),
            {"name": "A competitor", "category": "competitor", "motivation_level": "", "resources_level": "",
             "activity_level": ""},
        )
        html = client.get(workshop.get_absolute_url()).content.decode()

        assert RiskSource.objects.get().threat_level is None
        assert "Not assessed" in html

    def test_it_is_not_added_to_a_study_of_another_method(self, client, admin):
        other = RiskAssessmentFactory()

        response = client.get(reverse("risks:ebios-risk-source-create", kwargs={"assessment_pk": other.pk}))

        assert response.status_code == 404

    def test_editing_it_shows_everything_on_one_screen(self, client, admin):
        assessment, _workshop = _study()
        source = RiskSourceFactory(assessment=assessment)

        form = RiskSourceForm(instance=source, assessment=assessment, user=admin)
        response = client.post(
            reverse("risks:ebios-risk-source-update", kwargs={"pk": source.pk}),
            {"name": source.name, "category": "state", "description": "", "motivation_level": "2",
             "resources_level": "2", "activity_level": "3", "motivation_description": "",
             "retention_justification": "<p>Out of our sector.</p>"},
            **DRAWER,
        )

        source.refresh_from_db()
        assert form.is_multistep is False
        assert list(form.fields) == [
            "name", "category", "description", "motivation_level", "resources_level", "activity_level",
            "motivation_description", "is_retained", "retention_justification",
        ]
        assert response.status_code == 204, response.content.decode()[:400]
        # Unticked : set aside. Activity from level 3 raises the threat level by one.
        assert (source.is_retained, source.threat_level) == (False, 3)

    def test_it_is_removed_from_the_side_panel(self, client, admin):
        assessment, workshop = _study()
        source = RiskSourceFactory(assessment=assessment)

        response = client.post(reverse("risks:ebios-risk-source-delete", kwargs={"pk": source.pk}), **DRAWER)

        assert response.status_code == 204 and response.headers["HX-Redirect"] == workshop.get_absolute_url()
        assert not RiskSource.objects.filter(pk=source.pk).exists()


class TestATargetedObjective:
    def test_creation_asks_its_name_its_category_and_the_feared_events_it_would_cause(self, admin):
        assessment, _workshop = _study()
        source = RiskSourceFactory(assessment=assessment)

        form = TargetedObjectiveCreateForm(risk_source=source, user=admin)

        assert list(form.fields) == ["name", "category", "targeted_feared_events"]
        assert form.is_multistep is False
        assert form.fields["category"].required and not form.initial.get("category")

    def test_it_targets_what_its_own_study_holds(self, admin):
        """The pickers listed the feared events and the essential assets of every study."""
        assessment, _workshop = _study()
        other, _other_workshop = _study()
        ours = FearedEventFactory(baseline=assessment.ebios_security_baseline)
        theirs = FearedEventFactory(baseline=other.ebios_security_baseline)
        studied, elsewhere = EssentialAssetFactory(), EssentialAssetFactory()
        assessment.ebios_security_baseline.essential_assets.add(studied)
        source = RiskSourceFactory(assessment=assessment)

        form = TargetedObjectiveForm(risk_source=source, user=admin)

        assert list(form.fields["targeted_feared_events"].queryset) == [ours] and theirs.pk
        assert list(form.fields["targeted_essential_assets"].queryset) == [studied] and elsewhere.pk

    def test_it_is_added_under_its_risk_source_and_comes_last(self, client, admin):
        assessment, _workshop = _study()
        source = RiskSourceFactory(assessment=assessment)
        event = FearedEventFactory(baseline=assessment.ebios_security_baseline)
        url = reverse("risks:ebios-targeted-objective-create", kwargs={"risk_source_pk": source.pk})

        first = client.post(url, {"name": "Extort money", "category": "lucrative",
                                  "targeted_feared_events": [str(event.pk)]}, **DRAWER)
        client.post(url, {"name": "Resell the data", "category": "lucrative"}, **DRAWER)

        objectives = list(source.targeted_objectives.order_by("order"))
        assert first.status_code == 204, first.content.decode()[:400]
        assert [(o.name, o.order) for o in objectives] == [("Extort money", 1), ("Resell the data", 2)]
        assert list(objectives[0].targeted_feared_events.all()) == [event]
        assert objectives[0].created_by == admin

    def test_a_risk_source_of_another_scope_is_an_unknown_one(self, client):
        mine, theirs = ScopeFactory(), ScopeFactory()
        assessment, _workshop = _study(scopes=[theirs])
        source = RiskSourceFactory(assessment=assessment)
        client.force_login(_user_with("risks.ebios_risk_source.create", "risks.ebios_risk_source.read", scopes=[mine]))
        url = reverse("risks:ebios-targeted-objective-create", kwargs={"risk_source_pk": source.pk})

        assert client.get(url).status_code == 404
        assert client.post(url, {"name": "x", "category": "lucrative"}).status_code == 404
        assert not TargetedObjective.objects.exists()


class TestAPair:
    def test_creation_asks_the_objective_and_the_relevance(self, admin):
        assessment, _workshop = _study()
        TargetedObjectiveFactory(risk_source=RiskSourceFactory(assessment=assessment))

        form = RiskSourceObjectivePairCreateForm(assessment=assessment, user=admin)

        assert list(form.fields) == ["targeted_objective", "relevance"]
        # The risk source is not a question : an objective belongs to one.
        assert "risk_source" not in form.fields
        # The relevance is the judgment the pair exists for.
        assert form.fields["relevance"].required and not form.initial.get("relevance")

    def test_the_objectives_are_listed_under_their_risk_source_and_only_the_unpaired_ones(self, admin):
        assessment, _workshop = _study()
        other, _other_workshop = _study()
        crime = RiskSourceFactory(assessment=assessment, name="Organised crime")
        extort = TargetedObjectiveFactory(risk_source=crime, name="Extort money")
        resell = TargetedObjectiveFactory(risk_source=crime, name="Resell the data")
        TargetedObjectiveFactory(risk_source=RiskSourceFactory(assessment=other), name="Of another study")
        RiskSourceObjectivePairFactory(assessment=assessment, risk_source=crime, targeted_objective=extort)

        choices = RiskSourceObjectivePairCreateForm(assessment=assessment, user=admin).fields["targeted_objective"].choices

        assert choices[0][0] == ""
        assert [(group, [label for _pk, label in options]) for group, options in choices[1:]] == [
            (str(crime), [str(resell)]),
        ]

    def test_the_pair_takes_the_risk_source_of_its_objective(self, client, admin):
        assessment, _workshop = _study()
        source = RiskSourceFactory(assessment=assessment, motivation_level=4, resources_level=4)
        objective = TargetedObjectiveFactory(risk_source=source)

        response = client.post(
            reverse("risks:ebios-sr-ov-pair-create", kwargs={"assessment_pk": assessment.pk}),
            {"targeted_objective": str(objective.pk), "relevance": "medium"},
            **DRAWER,
        )

        pair = RiskSourceObjectivePair.objects.get()
        assert response.status_code == 204, response.content.decode()[:400]
        assert (pair.risk_source, pair.assessment, pair.created_by) == (source, assessment, admin)
        assert (pair.priority_score, pair.is_retained) == (4, True)

    def test_opened_from_an_objective_the_form_opens_on_it(self, client, admin):
        assessment, _workshop = _study()
        objective = TargetedObjectiveFactory(risk_source=RiskSourceFactory(assessment=assessment))
        stranger = TargetedObjectiveFactory()
        url = reverse("risks:ebios-sr-ov-pair-create", kwargs={"assessment_pk": assessment.pk})

        html = client.get(f"{url}?objective={objective.pk}", **DRAWER).content.decode()
        elsewhere = client.get(f"{url}?objective={stranger.pk}", **DRAWER).content.decode()

        assert f'<option value="{objective.pk}" selected>' in html
        assert "selected>" not in elsewhere.split('name="targeted_objective"')[1].split("</select>")[0].replace(
            '<option value="" selected>', "",
        )

    def test_an_existing_pair_keeps_its_objective(self, client, admin):
        pair = RiskSourceObjectivePairFactory()
        other = TargetedObjectiveFactory(risk_source=pair.risk_source)

        form = RiskSourceObjectivePairForm(instance=pair, assessment=pair.assessment, user=admin)
        response = client.post(
            reverse("risks:ebios-sr-ov-pair-update", kwargs={"pk": pair.pk}),
            {"targeted_objective": str(other.pk), "relevance": "low", "relevance_justification": "",
             "retention_justification": "<p>Not credible here.</p>"},
            **DRAWER,
        )

        pair.refresh_from_db()
        assert form.fields["targeted_objective"].disabled
        assert response.status_code == 204, response.content.decode()[:400]
        assert pair.targeted_objective != other
        assert (pair.relevance, pair.is_retained) == ("low", False)

    def test_a_pair_is_a_risk_source_and_one_of_its_own_objectives(self):
        pair = RiskSourceObjectivePairFactory()
        pair.targeted_objective = TargetedObjectiveFactory(
            risk_source=RiskSourceFactory(assessment=pair.assessment),
        )

        with pytest.raises(ValidationError) as refusal:
            pair.full_clean()

        assert "belongs to another risk source" in str(refusal.value)


class TestThePageOfTheWorkshop:
    def test_an_objective_is_listed_under_its_risk_source_with_its_pair_or_the_way_to_open_one(self, client, admin):
        assessment, workshop = _study()
        source = RiskSourceFactory(assessment=assessment, name="Organised crime")
        judged = TargetedObjectiveFactory(risk_source=source, name="Extort money")
        waiting = TargetedObjectiveFactory(risk_source=source, name="Resell the data")
        RiskSourceObjectivePairFactory(
            assessment=assessment, risk_source=source, targeted_objective=judged, relevance="critical",
        )
        new_pair = reverse("risks:ebios-sr-ov-pair-create", kwargs={"assessment_pk": assessment.pk})

        html = client.get(workshop.get_absolute_url()).content.decode()

        assert "Extort money" in html and "Resell the data" in html
        assert f'hx-get="{new_pair}?objective={waiting.pk}"' in html
        assert f"{new_pair}?objective={judged.pk}" not in html
        new_objective = reverse("risks:ebios-targeted-objective-create", kwargs={"risk_source_pk": source.pk})
        assert f'hx-get="{new_objective}"' in html

    def test_an_empty_workshop_says_what_to_do_first(self, client, admin):
        assessment, workshop = _study()
        new_source = reverse("risks:ebios-risk-source-create", kwargs={"assessment_pk": assessment.pk})
        new_pair = reverse("risks:ebios-sr-ov-pair-create", kwargs={"assessment_pk": assessment.pk})

        html = client.get(workshop.get_absolute_url()).content.decode()

        assert "No risk source yet." in html and f'hx-get="{new_source}"' in html
        # No objective yet : there is nothing to pair.
        assert "Add a risk source and its targeted objectives first." in html and new_pair not in html

    def test_a_reader_is_offered_nothing_to_change(self, client):
        pair = RiskSourceObjectivePairFactory()
        workshop = pair.assessment.ebios_workshops.get(workshop_number=EbiosWorkshopNumber.W2)
        client.force_login(_user_with("risks.ebios_assessment.read", "risks.ebios_risk_source.read"))

        html = client.get(workshop.get_absolute_url()).content.decode()

        assert pair.risk_source.name in html
        for fragment in ("/risk-sources/create/", "/objectives/create/", "/sr-ov-pairs/create/", "/edit/", "/delete/"):
            assert fragment not in html.split('id="risk-sources"')[1], fragment

    def test_the_french_names_the_attacker_not_the_origin_of_a_risk(self, client, admin):
        """"Risk source" was one message for two things : the attacker of the
        method, and where a risk of the register comes from ("source du risque")."""
        pair = RiskSourceObjectivePairFactory()
        workshop = pair.assessment.ebios_workshops.get(workshop_number=EbiosWorkshopNumber.W2)
        admin.language = "fr"
        admin.save()

        with translation.override("fr"):
            html = client.get(workshop.get_absolute_url(), HTTP_ACCEPT_LANGUAGE="fr").content.decode()
            label = str(TargetedObjective._meta.get_field("risk_source").verbose_name)

        assert label == "Source de risque"
        assert "Source du risque" not in html


class TestWhatTheWorkshopStillNeeds:
    def test_a_new_study_lists_what_workshop_2_needs(self, client, admin):
        _assessment, workshop = _study()

        report = completeness_of(workshop)
        html = client.get(workshop.get_absolute_url()).content.decode()

        assert [item.key for item in report.blocking_missing] == [
            "w2_risk_sources", "w2_targeted_objectives", "w2_retained_pair",
        ]
        assert report.advised_missing == []
        assert f'href="{workshop.get_absolute_url()}#risk-sources"' in html
        assert f'href="{workshop.get_absolute_url()}#pairs"' in html
        assert 'id="risk-sources"' in html and 'id="pairs"' in html

    def test_a_retained_source_that_is_not_rated_is_pointed_out(self):
        assessment, workshop = _study()
        RiskSourceFactory(assessment=assessment, motivation_level=None, resources_level=None)

        assert [item.key for item in completeness_of(workshop).advised_missing] == ["w2_threat_levels"]

    def test_it_is_not_validated_without_a_retained_pair(self, client, admin):
        pair = RiskSourceObjectivePairFactory(is_retained=False)
        assessment = pair.assessment
        workshop = assessment.ebios_workshops.get(workshop_number=EbiosWorkshopNumber.W2)
        type(workshop).objects.filter(pk=workshop.pk).update(workflow_state="under_review")
        url = reverse("risks:ebios-workshop-validate", kwargs={"assessment_pk": assessment.pk, "workshop_pk": workshop.pk})

        refused = client.post(url, follow=True)
        workshop.refresh_from_db()
        state = workshop.workflow_state
        RiskSourceObjectivePair.objects.filter(pk=pair.pk).update(is_retained=True)
        client.post(url)
        workshop.refresh_from_db()

        assert state == "under_review"
        assert "retain a pair of risk source and targeted objective" in refused.content.decode()
        assert workshop.workflow_state == "validated"


class TestTheApiAndTheMcpServer:
    def test_the_mcp_server_names_a_pair_by_its_objective(self, admin):
        assessment, _workshop = _study()
        source = RiskSourceFactory(assessment=assessment)
        objective = TargetedObjectiveFactory(risk_source=source)

        answer = _mcp(admin, "create_ebios_sr_ov_pair", {"targeted_objective_id": str(objective.pk), "relevance": "high"})

        pair = RiskSourceObjectivePair.objects.get()
        assert "error" not in json.dumps(answer).lower(), answer
        assert (pair.risk_source, pair.assessment) == (source, assessment)

    def test_the_mcp_server_refuses_a_pair_whose_source_is_not_the_one_of_its_objective(self, admin):
        assessment, _workshop = _study()
        objective = TargetedObjectiveFactory(risk_source=RiskSourceFactory(assessment=assessment))
        another = RiskSourceFactory(assessment=assessment)

        answer = _mcp(admin, "create_ebios_sr_ov_pair", {
            "targeted_objective_id": str(objective.pk), "risk_source_id": str(another.pk),
        })

        assert "belongs to another risk source" in json.dumps(answer)
        assert not RiskSourceObjectivePair.objects.exists()

    def test_the_rest_api_does_the_same(self, admin):
        assessment, _workshop = _study()
        source = RiskSourceFactory(assessment=assessment)
        objective = TargetedObjectiveFactory(risk_source=source)
        another = RiskSourceFactory(assessment=assessment)
        api = APIClient()
        api.force_authenticate(admin)

        refused = api.post("/api/v1/risks/ebios/sr-ov-pairs/", {
            "targeted_objective": str(objective.pk), "risk_source": str(another.pk), "relevance": "high",
        }, format="json")
        created = api.post("/api/v1/risks/ebios/sr-ov-pairs/", {
            "targeted_objective": str(objective.pk), "relevance": "high",
        }, format="json")

        assert refused.status_code == 400 and "another risk source" in json.dumps(refused.json())
        assert created.status_code == 201, created.content
        assert RiskSourceObjectivePair.objects.get().risk_source == source

    def test_the_mcp_server_sets_what_an_objective_targets(self, admin):
        """The feared events and the essential assets of an objective were set by the page and the REST API only."""
        assessment, _workshop = _study()
        objective = TargetedObjectiveFactory(risk_source=RiskSourceFactory(assessment=assessment))
        event = FearedEventFactory(baseline=assessment.ebios_security_baseline)

        answer = _mcp(admin, "update_ebios_targeted_objective", {
            "id": str(objective.pk), "targeted_feared_event_ids": [str(event.pk)],
            "targeted_essential_asset_ids": [str(event.essential_asset.pk)],
        })

        assert "error" not in json.dumps(answer).lower(), answer
        assert list(objective.targeted_feared_events.all()) == [event]
        assert list(objective.targeted_essential_assets.all()) == [event.essential_asset]

    def test_they_report_what_the_workshop_still_needs(self, admin):
        _assessment, workshop = _study()

        other = _mcp(admin, "get_ebios_workshop", {"id": str(workshop.pk)})

        assert [item["key"] for item in other["completeness"]["missing"]] == [
            "w2_risk_sources", "w2_targeted_objectives", "w2_retained_pair",
        ]
