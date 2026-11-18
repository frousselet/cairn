# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""A record is created short, completed on its page, and held to it.

``core/completeness.py`` is how a model says what *complete* means. Asking
less at creation must not lower what a record is worth once it is relied
upon : the lifecycle refuses the steps the model names while a blocking
requirement is missing, on the web, the REST API and the MCP server alike.
"""

import pytest
from django.apps import apps
from django.urls import reverse

from accounts.tests.factories import UserFactory
from assets.tests.factories import EssentialAssetFactory
from context.tests.factories import ScopeFactory, SiteFactory
from core.completeness import (
    Completeness,
    Requirement,
    as_payload,
    completeness_of,
    is_filled,
    refuse_if_incomplete,
)
from core.lifecycle import DomainRefusalError

pytestmark = pytest.mark.django_db


def _complete_scope(**kwargs):
    """A scope that says where it stops and who answers for it."""
    scope = ScopeFactory(boundaries="No exclusion.", **kwargs)
    scope.managers.add(UserFactory())
    return scope


class TestIsFilled:
    def test_a_text_holds_an_answer_when_something_is_left_of_it(self):
        scope = ScopeFactory(boundaries="   ")

        assert not is_filled(scope, "boundaries")
        # An emptied rich-text field stores markup and no word.
        scope.boundaries = "<p><br></p>"
        assert not is_filled(scope, "boundaries")
        scope.boundaries = "<p>&nbsp;</p>"
        assert not is_filled(scope, "boundaries")
        scope.boundaries = "<p>The warehouse is left out.</p>"
        assert is_filled(scope, "boundaries")

    def test_a_relation_to_many_holds_an_answer_when_it_has_a_row(self):
        scope = ScopeFactory()

        assert not is_filled(scope, "managers")
        scope.managers.add(UserFactory())
        assert is_filled(scope, "managers")

    def test_a_reverse_relation_counts_as_well(self):
        from assets.tests.factories import DependencyFactory

        asset = EssentialAssetFactory()

        assert not is_filled(asset, "dependencies_as_essential")
        DependencyFactory(essential_asset=asset)
        assert is_filled(asset, "dependencies_as_essential")

    def test_a_level_of_zero_is_an_answer_and_none_is_not(self):
        asset = EssentialAssetFactory(confidentiality_level=0, integrity_level=None)

        assert is_filled(asset, "confidentiality_level")
        assert not is_filled(asset, "integrity_level")

    def test_a_date_and_an_unknown_attribute(self):
        scope = ScopeFactory()

        assert not is_filled(scope, "review_date")
        assert not is_filled(scope, "no_such_attribute")


class TestRequirement:
    def test_a_requirement_must_test_something(self):
        with pytest.raises(ValueError):
            Requirement("empty", "do nothing")

    def test_every_field_named_must_hold_an_answer(self):
        need = Requirement("both", "fill both", fields=["boundaries", "managers"])
        scope = ScopeFactory(boundaries="x")

        assert not need.is_met(scope)
        scope.managers.add(UserFactory())
        assert need.is_met(scope)

    def test_one_of_several_is_enough_when_asked_so(self):
        need = Requirement("any", "fill one", any_of=["geographic_scope", "technical_scope"])
        scope = ScopeFactory()

        assert not need.is_met(scope)
        scope.technical_scope = "The ERP."
        assert need.is_met(scope)

    def test_a_custom_check(self):
        need = Requirement("named", "name it", check=lambda scope: scope.name.startswith("HQ"))

        assert need.is_met(ScopeFactory(name="HQ Lyon"))
        assert not need.is_met(ScopeFactory(name="Lyon"))

    def test_two_requirements_cannot_share_a_key(self):
        with pytest.raises(ValueError):
            Completeness(
                Requirement("a", "x", fields=["name"]),
                Requirement("a", "y", fields=["name"]),
            )


class TestReport:
    def test_a_new_scope_lists_what_it_still_needs(self):
        report = completeness_of(ScopeFactory())

        assert [item.key for item in report.blocking_missing] == ["boundaries", "managers"]
        assert [item.key for item in report.advised_missing] == ["coverage", "sites", "review"]
        assert not report.can_advance
        assert not report.is_complete
        assert (report.done, report.total) == (0, 5)
        # A label is an act, shown capitalised as a line of the list.
        assert report.blocking_missing[0].label == "Say where the scope stops"
        assert report.blocking_missing[0].section == "boundaries"

    def test_the_gate_is_named_until_the_record_stands_on_it(self):
        assert completeness_of(ScopeFactory()).gate_label == "Validation"
        # A scope already in force is not "before" anything any more.
        assert completeness_of(ScopeFactory(workflow_state="in_force")).gate_label == ""

    def test_a_scope_with_everything_is_complete(self):
        from datetime import date

        scope = _complete_scope(geographic_scope="France", review_date=date(2030, 1, 1))
        scope.included_sites.add(SiteFactory())

        report = completeness_of(scope)

        assert report.can_advance and report.is_complete
        assert report.missing == []

    def test_a_model_that_declares_nothing_has_no_report(self):
        assert completeness_of(SiteFactory()) is None
        assert as_payload(SiteFactory()) is None

    def test_an_item_done_elsewhere_carries_its_address(self):
        """Attaching support assets is not a section of the asset's own form."""
        asset = EssentialAssetFactory()
        item = next(i for i in completeness_of(asset).items if i.key == "support_assets")

        assert item.section is None
        assert item.href == reverse("assets:dependency-list")

    def test_the_payload_is_plain_data(self):
        payload = as_payload(ScopeFactory())

        assert payload["complete"] is False
        assert payload["can_advance"] is False
        assert {"key": "managers", "label": "Name at least one manager", "blocking": True} in payload["missing"]


