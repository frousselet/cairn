# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""A scope is created on one screen, then completed on its page.

The pilot of the usability standard (``docs/sdk/usability-standard.md``) :
creation asks for what makes the scope exist, the page lists what it still
needs, and each card of the page opens the dialog of its own section.
"""

import pytest
from django.contrib.messages import get_messages
from django.urls import reverse

from accounts.models import Permission
from accounts.tests.factories import GroupFactory, UserFactory
from context.forms import ScopeCreateForm, ScopeUpdateForm
from context.models import Scope
from context.tests.factories import ScopeFactory

pytestmark = pytest.mark.django_db

DRAWER = {"HTTP_HX_REQUEST": "true", "HTTP_HX_TARGET": "drawer-form-content"}


@pytest.fixture
def admin(client):
    user = UserFactory(is_superuser=True)
    client.force_login(user)
    return user


def _member(*codenames, scopes=()):
    user = UserFactory(is_superuser=False)
    group = GroupFactory()
    group.permissions.set(Permission.objects.filter(codename__in=codenames))
    if scopes:
        group.allowed_scopes.set(scopes)
    group.users.add(user)
    return user


class TestCreationIsShort:
    def test_the_very_first_scope_is_asked_three_things(self):
        form = ScopeCreateForm()

        # No scope exists : a parent cannot be chosen, so it is not asked.
        assert list(form.fields) == ["name", "description", "icon"]
        assert form.is_multistep is False

    def test_the_parent_is_asked_once_a_scope_exists(self):
        ScopeFactory()

        assert "parent_scope" in ScopeCreateForm().fields

    def test_it_asks_nothing_that_can_wait(self):
        ScopeFactory()
        form = ScopeCreateForm()

        assert len(form.fields) <= 6
        assert not {"boundaries", "managers", "included_sites", "review_date"} & set(form.fields)

    def test_creating_lands_on_the_new_scope(self, client, admin):
        response = client.post(
            reverse("context:scope-create"), {"name": "Head office", "description": "Everything in Lyon."}, **DRAWER,
        )

        scope = Scope.objects.get(name="Head office")
        assert response.status_code == 204
        # The drawer closes on the scope page, where the rest is filled in.
        assert response["HX-Redirect"] == reverse("context:scope-detail", kwargs={"pk": scope.pk})
        assert "HX-Trigger" not in response
        assert scope.created_by == admin
        assert any("Head office" in str(m) for m in get_messages(response.wsgi_request))

    def test_without_scripts_it_lands_there_too(self, client, admin):
        response = client.post(reverse("context:scope-create"), {"name": "Plant", "description": "The plant."})

        scope = Scope.objects.get(name="Plant")
        assert response.status_code == 302
        assert response["Location"] == reverse("context:scope-detail", kwargs={"pk": scope.pk})

    def test_the_dialog_creates_and_says_so(self, client, admin):
        from core.tests.markup_audit import parse

        html = client.get(reverse("context:scope-create"), **DRAWER).content.decode()
        submit = next(
            node for node in parse(html).walk()
            if node.tag == "button" and node.attrs.get("type") == "submit"
        )

        assert " ".join(" ".join(t for n in submit.walk() for t in n.text).split()) == "Create"
        # One screen : no steps to walk.
        assert "mform-stepper" not in html

    def test_a_sub_scope_starts_from_its_parent(self, client, admin):
        parent = ScopeFactory()

        response = client.get(reverse("context:scope-create") + f"?parent={parent.pk}", **DRAWER)

        assert response.context["form"].initial["parent_scope"] == parent.pk

    def test_a_parent_out_of_reach_is_not_prefilled(self, client):
        mine, theirs = ScopeFactory(), ScopeFactory()
        client.force_login(_member("context.scope.create", "context.scope.read", scopes=[mine]))

        response = client.get(reverse("context:scope-create") + f"?parent={theirs.pk}", **DRAWER)

        assert "parent_scope" not in response.context["form"].initial

    def test_a_restricted_user_picks_a_parent_among_their_scopes(self):
        mine, theirs = ScopeFactory(), ScopeFactory()
        user = _member("context.scope.create", scopes=[mine])

        choices = set(ScopeCreateForm(user=user).fields["parent_scope"].queryset)

        assert choices == {mine}
        assert theirs not in choices

    def test_the_parent_already_set_stays_offered(self):
        """Or saving the form would silently detach the scope from it."""
        mine, theirs = ScopeFactory(), ScopeFactory()
        mine.parent_scope = theirs
        mine.save()
        user = _member("context.scope.update", scopes=[mine])

        choices = set(ScopeUpdateForm(instance=mine, user=user).fields["parent_scope"].queryset)

        assert theirs in choices


class TestEditingBySection:
    def test_each_card_of_the_page_is_a_section_of_the_form(self):
        assert ScopeUpdateForm.section_keys() == [
            "identity", "coverage", "boundaries", "sites", "managers", "planning",
        ]

    def test_a_section_opens_alone_and_takes_its_title(self, client, admin):
        scope = ScopeFactory()

        response = client.get(reverse("context:scope-update", kwargs={"pk": scope.pk}) + "?section=boundaries", **DRAWER)

        assert response.status_code == 200
        assert set(response.context["form"].fields) == {"boundaries", "justification_exclusions"}
        assert response.context["modal_title"] == "Boundaries and exclusions"
        assert 'name="_section"' in response.content.decode()

    def test_saving_a_section_leaves_the_rest_of_the_scope_alone(self, client, admin):
        scope = ScopeFactory(name="Kept", description="Kept too", geographic_scope="France")
        manager = UserFactory()
        scope.managers.add(manager)

        response = client.post(
            reverse("context:scope-update", kwargs={"pk": scope.pk}),
            {"_section": "boundaries", "boundaries": "The warehouse is left out.", "justification_exclusions": ""},
            **DRAWER,
        )

        scope.refresh_from_db()
        assert response.status_code == 204
        assert response["HX-Trigger"] == "formSaved"
        assert scope.boundaries == "The warehouse is left out."
        # Nothing else was asked, nothing else moved.
        assert (scope.name, scope.description, scope.geographic_scope) == ("Kept", "Kept too", "France")
        assert list(scope.managers.all()) == [manager]

    def test_an_unknown_section_is_a_404_not_the_whole_form(self, client, admin):
        scope = ScopeFactory()

        response = client.get(reverse("context:scope-update", kwargs={"pk": scope.pk}) + "?section=nope", **DRAWER)

        assert response.status_code == 404

    def test_a_creation_is_never_cut_to_a_section(self, client, admin):
        response = client.get(reverse("context:scope-create") + "?section=boundaries", **DRAWER)

        assert "name" in response.context["form"].fields

    def test_the_whole_form_saves_and_stays_on_the_scope(self, client, admin):
        scope = ScopeFactory()
        url = reverse("context:scope-update", kwargs={"pk": scope.pk})

        page = client.get(url)
        assert page.context["cancel_url"] == reverse("context:scope-detail", kwargs={"pk": scope.pk})
        response = client.post(url, {"name": "Renamed", "description": "Same."})

        assert response.status_code == 302
        assert response["Location"] == reverse("context:scope-detail", kwargs={"pk": scope.pk})

    def test_a_date_filled_in_by_the_lifecycle_is_explained(self):
        help_text = str(ScopeUpdateForm().fields["effective_date"].help_text)

        assert "comes into force" in help_text


class TestThePageSaysWhatIsMissing:
    def test_a_new_scope_lists_what_it_needs_and_opens_the_right_dialog(self, client, admin):
        scope = ScopeFactory()
        edit = reverse("context:scope-update", kwargs={"pk": scope.pk})

        html = client.get(reverse("context:scope-detail", kwargs={"pk": scope.pk})).content.decode()

        assert "To complete" in html
        assert "Fill in the boundaries and exclusions" in html
        assert f'href="{edit}?section=boundaries"' in html
        assert f'hx-get="{edit}?section=managers"' in html
        # Each card offers its own dialog.
        for key in ScopeUpdateForm.section_keys():
            assert f'{edit}?section={key}"' in html

    def test_a_complete_scope_shows_no_list(self, client, admin):
        from datetime import date

        from context.tests.factories import SiteFactory

        scope = ScopeFactory(boundaries="None.", geographic_scope="France", review_date=date(2030, 1, 1))
        scope.managers.add(admin)
        scope.included_sites.add(SiteFactory())

        html = client.get(reverse("context:scope-detail", kwargs={"pk": scope.pk})).content.decode()

        assert "todo-card" not in html

    def test_a_reader_sees_what_is_missing_but_no_way_to_edit(self, client):
        scope = ScopeFactory()
        client.force_login(_member("context.scope.read"))

        html = client.get(reverse("context:scope-detail", kwargs={"pk": scope.pk})).content.decode()

        assert "Fill in the boundaries and exclusions" in html
        assert "?section=" not in html
        assert reverse("context:scope-update", kwargs={"pk": scope.pk}) not in html


class TestTheEmptyRegister:
    def test_it_says_what_a_scope_is_and_offers_the_first_one(self, client, admin):
        html = client.get(reverse("context:scope-list")).content.decode()

        assert "No scope yet." in html
        assert "this is where to start" in html
        create = reverse("context:scope-create")
        assert f'href="{create}"' in html and f'hx-get="{create}"' in html

    def test_a_reader_is_offered_nothing_to_create(self, client):
        client.force_login(_member("context.scope.read"))

        html = client.get(reverse("context:scope-list")).content.decode()

        assert "No scope yet." in html
        assert "empty-state" in html
        assert f'href="{reverse("context:scope-create")}" hx-get' not in html

    def test_a_search_with_no_result_says_so_instead(self, client, admin):
        ScopeFactory(name="Head office")

        html = client.get(reverse("context:scope-table-body") + "?q=zzzz").content.decode()

        assert "Nothing matches." in html
        assert "No scope yet." not in html
