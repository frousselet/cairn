# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""Workshop 1 of an EBIOS RM study : rows added on one screen, a page that says what is missing.

The records of a workshop are rows of its page : a feared event and a baseline
gap are added and edited in the side panel, the security baseline is edited
card by card. What every form of the usability standard does is checked for
all of them in ``core/tests/test_usability_standard.py``; this file holds what
is particular to the workshop : the baseline a row hangs under is never asked,
a feared event is about an essential asset of the study, its gravity is a
named level, and the workshop is validated on its deliverables.
"""

import json
from html import unescape

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import Permission
from accounts.tests.factories import GroupFactory, UserFactory
from assets.tests.factories import EssentialAssetFactory, SupportAssetFactory
from compliance.tests.factories import FrameworkFactory, RequirementFactory
from context.tests.factories import ActivityFactory, ScopeFactory
from core.completeness import completeness_of
from helpers.models import HelpContent
from risks.constants import EbiosWorkshopNumber
from risks.forms_ebios import (
    BaselineGapCreateForm,
    BaselineGapForm,
    FearedEventCreateForm,
    FearedEventForm,
    SecurityBaselineForm,
)
from risks.models import BaselineGap, FearedEvent
from risks.tests.factories import (
    BaselineGapFactory,
    EbiosAssessmentFactory,
    FearedEventFactory,
    RiskCriteriaFactory,
    ScaleLevelFactory,
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
    """A study, its security baseline and the page of its workshop 1."""
    assessment = EbiosAssessmentFactory(**kwargs)
    baseline = assessment.ebios_security_baseline
    workshop = assessment.ebios_workshops.get(workshop_number=EbiosWorkshopNumber.W1)
    return assessment, baseline, workshop


def _asset(**kwargs):
    return EssentialAssetFactory(workflow_state="identified", **kwargs)


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


class TestAFearedEvent:
    def test_creation_asks_the_asset_the_criterion_the_name_and_the_gravity(self, admin):
        _assessment, baseline, _workshop = _study()

        form = FearedEventCreateForm(baseline=baseline, user=admin)

        assert list(form.fields) == ["essential_asset", "dic_criterion", "name", "gravity_level"]
        assert form.is_multistep is False
        # The baseline it belongs to is known from the address : it is not a question.
        assert "baseline" not in form.fields

    def test_it_is_about_an_essential_asset_of_the_study(self, admin):
        _assessment, baseline, _workshop = _study()
        studied, elsewhere = _asset(name="Customer file"), _asset(name="Payroll")
        baseline.essential_assets.add(studied)

        offered = FearedEventCreateForm(baseline=baseline, user=admin).fields["essential_asset"].queryset

        assert list(offered) == [studied] and elsewhere not in offered

    def test_the_asset_an_event_already_names_stays_offered(self, admin):
        _assessment, baseline, _workshop = _study()
        event = FearedEventFactory(baseline=baseline)

        offered = FearedEventForm(instance=event, baseline=baseline, user=admin).fields["essential_asset"].queryset

        assert list(offered) == [event.essential_asset]

    def test_its_gravity_is_a_named_level_of_the_impact_scale(self, admin):
        criteria = RiskCriteriaFactory()
        ScaleLevelFactory(criteria=criteria, scale_type="impact", level=1, name="Minor")
        ScaleLevelFactory(criteria=criteria, scale_type="impact", level=4, name="Critical")
        _assessment, baseline, _workshop = _study(risk_criteria=criteria)

        choices = FearedEventCreateForm(baseline=baseline, user=admin).fields["gravity_level"].choices

        assert [label for _value, label in choices] == ["Not assessed", "1 - Minor", "4 - Critical"]

    def test_a_level_rated_on_a_scale_that_changed_is_kept(self, admin):
        criteria = RiskCriteriaFactory()
        ScaleLevelFactory(criteria=criteria, scale_type="impact", level=1, name="Minor")
        _assessment, baseline, _workshop = _study(risk_criteria=criteria)
        event = FearedEventFactory(baseline=baseline, gravity_level=5)

        choices = FearedEventForm(instance=event, baseline=baseline, user=admin).fields["gravity_level"].choices

        assert (5, "5") in list(choices)

    def test_it_is_added_from_the_side_panel_and_the_page_is_refreshed(self, client, admin):
        _assessment, baseline, _workshop = _study()
        asset = _asset()
        baseline.essential_assets.add(asset)

        response = client.post(
            reverse("risks:ebios-feared-event-create", kwargs={"baseline_pk": baseline.pk}),
            {"essential_asset": str(asset.pk), "dic_criterion": "availability", "name": "Production stops",
             "gravity_level": ""},
            **DRAWER,
        )

        event = FearedEvent.objects.get()
        assert response.status_code == 204, response.content.decode()[:400]
        assert response.headers["HX-Trigger"] == "formSaved"
        assert (event.baseline, event.created_by, event.gravity_level) == (baseline, admin, None)

    def test_rows_keep_the_order_they_were_added_in(self, client, admin):
        _assessment, baseline, _workshop = _study()
        asset = _asset()
        baseline.essential_assets.add(asset)
        url = reverse("risks:ebios-feared-event-create", kwargs={"baseline_pk": baseline.pk})

        for criterion in ("integrity", "availability", "confidentiality"):
            client.post(url, {"essential_asset": str(asset.pk), "dic_criterion": criterion, "name": criterion})

        assert [(event.order, event.dic_criterion) for event in baseline.feared_events.order_by("order")] == [
            (1, "integrity"), (2, "availability"), (3, "confidentiality"),
        ]

    def test_a_second_event_for_the_same_asset_and_criterion_is_refused_in_words(self, client, admin):
        """The baseline is not a field of the form, so the form did not check
        the constraint that names it : the database refused the row and the
        page answered with a server error."""
        _assessment, baseline, _workshop = _study()
        first = FearedEventFactory(baseline=baseline, dic_criterion="availability")
        baseline.essential_assets.add(first.essential_asset)

        response = client.post(
            reverse("risks:ebios-feared-event-create", kwargs={"baseline_pk": baseline.pk}),
            {"essential_asset": str(first.essential_asset.pk), "dic_criterion": "availability", "name": "Again"},
            **DRAWER,
        )

        assert response.status_code == 200
        assert f"{first.reference} is already the feared event" in response.content.decode()
        assert baseline.feared_events.count() == 1

    def test_editing_it_shows_everything_on_one_screen(self, client, admin):
        _assessment, baseline, _workshop = _study()
        event = FearedEventFactory(baseline=baseline, name="Customer file disclosed")

        form = FearedEventForm(instance=event, baseline=baseline, user=admin)
        response = client.post(
            reverse("risks:ebios-feared-event-update", kwargs={"pk": event.pk}),
            {"essential_asset": str(event.essential_asset.pk), "dic_criterion": "confidentiality",
             "name": "Customer file disclosed", "description": "<p>Sold on a forum.</p>", "gravity_level": "",
             "gravity_justification": "<p>Fines and lost contracts.</p>"},
            **DRAWER,
        )

        event.refresh_from_db()
        assert form.is_multistep is False
        assert list(form.fields) == [
            "essential_asset", "dic_criterion", "name", "description", "gravity_level", "gravity_justification",
        ]
        assert response.status_code == 204, response.content.decode()[:400]
        assert event.gravity_justification == "<p>Fines and lost contracts.</p>"

    def test_it_is_removed_from_the_side_panel(self, client, admin):
        _assessment, baseline, workshop = _study()
        event = FearedEventFactory(baseline=baseline)
        url = reverse("risks:ebios-feared-event-delete", kwargs={"pk": event.pk})

        dialog = client.get(url, **DRAWER)
        response = client.post(url, **DRAWER)

        assert dialog.status_code == 200 and "modal-header" in dialog.content.decode()
        assert response.status_code == 204
        assert response.headers["HX-Redirect"] == workshop.get_absolute_url()
        assert not FearedEvent.objects.filter(pk=event.pk).exists()

    def test_one_its_lifecycle_protects_is_kept_and_the_page_says_why(self, client, admin):
        """It used to be a server error : the model refuses, nothing caught it."""
        _assessment, baseline, workshop = _study()
        event = FearedEventFactory(baseline=baseline, workflow_state="validated")

        response = client.post(reverse("risks:ebios-feared-event-delete", kwargs={"pk": event.pk}), follow=True)
        page = client.get(workshop.get_absolute_url()).content.decode()

        assert FearedEvent.objects.filter(pk=event.pk).exists()
        assert f"{event.reference} cannot be deleted at the step it has reached" in response.content.decode()
        # The page does not offer what the lifecycle refuses.
        assert reverse("risks:ebios-feared-event-delete", kwargs={"pk": event.pk}) not in page


class TestABaselineGap:
    def test_creation_asks_the_rule_the_gap_and_its_severity(self, admin):
        _assessment, baseline, _workshop = _study()

        form = BaselineGapCreateForm(baseline=baseline, user=admin)

        assert list(form.fields) == ["reference_source", "severity", "description"]
        assert form.is_multistep is False
        # The severity is judged : the default of the model is not saved for the reader.
        assert form.fields["severity"].required and not form.initial.get("severity")
        assert form.fields["severity"].choices[0][0] == ""

    def test_it_is_added_from_the_side_panel(self, client, admin):
        _assessment, baseline, _workshop = _study()

        refused = client.post(
            reverse("risks:ebios-baseline-gap-create", kwargs={"baseline_pk": baseline.pk}),
            {"reference_source": "ISO 27002, control 8.22", "description": "<p>One flat network.</p>", "severity": ""},
            **DRAWER,
        )
        response = client.post(
            reverse("risks:ebios-baseline-gap-create", kwargs={"baseline_pk": baseline.pk}),
            {"reference_source": "ISO 27002, control 8.22", "description": "<p>One flat network.</p>",
             "severity": "high"},
            **DRAWER,
        )

        gap = BaselineGap.objects.get()
        assert refused.status_code == 200
        assert 'Choose a value for "Severity".' in unescape(refused.content.decode())
        assert response.status_code == 204, response.content.decode()[:400]
        assert (gap.baseline, gap.severity, gap.created_by, gap.order) == (baseline, "high", admin, 1)

    def test_its_requirement_and_its_assets_are_picked_in_the_baseline(self, admin):
        """The select listed every requirement of the instance, and the support
        assets of a gap were set through the REST API only."""
        _assessment, baseline, _workshop = _study()
        applied, other = FrameworkFactory(workflow_state="validated"), FrameworkFactory(workflow_state="validated")
        baseline.baseline_references.add(applied)
        ours = RequirementFactory(framework=applied, workflow_state="validated")
        theirs = RequirementFactory(framework=other, workflow_state="validated")
        server, laptop = SupportAssetFactory(workflow_state="active"), SupportAssetFactory(workflow_state="active")
        baseline.support_assets.add(server)
        gap = BaselineGapFactory(baseline=baseline)

        form = BaselineGapForm(instance=gap, baseline=baseline, user=admin)

        assert list(form.fields["linked_requirement"].queryset) == [ours] and theirs.pk
        assert list(form.fields["affected_support_assets"].queryset) == [server] and laptop.pk

    def test_editing_it_links_its_requirement_and_its_assets(self, client, admin):
        _assessment, baseline, _workshop = _study()
        framework = FrameworkFactory(workflow_state="validated")
        baseline.baseline_references.add(framework)
        requirement = RequirementFactory(framework=framework, workflow_state="validated")
        server = SupportAssetFactory(workflow_state="active")
        baseline.support_assets.add(server)
        gap = BaselineGapFactory(baseline=baseline)

        response = client.post(
            reverse("risks:ebios-baseline-gap-update", kwargs={"pk": gap.pk}),
            {"reference_source": gap.reference_source, "severity": "critical", "description": "<p>No inventory.</p>",
             "linked_requirement": str(requirement.pk), "affected_support_assets": [str(server.pk)],
             "recommended_remediation": ""},
            **DRAWER,
        )

        gap.refresh_from_db()
        assert response.status_code == 204, response.content.decode()[:400]
        assert (gap.linked_requirement, list(gap.affected_support_assets.all())) == (requirement, [server])

    def test_one_under_remediation_is_not_removed(self, client, admin):
        _assessment, baseline, workshop = _study()
        gap = BaselineGapFactory(baseline=baseline, status="in_remediation")

        client.post(reverse("risks:ebios-baseline-gap-delete", kwargs={"pk": gap.pk}))
        page = client.get(workshop.get_absolute_url()).content.decode()

        assert BaselineGap.objects.filter(pk=gap.pk).exists()
        assert reverse("risks:ebios-baseline-gap-delete", kwargs={"pk": gap.pk}) not in page


class TestTheSecurityBaseline:
    def test_its_form_has_a_section_for_each_card_of_the_page(self, admin):
        _assessment, baseline, _workshop = _study()

        assert SecurityBaselineForm.section_keys() == ["studied", "needs", "references"]
        assert list(SecurityBaselineForm(instance=baseline, user=admin, section="studied").fields) == [
            "business_values", "essential_assets", "support_assets",
        ]

    def test_a_card_sets_its_own_fields_and_leaves_the_others(self, client, admin):
        _assessment, baseline, _workshop = _study()
        framework = FrameworkFactory(workflow_state="validated")
        baseline.baseline_references.add(framework)
        baseline.dic_summary = "<p>Production must not stop.</p>"
        baseline.save()
        asset, server = _asset(), SupportAssetFactory(workflow_state="active")
        activity = ActivityFactory(workflow_state="validated")

        response = client.post(
            reverse("risks:ebios-baseline-update", kwargs={"pk": baseline.pk}),
            {"_section": "studied", "business_values": [str(activity.pk)], "essential_assets": [str(asset.pk)],
             "support_assets": [str(server.pk)]},
            **DRAWER,
        )

        baseline.refresh_from_db()
        assert response.status_code == 204, response.content.decode()[:400]
        assert list(baseline.essential_assets.all()) == [asset] and list(baseline.support_assets.all()) == [server]
        assert list(baseline.baseline_references.all()) == [framework]
        assert baseline.dic_summary == "<p>Production must not stop.</p>"

    def test_a_new_link_targets_what_can_be_linked_and_a_link_already_there_stays(self, admin):
        _assessment, baseline, _workshop = _study()
        draft, active, retired = EssentialAssetFactory(), _asset(), EssentialAssetFactory(workflow_state="decommissioned")
        baseline.essential_assets.add(retired)

        offered = SecurityBaselineForm(instance=baseline, user=admin).fields["essential_assets"].queryset

        assert active in offered and retired in offered and draft not in offered


class TestThePageOfTheWorkshop:
    def test_it_names_what_the_study_covers_and_opens_each_card_on_its_own(self, client, admin):
        _assessment, baseline, workshop = _study()
        baseline.essential_assets.add(_asset(name="Customer file"))
        baseline.support_assets.add(SupportAssetFactory(name="Billing server"))
        baseline.baseline_references.add(FrameworkFactory(name="Hygiene guide"))
        edit = reverse("risks:ebios-baseline-update", kwargs={"pk": baseline.pk})
        # The help of the page. Its data migration ships it where the migrations
        # are replayed (PostgreSQL), not on the test database built from the models.
        HelpContent.objects.update_or_create(
            key="risks.ebios_workshop_1", language="en",
            defaults={"title": "Workshop 1 - Security baseline", "body": "Workshop 1 says what the study protects."},
        )

        html = client.get(workshop.get_absolute_url()).content.decode()

        assert "Customer file" in html and "Billing server" in html and "Hygiene guide" in html
        for section in ("studied", "needs", "references"):
            assert f'hx-get="{edit}?section={section}"' in html
        assert 'data-helper-key="risks.ebios_workshop_1"' in html
        assert "Workshop 1 says what the study protects." in html

    def test_an_empty_workshop_says_what_to_do_first(self, client, admin):
        _assessment, baseline, workshop = _study()
        edit = reverse("risks:ebios-baseline-update", kwargs={"pk": baseline.pk})
        new_gap = reverse("risks:ebios-baseline-gap-create", kwargs={"baseline_pk": baseline.pk})
        new_event = reverse("risks:ebios-feared-event-create", kwargs={"baseline_pk": baseline.pk})

        html = client.get(workshop.get_absolute_url()).content.decode()

        # No essential asset yet : a feared event has nothing to be about.
        assert "No feared event yet." in html and "Choose the essential assets of the study first." in html
        assert f'hx-get="{edit}?section=studied"' in html and new_event not in html
        assert "No baseline gap yet." in html and f'hx-get="{new_gap}"' in html

    def test_once_an_asset_is_chosen_the_first_feared_event_is_offered(self, client, admin):
        _assessment, baseline, workshop = _study()
        baseline.essential_assets.add(_asset())
        new_event = reverse("risks:ebios-feared-event-create", kwargs={"baseline_pk": baseline.pk})

        html = client.get(workshop.get_absolute_url()).content.decode()

        assert "Add one for each essential asset of the study." in html
        assert html.count(f'hx-get="{new_event}"') == 2  # the card and its empty state

    def test_the_gravity_reads_by_its_name_and_an_unrated_event_says_so(self, client, admin):
        criteria = RiskCriteriaFactory()
        ScaleLevelFactory(criteria=criteria, scale_type="impact", level=4, name="Critical")
        _assessment, baseline, workshop = _study(risk_criteria=criteria)
        FearedEventFactory(baseline=baseline, gravity_level=4, dic_criterion="integrity")
        FearedEventFactory(baseline=baseline, gravity_level=None)

        html = client.get(workshop.get_absolute_url()).content.decode()

        assert '<span class="tabular-nums">4</span> - Critical' in html
        assert "Not assessed" in html

    def test_a_gap_written_in_rich_text_is_shown_as_text(self, client, admin):
        _assessment, baseline, workshop = _study()
        BaselineGapFactory(baseline=baseline, description="<p>No <strong>inventory</strong> of firmware.</p>")

        html = client.get(workshop.get_absolute_url()).content.decode()

        assert "No inventory of firmware." in html and "&lt;p&gt;" not in html

    def test_it_lists_the_essential_assets_that_have_no_feared_event(self, client, admin):
        _assessment, baseline, workshop = _study()
        covered, bare = _asset(name="Customer file"), _asset(name="Payroll")
        baseline.essential_assets.add(covered, bare)
        FearedEventFactory(baseline=baseline, essential_asset=covered)

        html = client.get(workshop.get_absolute_url()).content.decode()

        assert "Essential assets without a feared event :" in html
        assert html.split("Essential assets without a feared event :")[1].split("</p>")[0].strip().endswith("Payroll.")

    def test_a_reader_is_offered_nothing_to_change(self, client):
        _assessment, baseline, workshop = _study()
        event = FearedEventFactory(baseline=baseline)
        baseline.essential_assets.add(event.essential_asset)
        client.force_login(_user_with("risks.ebios_assessment.read", "risks.ebios_baseline.read"))

        html = client.get(workshop.get_absolute_url()).content.decode()

        assert event.name in html
        for name, kwargs in (
            ("risks:ebios-baseline-update", {"pk": baseline.pk}),
            ("risks:ebios-feared-event-create", {"baseline_pk": baseline.pk}),
            ("risks:ebios-feared-event-update", {"pk": event.pk}),
            ("risks:ebios-feared-event-delete", {"pk": event.pk}),
            ("risks:ebios-baseline-gap-create", {"baseline_pk": baseline.pk}),
        ):
            assert reverse(name, kwargs=kwargs) not in html

    def test_a_record_of_another_scope_is_not_named(self, client):
        mine, theirs = ScopeFactory(), ScopeFactory()
        _assessment, baseline, workshop = _study(scopes=[mine])
        hidden = _asset(name="An asset of the other scope", scopes=[theirs])
        baseline.essential_assets.add(_asset(name="An asset of my scope", scopes=[mine]), hidden)
        FearedEventFactory(baseline=baseline, essential_asset=hidden, name="An event about it")
        client.force_login(_user_with("risks.ebios_assessment.read", "risks.ebios_baseline.read", scopes=[mine]))

        html = client.get(workshop.get_absolute_url()).content.decode()

        assert "An asset of my scope" in html and "An event about it" in html
        assert "An asset of the other scope" not in html


class TestTheFormsOnADirectVisit:
    def test_a_form_opened_by_its_address_is_a_page_that_leads_back_to_the_workshop(self, client, admin):
        assessment, baseline, workshop = _study()

        html = client.get(reverse("risks:ebios-feared-event-create", kwargs={"baseline_pk": baseline.pk})).content.decode()

        assert "New feared event" in html and assessment.name in html
        assert f'href="{workshop.get_absolute_url()}" class="btn btn-secondary me-auto"' in html
        # A creation is confirmed by its word.
        assert ">Create</button>" in html.replace("\n", "").replace("</i>", "")

    def test_saving_it_from_the_page_goes_back_to_the_workshop(self, client, admin):
        _assessment, baseline, workshop = _study()

        response = client.post(
            reverse("risks:ebios-baseline-gap-create", kwargs={"baseline_pk": baseline.pk}),
            {"reference_source": "Hygiene guide, rule 12", "description": "<p>Shared accounts.</p>", "severity": "low"},
        )

        assert response.status_code == 302 and response.url == workshop.get_absolute_url()

    @pytest.mark.parametrize("name", ["risks:ebios-feared-event-create", "risks:ebios-baseline-gap-create"])
    def test_a_visitor_is_asked_to_sign_in(self, client, name):
        _assessment, baseline, _workshop = _study()

        response = client.get(reverse(name, kwargs={"baseline_pk": baseline.pk}))

        assert response.status_code == 302 and "/login" in response.url

    @pytest.mark.parametrize("name", ["risks:ebios-feared-event-create", "risks:ebios-baseline-gap-create"])
    def test_a_baseline_of_another_scope_is_an_unknown_one(self, client, name):
        mine, theirs = ScopeFactory(), ScopeFactory()
        _assessment, baseline, _workshop = _study(scopes=[theirs])
        client.force_login(_user_with("risks.ebios_baseline.create", "risks.ebios_baseline.read", scopes=[mine]))
        url = reverse(name, kwargs={"baseline_pk": baseline.pk})

        assert client.get(url).status_code == 404
        assert client.post(url, {"name": "x", "reference_source": "x", "description": "x", "severity": "low"}).status_code == 404
        assert not FearedEvent.objects.exists() and not BaselineGap.objects.exists()


class TestWhatTheWorkshopStillNeeds:
    """The deliverables a workshop is validated on (rule RE-04 of the specification)."""

    def test_a_new_study_lists_what_workshop_1_needs(self, client, admin):
        _assessment, _baseline, workshop = _study()

        report = completeness_of(workshop)
        html = client.get(workshop.get_absolute_url()).content.decode()

        assert [item.key for item in report.blocking_missing] == ["w1_essential_assets", "w1_support_assets"]
        assert [item.key for item in report.advised_missing] == ["w1_business_values", "w1_baseline_references"]
        # Each line leads to the card of the page where it is done.
        assert f'href="{workshop.get_absolute_url()}#business-values-and-assets"' in html
        assert 'id="business-values-and-assets"' in html and 'id="baseline-references"' in html
        assert "Choose the essential assets" in html

    def test_each_essential_asset_asks_for_its_feared_event(self):
        _assessment, baseline, workshop = _study()
        covered, bare = _asset(), _asset()
        baseline.essential_assets.add(covered, bare)
        baseline.support_assets.add(SupportAssetFactory())
        FearedEventFactory(baseline=baseline, essential_asset=covered, gravity_level=None)

        report = completeness_of(workshop)

        assert [item.key for item in report.blocking_missing] == ["w1_feared_events"]
        assert "w1_gravity" in [item.key for item in report.advised_missing]

    def test_the_other_workshops_are_not_asked_for_it(self):
        assessment, _baseline, _workshop = _study()

        for number in (0, 2, 3, 4, 5):
            report = completeness_of(assessment.ebios_workshops.get(workshop_number=number))
            assert [item.key for item in report.items if item.key.startswith("w1_")] == []

    def _ready(self):
        assessment, baseline, workshop = _study()
        asset = _asset()
        baseline.essential_assets.add(asset)
        baseline.support_assets.add(SupportAssetFactory())
        type(workshop).objects.filter(pk=workshop.pk).update(workflow_state="under_review")
        return assessment, baseline, workshop, asset

    def test_it_is_not_validated_while_an_essential_asset_has_no_feared_event(self, client, admin):
        assessment, _baseline, workshop, _asset_ = self._ready()

        response = client.post(
            reverse("risks:ebios-workshop-validate", kwargs={"assessment_pk": assessment.pk, "workshop_pk": workshop.pk}),
            follow=True,
        )

        workshop.refresh_from_db()
        assert workshop.workflow_state == "under_review"
        assert "this remains to be done : add a feared event for each essential asset" in response.content.decode()

    def test_it_is_validated_once_its_deliverables_are_there(self, client, admin):
        assessment, baseline, workshop, asset = self._ready()
        FearedEventFactory(baseline=baseline, essential_asset=asset)

        client.post(
            reverse("risks:ebios-workshop-validate", kwargs={"assessment_pk": assessment.pk, "workshop_pk": workshop.pk}),
        )

        workshop.refresh_from_db()
        assert (workshop.workflow_state, workshop.validated_by) == ("validated", admin)

    def test_the_generic_endpoint_and_the_mcp_server_wait_for_them_too(self, client, admin):
        _assessment, _baseline, workshop, _asset_ = self._ready()

        client.post(
            reverse("workflow:transition", kwargs={
                "app_label": "risks", "model": "ebiosworkshopprogress", "pk": workshop.pk,
            }),
            {"target_status": "validated"},
        )
        answer = _mcp(admin, "update_ebios_workshop", {"id": str(workshop.pk), "status": "validated"})

        workshop.refresh_from_db()
        assert workshop.workflow_state == "under_review"
        assert "add a feared event for each essential asset" in json.dumps(answer)


class TestTheApiAndTheMcpServer:
    def test_they_report_what_the_workshop_still_needs(self, admin):
        _assessment, _baseline, workshop = _study()
        api = APIClient()
        api.force_authenticate(admin)

        one = api.get(f"/api/v1/risks/ebios/workshops/{workshop.pk}/").json()
        one = one.get("data", one)
        other = _mcp(admin, "get_ebios_workshop", {"id": str(workshop.pk)})

        expected = ["w1_essential_assets", "w1_support_assets", "w1_business_values", "w1_baseline_references"]
        assert [item["key"] for item in one["completeness"]["missing"]] == expected
        assert [item["key"] for item in other["completeness"]["missing"]] == expected
        assert one["completeness"]["can_advance"] is False

    def test_the_mcp_server_sets_what_the_study_covers(self, admin):
        """The four relations of the baseline were set by the page and the REST API only."""
        _assessment, baseline, workshop = _study()
        asset, server = _asset(), SupportAssetFactory(workflow_state="active")
        framework, activity = FrameworkFactory(workflow_state="validated"), ActivityFactory(workflow_state="validated")

        answer = _mcp(admin, "update_ebios_security_baseline", {
            "id": str(baseline.pk), "essential_asset_ids": [str(asset.pk)], "support_asset_ids": [str(server.pk)],
            "baseline_reference_ids": [str(framework.pk)], "business_value_ids": [str(activity.pk)],
        })

        assert "error" not in json.dumps(answer).lower(), answer
        assert list(baseline.essential_assets.all()) == [asset] and list(baseline.support_assets.all()) == [server]
        assert list(baseline.baseline_references.all()) == [framework]
        assert list(baseline.business_values.all()) == [activity]
        assert [item.key for item in completeness_of(workshop).blocking_missing] == ["w1_feared_events"]

    def test_the_mcp_server_does_not_link_a_record_out_of_reach(self):
        mine, theirs = ScopeFactory(), ScopeFactory()
        _assessment, baseline, _workshop = _study(scopes=[mine])
        hidden = _asset(scopes=[theirs])
        user = _user_with("risks.ebios_baseline.read", "risks.ebios_baseline.update", scopes=[mine])

        _mcp(user, "update_ebios_security_baseline", {"id": str(baseline.pk), "essential_asset_ids": [str(hidden.pk)]})

        assert not baseline.essential_assets.exists()

    def test_the_mcp_server_sets_the_support_assets_of_a_gap(self, admin):
        _assessment, baseline, _workshop = _study()
        server = SupportAssetFactory(workflow_state="active")
        gap = BaselineGapFactory(baseline=baseline)

        answer = _mcp(admin, "update_ebios_baseline_gap", {
            "id": str(gap.pk), "affected_support_asset_ids": [str(server.pk)],
        })

        assert "error" not in json.dumps(answer).lower(), answer
        assert list(gap.affected_support_assets.all()) == [server]