class TestTheLifecycleWaits:
    def test_an_incomplete_scope_cannot_be_submitted_for_validation(self):
        scope = ScopeFactory(workflow_state="definition")

        with pytest.raises(DomainRefusalError) as refusal:
            scope.transition_to("validation", UserFactory())

        # The sentence names the step and what remains to be done.
        assert str(refusal.value.detail) == (
            'Before moving to "Validation", this remains to be done : '
            "say where the scope stops ; name at least one manager."
        )
        scope.refresh_from_db()
        assert scope.workflow_state == "definition"

    def test_a_complete_scope_goes_through(self):
        scope = _complete_scope(workflow_state="definition")

        scope.transition_to("validation", UserFactory())

        assert scope.workflow_state == "validation"

    def test_the_steps_before_the_gate_stay_open(self):
        """A scope is worked on before it is complete : only the gate waits."""
        scope = ScopeFactory()

        scope.transition_to("definition", UserFactory())

        assert scope.workflow_state == "definition"

    def test_what_is_only_advised_does_not_hold_the_record_back(self):
        scope = _complete_scope(workflow_state="validation")
        assert completeness_of(scope).advised_missing

        scope.transition_to("in_force", UserFactory())

        assert scope.workflow_state == "in_force"

    def test_a_scope_is_dated_the_day_it_comes_into_force(self):
        from django.utils import timezone

        scope = _complete_scope(workflow_state="validation")
        assert scope.effective_date is None

        scope.transition_to("in_force", UserFactory())

        scope.refresh_from_db()
        assert scope.effective_date == timezone.localdate()

    def test_a_date_typed_beforehand_is_kept(self):
        from datetime import date

        scope = _complete_scope(workflow_state="validation", effective_date=date(2030, 6, 1))

        scope.transition_to("in_force", UserFactory())

        scope.refresh_from_db()
        assert scope.effective_date == date(2030, 6, 1)

    def test_a_refused_scope_is_not_dated(self):
        scope = ScopeFactory(workflow_state="validation")

        with pytest.raises(DomainRefusalError):
            scope.transition_to("in_force", UserFactory())

        assert scope.effective_date is None

    def test_an_asset_cannot_become_active_until_its_needs_are_assessed(self):
        asset = EssentialAssetFactory(
            confidentiality_level=None, integrity_level=None, availability_level=None,
        )

        with pytest.raises(DomainRefusalError) as refusal:
            refuse_if_incomplete(asset, "active")

        assert "assess its security needs" in str(refusal.value.detail)
        # One level missing is still "not assessed".
        asset.confidentiality_level, asset.integrity_level = 3, 2
        with pytest.raises(DomainRefusalError):
            refuse_if_incomplete(asset, "active")
        asset.availability_level = 0
        refuse_if_incomplete(asset, "active")

    def test_a_step_that_is_not_a_gate_is_never_refused(self):
        refuse_if_incomplete(ScopeFactory(), "definition")
        refuse_if_incomplete(ScopeFactory(), "archived")
        # A model that declares nothing is never refused either.
        refuse_if_incomplete(SiteFactory(), "operational")


