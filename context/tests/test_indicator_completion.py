# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""An indicator is created on one screen, then completed on its page.

Its forms are held to the usability standard with every other form
(``core/tests/test_usability_standard.py``). Its page is tested here, since an
indicator has three creation dialogs (organizational, technical, computed by
Cairn) and two forms, which the generic page tests cannot tell apart. What is
particular to it : its thresholds fit its format, a figure Cairn computes has
a source in place of a format, and it names who reads it and the objectives it
tells the progress of, which no form of the interface let anyone set.
"""

import datetime
import json

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.tests.factories import GroupFactory, PermissionFactory, UserFactory
from context.forms import (
    IndicatorCreateForm,
    IndicatorUpdateForm,
    PredefinedIndicatorCreateForm,
    PredefinedIndicatorUpdateForm,
)
from context.models import Indicator
from context.tests.factories import IndicatorFactory, ObjectiveFactory, ScopeFactory
from core.completeness import completeness_of

pytestmark = pytest.mark.django_db

DRAWER = {"HTTP_HX_REQUEST": "true", "HTTP_HX_TARGET": "drawer-form-content"}
SOON = (datetime.date.today() + datetime.timedelta(days=30)).isoformat()


@pytest.fixture
def admin(client):
    user = UserFactory(is_superuser=True)
    client.force_login(user)
    return user


def _user_with(*codenames, scopes=()):
    user = UserFactory(is_superuser=False)
    group = GroupFactory()
    for codename in codenames:
        group.permissions.add(PermissionFactory(codename=codename))
    for scope in scopes:
        group.allowed_scopes.add(scope)
    group.users.add(user)
    return user


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


class TestCreationIsShort:
    def test_it_asks_what_is_followed_whether_it_is_a_number_who_reads_it_and_how_often(self, admin):
        ScopeFactory()
        ScopeFactory()

        form = IndicatorCreateForm(user=admin)

        assert list(form.fields) == ["scopes", "name", "format", "owner", "review_frequency", "first_review_date"]
        assert form.is_multistep is False
        # Whoever creates it reads it unless they say otherwise.
        assert form.fields["owner"].initial == admin.pk

    def test_a_number_or_a_yes_or_no_answer_is_a_decision_nobody_takes_for_the_reader(self, client, admin):
        html = client.get(reverse("context:indicator-organizational-create"), **DRAWER).content.decode()
        select = html[html.index('name="format"'):]
        select = select[:select.index("</select>")]

        # The model answers "Number" : the form opens on no answer.
        assert 'value="" selected' in select and select.count("selected") == 1

    @pytest.mark.parametrize("kind", ["organizational", "technical"])
    def test_it_is_created_with_the_type_of_its_register_and_lands_on_its_page(self, client, admin, kind):
        response = client.post(
            reverse(f"context:indicator-{kind}-create"),
            {"name": "Share of staff trained", "format": "number", "owner": str(admin.pk),
             "review_frequency": "quarterly", "first_review_date": SOON},
            **DRAWER,
        )

        indicator = Indicator.objects.get()
        assert response.status_code == 204, response.content.decode()[:400]
        assert response.headers["HX-Redirect"] == indicator.get_absolute_url()
        assert (indicator.indicator_type, indicator.collection_method, indicator.owner) == (kind, "manual", admin)

    def test_with_one_scope_it_is_filed_under_it(self, client, admin):
        only = ScopeFactory()

        client.post(
            reverse("context:indicator-organizational-create"),
            {"name": "Share of staff trained", "format": "number", "owner": str(admin.pk),
             "review_frequency": "quarterly", "first_review_date": SOON},
            **DRAWER,
        )

        assert "scopes" not in IndicatorCreateForm(user=admin).fields
        assert list(Indicator.objects.get().scopes.all()) == [only]

    def test_the_method_of_the_figures_cairn_computes_is_not_a_choice_here(self, admin):
        """A figure Cairn computes is created from its own dialog."""
        methods = [value for value, _label in IndicatorUpdateForm(instance=IndicatorFactory(), user=admin).fields[
            "collection_method"].choices]

        assert methods == ["manual", "api"]


class TestAFigureCairnComputes:
    def test_its_creation_asks_which_figure_and_how_often_it_is_reviewed(self, admin):
        ScopeFactory()
        ScopeFactory()

        form = PredefinedIndicatorCreateForm(user=admin)

        assert list(form.fields) == [
            "scopes", "name", "internal_source", "internal_source_parameter", "review_frequency", "first_review_date",
        ]
        assert form.is_multistep is False

    def test_it_is_created_with_its_format_and_a_first_reading(self, client, admin):
        response = client.post(
            reverse("context:indicator-predefined-create"),
            {"name": "Objectives on track", "internal_source": "objective_progress", "internal_source_parameter": "",
             "review_frequency": "monthly", "first_review_date": SOON},
            **DRAWER,
        )

        indicator = Indicator.objects.get()
        assert response.status_code == 204, response.content.decode()[:400]
        assert response.headers["HX-Redirect"] == indicator.get_absolute_url()
        assert (indicator.is_internal, indicator.format, indicator.unit, indicator.collection_method) == (
            True, "number", "%", "internal",
        )

    def test_leaving_its_source_out_is_refused_by_the_form_not_by_a_server_error(self, client, admin):
        """The form let the source out and the record refused it once saved."""
        response = client.post(
            reverse("context:indicator-predefined-create"),
            {"name": "Objectives on track", "internal_source": "", "review_frequency": "monthly",
             "first_review_date": SOON},
            **DRAWER,
        )

        assert response.status_code == 200
        assert not Indicator.objects.exists()

    def test_its_page_edits_its_source_where_another_edits_its_format(self, client, admin):
        indicator = IndicatorFactory(is_internal=True, internal_source="objective_progress",
                                     collection_method="internal", unit="%")
        edit = reverse("context:indicator-update", kwargs={"pk": indicator.pk})

        html = client.get(indicator.get_absolute_url()).content.decode()

        assert PredefinedIndicatorUpdateForm.section_keys() == ["identity", "source", "thresholds", "review", "relations"]
        for key in PredefinedIndicatorUpdateForm.section_keys():
            assert f'href="{edit}?section={key}"' in html, key
        assert f'{edit}?section=measure"' not in html


class TestWhatItStillNeeds:
    def test_a_bare_indicator_lists_what_would_make_it_useful(self, client, admin):
        indicator = IndicatorFactory()
        edit = reverse("context:indicator-update", kwargs={"pk": indicator.pk})

        report = completeness_of(indicator)
        html = client.get(indicator.get_absolute_url()).content.decode()

        assert [item.key for item in report.advised_missing] == ["target", "owner", "objectives", "reading"]
        # Advice : nothing holds its lifecycle back.
        assert report.blocking_missing == [] and report.can_advance
        assert IndicatorUpdateForm.section_keys() == ["identity", "measure", "thresholds", "review", "relations"]
        for key in IndicatorUpdateForm.section_keys():
            assert f'href="{edit}?section={key}"' in html, key
        # Readings are recorded on the page : the line leads to their card.
        assert f'href="{indicator.get_absolute_url()}#measurements"' in html and 'id="measurements"' in html

    def test_what_it_names_is_a_section_of_both_of_its_forms(self):
        """Its update view picks one of two forms : a line of the list must
        open a section whichever it is."""
        named = {requirement.section for requirement in Indicator.COMPLETENESS.requirements if requirement.section}

        assert named <= set(IndicatorUpdateForm.section_keys())
        assert named <= set(PredefinedIndicatorUpdateForm.section_keys())

    def test_a_first_reading_answers_the_last_line(self, admin):
        indicator = IndicatorFactory()

        indicator.record_measurement(value="42", recorded_by=admin)

        assert "reading" not in [item.key for item in completeness_of(indicator).advised_missing]

    def test_the_card_of_its_review_sets_it_and_leaves_the_rest_alone(self, client, admin):
        indicator = IndicatorFactory(name="Share of staff trained", unit="%", expected_level="95")

        response = client.post(
            reverse("context:indicator-update", kwargs={"pk": indicator.pk}),
            {"_section": "review", "review_frequency": "annual", "first_review_date": SOON},
            **DRAWER,
        )

        indicator.refresh_from_db()
        assert response.status_code == 204, response.content.decode()[:400]
        assert indicator.review_frequency == "annual"
        assert (indicator.name, indicator.unit, indicator.expected_level) == ("Share of staff trained", "%", "95")


class TestItsThresholdsFitItsFormat:
    """The form offered the four alarms and every figure to both formats, and
    the record refused the pairs that mean nothing."""

    def test_a_number_falls_below_or_exceeds_a_figure(self, admin):
        form = IndicatorUpdateForm(instance=IndicatorFactory(format="number"), user=admin, section="thresholds")

        assert [value for value, _label in form.fields["critical_threshold_operator"].choices] == ["", "below", "above"]
        assert {"critical_threshold_value", "critical_threshold_min", "critical_threshold_max"} <= set(form.fields)

    def test_a_yes_or_no_answer_is_true_or_false_and_compared_with_no_figure(self, admin):
        form = IndicatorUpdateForm(instance=IndicatorFactory(format="boolean"), user=admin, section="thresholds")

        assert [value for value, _label in form.fields["critical_threshold_operator"].choices] == [
            "", "is_false", "is_true",
        ]
        assert list(form.fields) == ["expected_level", "critical_threshold_operator"]

    def test_its_card_saves_the_alarm_of_a_yes_or_no_answer(self, client, admin):
        indicator = IndicatorFactory(format="boolean")

        response = client.post(
            reverse("context:indicator-update", kwargs={"pk": indicator.pk}),
            {"_section": "thresholds", "expected_level": "true", "critical_threshold_operator": "is_false"},
            **DRAWER,
        )

        indicator.refresh_from_db()
        assert response.status_code == 204, response.content.decode()[:400]
        assert indicator.critical_threshold_operator == "is_false"


class TestWhatItIsLinkedTo:
    """Who reads it and the objectives it tells the progress of existed in the
    model, the REST API and the MCP server, and in no form of the interface."""

    def test_its_objectives_are_picked_among_what_can_be_linked_and_shown_on_its_page(self, client, admin):
        objective = ObjectiveFactory(name="Every newcomer is trained", workflow_state="validated")
        draft = ObjectiveFactory(name="A draft objective")
        indicator = IndicatorFactory()

        offered = IndicatorUpdateForm(instance=indicator, user=admin, section="relations").fields["linked_objectives"].queryset
        response = client.post(
            reverse("context:indicator-update", kwargs={"pk": indicator.pk}),
            {"_section": "relations", "linked_objectives": [str(objective.pk)]},
            **DRAWER,
        )

        assert objective in offered and draft not in offered
        assert response.status_code == 204, response.content.decode()[:400]
        assert "Every newcomer is trained" in client.get(indicator.get_absolute_url()).content.decode()

    def test_an_objective_of_another_scope_is_not_named_on_its_page(self, client):
        mine, theirs = ScopeFactory(), ScopeFactory()
        indicator = IndicatorFactory(scopes=[mine])
        indicator.linked_objectives.add(
            ObjectiveFactory(name="An objective of the other scope", scopes=[theirs]),
            ObjectiveFactory(name="An objective of my scope", scopes=[mine]),
        )
        client.force_login(_user_with("context.indicator.read", scopes=[mine]))

        html = client.get(indicator.get_absolute_url()).content.decode()

        assert "An objective of my scope" in html and "An objective of the other scope" not in html


class TestThePage:
    def test_deleting_is_offered_to_whoever_may_delete(self, client):
        """The button was shown to every reader, and refused once pressed."""
        indicator = IndicatorFactory()
        delete = reverse("context:indicator-delete", kwargs={"pk": indicator.pk})

        client.force_login(_user_with("context.indicator.read"))
        as_a_reader = client.get(indicator.get_absolute_url()).content.decode()
        client.force_login(_user_with("context.indicator.read", "context.indicator.delete"))
        as_someone_who_may = client.get(indicator.get_absolute_url()).content.decode()

        assert f'href="{delete}"' not in as_a_reader
        assert f'href="{delete}"' in as_someone_who_may

    @pytest.mark.parametrize("kind", ["organizational", "technical"])
    def test_an_empty_register_explains_and_offers_an_indicator_of_its_type(self, client, admin, kind):
        html = client.get(reverse(f"context:indicator-{kind}-list")).content.decode()

        assert "No indicator yet." in html
        create = reverse(f"context:indicator-{kind}-create")
        assert f'href="{create}"' in html and f'hx-get="{create}"' in html


class TestTheApiAndTheMcpServer:
    def test_they_report_the_completeness_of_one_indicator(self, admin):
        indicator = IndicatorFactory()
        api = APIClient()
        api.force_authenticate(admin)

        one = api.get(f"/api/v1/context/indicators/{indicator.pk}/").json()
        one = one.get("data", one)
        read = _mcp(admin, "get_indicator", {"id": str(indicator.pk)})

        assert [item["key"] for item in one["completeness"]["missing"]] == ["target", "owner", "objectives", "reading"]
        assert [item["key"] for item in read["completeness"]["missing"]] == ["target", "owner", "objectives", "reading"]
