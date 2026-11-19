# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""A framework is created on one screen, then completed on its page.

What every entity of the usability standard does is checked for all of them
in ``core/tests/test_usability_standard.py``. This file holds what is
particular to the framework : its page asks for its requirements first and
opens their form on this framework, and its logo survives the edit of another
card.
"""

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.tests.factories import GroupFactory, UserFactory
from compliance.forms import FrameworkCreateForm
from compliance.models import Framework
from compliance.tests.factories import FrameworkFactory, RequirementFactory
from context.tests.factories import ScopeFactory
from core.completeness import completeness_of

pytestmark = pytest.mark.django_db

DRAWER = {"HTTP_HX_REQUEST": "true", "HTTP_HX_TARGET": "drawer-form-content"}
#: A one-pixel PNG, as the logo widget posts it.
LOGO = (
    "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk"
    "+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
)


@pytest.fixture
def admin(client):
    user = UserFactory(is_superuser=True)
    client.force_login(user)
    return user


class TestCreationIsShort:
    def test_it_asks_what_the_text_is_and_who_answers_for_it(self, admin):
        ScopeFactory()
        ScopeFactory()

        form = FrameworkCreateForm(user=admin)

        assert list(form.fields) == ["scopes", "name", "short_name", "type", "category", "owner"]
        assert form.is_multistep is False

    def test_a_framework_is_created_and_lands_on_its_page(self, client, admin):
        # With one scope to file it under, the scope is not asked.
        scope = ScopeFactory()

        response = client.post(
            reverse("compliance:framework-create"),
            {"name": "ISO/IEC 27001:2022", "short_name": "ISO 27001", "type": "standard",
             "category": "information_security", "owner": str(admin.pk)},
            **DRAWER,
        )

        framework = Framework.objects.get()
        assert response.status_code == 204, response.content.decode()[:400]
        assert response.headers["HX-Redirect"] == framework.get_absolute_url()
        assert framework.logo == "" and framework.owner == admin
        assert list(framework.scopes.all()) == [scope]


class TestWhatItStillNeeds:
    def test_a_new_framework_asks_for_its_requirements_first(self, client, admin):
        framework = FrameworkFactory()
        edit = reverse("compliance:framework-update", kwargs={"pk": framework.pk})

        report = completeness_of(framework)
        html = client.get(framework.get_absolute_url()).content.decode()

        assert [item.key for item in report.advised_missing] == ["requirements", "applicability", "review_date"]
        # Advice : nothing holds the lifecycle of a framework back.
        assert report.blocking_missing == [] and report.can_advance
        assert "Add requirements" in html
        assert f'href="{reverse("compliance:requirement-create")}?framework={framework.pk}"' in html
        assert f'href="{edit}?section=applicability"' in html
        assert f'href="{edit}?section=follow_up"' in html

    def test_the_form_of_a_requirement_opens_on_that_framework(self, client, admin):
        FrameworkFactory(name="Another text")
        framework = FrameworkFactory(name="ISO/IEC 27001:2022")

        html = client.get(reverse("compliance:requirement-create"), {"framework": str(framework.pk)}).content.decode()

        assert f'<option value="{framework.pk}" selected>' in html

    def test_a_framework_out_of_reach_is_not_preselected(self, client):
        mine, theirs = ScopeFactory(), ScopeFactory()
        group = GroupFactory()
        group.allowed_scopes.add(mine)
        user = UserFactory(is_superuser=False)
        group.users.add(user)
        framework = FrameworkFactory()
        framework.scopes.add(theirs)
        client.force_login(user)

        response = client.get(reverse("compliance:requirement-create"), {"framework": str(framework.pk)})

        assert str(framework.pk) not in response.content.decode()

    def test_what_is_done_leaves_the_list(self, admin):
        framework = FrameworkFactory(
            applicability_justification="<p>Asked by our clients.</p>", review_date="2027-06-30",
        )
        RequirementFactory(framework=framework)

        assert completeness_of(framework).is_complete


class TestTheLogo:
    def test_editing_another_card_keeps_it(self, client, admin):
        framework = FrameworkFactory(logo=LOGO, logo_16=LOGO, logo_32=LOGO, logo_64=LOGO)
        edit = reverse("compliance:framework-update", kwargs={"pk": framework.pk})

        response = client.post(edit, {"_section": "publication", "issuing_body": "ISO"}, **DRAWER)

        framework.refresh_from_db()
        assert response.status_code == 204, response.content.decode()[:400]
        assert framework.issuing_body == "ISO"
        assert framework.logo == LOGO and framework.logo_64 == LOGO

    def test_the_identity_card_can_remove_it(self, client, admin):
        scope = ScopeFactory()
        framework = FrameworkFactory(logo=LOGO, logo_16=LOGO, logo_32=LOGO, logo_64=LOGO)
        framework.scopes.add(scope)
        edit = reverse("compliance:framework-update", kwargs={"pk": framework.pk})

        response = client.post(
            edit,
            {"_section": "identity", "name": framework.name, "type": framework.type,
             "category": framework.category, "logo": "", "description": "", "scopes": [str(scope.pk)]},
            **DRAWER,
        )

        framework.refresh_from_db()
        assert response.status_code == 204, response.content.decode()[:400]
        assert framework.logo == "" and framework.logo_64 == ""


class TestThePage:
    def test_a_publication_nobody_filled_in_reads_as_one_line(self, client, admin):
        framework = FrameworkFactory()

        html = client.get(framework.get_absolute_url()).content.decode()

        assert (
            "Not filled in yet : Issuing body, Jurisdiction, Official link, Publication date, "
            "Effective date, Expiry date." in html
        )

    def test_the_empty_register_explains_and_offers_the_first_framework(self, client, admin):
        html = client.get(reverse("compliance:framework-list")).content.decode()

        assert "No framework yet." in html
        create = reverse("compliance:framework-create")
        assert f'href="{create}"' in html and f'hx-get="{create}"' in html


class TestTheApi:
    def test_one_framework_carries_its_completeness_and_a_list_does_not(self, admin):
        framework = FrameworkFactory()
        api = APIClient()
        api.force_authenticate(admin)

        one = api.get(f"/api/v1/compliance/frameworks/{framework.pk}/").json()
        one = one.get("data", one)
        many = api.get("/api/v1/compliance/frameworks/").json()
        rows = many.get("data", many.get("results", many))

        assert one["completeness"]["complete"] is False
        assert [item["key"] for item in one["completeness"]["missing"]] == [
            "requirements", "applicability", "review_date",
        ]
        assert all(item["blocking"] is False for item in one["completeness"]["missing"])
        assert rows and "completeness" not in rows[0]