class TestWhatIsCheckedFirst:
    """Whether the move is legal and allowed is answered before what the record lacks."""

    def test_a_caller_who_may_not_move_the_record_is_told_so(self):
        from core.lifecycle import TransitionNotAllowedError

        scope = ScopeFactory(workflow_state="definition")
        stranger = UserFactory(is_superuser=False)

        with pytest.raises(TransitionNotAllowedError):
            scope.transition_to("validation", stranger, enforce_permission=True)

    def test_a_move_the_lifecycle_does_not_offer_is_illegal_not_incomplete(self):
        from core.lifecycle import IllegalTransitionError

        scope = ScopeFactory()  # draft : validation is two steps away

        with pytest.raises(IllegalTransitionError):
            scope.transition_to("validation", UserFactory())


class TestTheWebRefusal:
    def test_the_transition_endpoint_says_what_remains_to_be_done(self, client):
        from django.contrib.messages import get_messages

        user = UserFactory(is_superuser=True)
        client.force_login(user)
        scope = ScopeFactory(workflow_state="definition")
        url = reverse("workflow:transition", kwargs={"app_label": "context", "model": "scope", "pk": scope.pk})

        response = client.post(url, {"target_status": "validation"})

        scope.refresh_from_db()
        assert scope.workflow_state == "definition"
        messages = [str(m) for m in get_messages(response.wsgi_request)]
        assert any("name at least one manager" in m for m in messages)


class TestDeclarationsHoldTogether:
    """Every model that declares a completeness, checked against its lifecycle and its form."""

    def _declaring_models(self):
        return [m for m in apps.get_models() if getattr(m, "COMPLETENESS", None) is not None]

    def test_the_pilot_models_declare_one(self):
        labels = {m._meta.label for m in self._declaring_models()}

        assert {"context.Scope", "assets.EssentialAsset"} <= labels

    def test_every_gate_is_a_step_of_the_lifecycle(self):
        from core.lifecycle import resolve_lifecycle

        for model in self._declaring_models():
            lifecycle = resolve_lifecycle(model)
            for code in model.COMPLETENESS.before:
                assert lifecycle.has_step(code), f"{model._meta.label} : '{code}' is not a step of '{lifecycle.name}'"

    def test_every_attribute_tested_exists(self):
        for model in self._declaring_models():
            names = {f.name for f in model._meta.get_fields()} | {
                getattr(f, "get_accessor_name", lambda: None)() for f in model._meta.get_fields()
            }
            for requirement in model.COMPLETENESS.requirements:
                for name in (*requirement.fields, *requirement.any_of):
                    assert name in names, f"{model._meta.label} : requirement '{requirement.key}' tests unknown '{name}'"

    @staticmethod
    def _update_forms():
        """model -> the form of its update view, read from the URL configuration."""
        from django.urls import get_resolver
        from django.views.generic.edit import UpdateView

        forms = {}

        def walk(patterns):
            for pattern in patterns:
                if hasattr(pattern, "url_patterns"):
                    walk(pattern.url_patterns)
                    continue
                view = getattr(pattern.callback, "view_class", None)
                if view is not None and issubclass(view, UpdateView) and getattr(view, "form_class", None):
                    forms.setdefault(view.model, view.form_class)

        walk(get_resolver().url_patterns)
        return forms

    def test_every_section_named_is_a_section_of_the_update_form(self):
        forms = self._update_forms()
        for model in self._declaring_models():
            form = forms.get(model)
            assert form is not None, f"{model._meta.label} : no update view edits it"
            for requirement in model.COMPLETENESS.requirements:
                if requirement.section:
                    assert requirement.section in form.section_keys(), (
                        f"{model._meta.label} : '{requirement.section}' is not a section of {form.__name__}"
                    )
