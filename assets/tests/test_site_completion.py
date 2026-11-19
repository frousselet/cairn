# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""A site is created on one screen, then completed on its page.

What every entity of the usability standard does is checked for all of them
in ``core/tests/test_usability_standard.py``. This file holds what is
particular to the site : its type is a decision the model used to take
("Other"), and the very first site is asked for no parent.
"""

import pytest
from django.urls import reverse

from accounts.tests.factories import UserFactory
from assets.forms import SiteCreateForm
from context.models import Site
from context.tests.factories import ScopeFactory, SiteFactory
from core.completeness import completeness_of

pytestmark = pytest.mark.django_db

DRAWER = {"HTTP_HX_REQUEST": "true", "HTTP_HX_TARGET": "drawer-form-content"}


@pytest.fixture
def admin(client):
    user = UserFactory(is_superuser=True)
    client.force_login(user)
    return user


def test_the_first_site_is_asked_for_no_parent(admin):
    ScopeFactory()

    form = SiteCreateForm(user=admin)

    assert set(form.fields) == {"name", "type", "address", "description"}


def test_with_sites_and_scopes_it_still_fits_one_screen(admin):
    ScopeFactory()
    ScopeFactory()
    SiteFactory()

    form = SiteCreateForm(user=admin)

    assert set(form.fields) == {"name", "type", "address", "description", "parent_site", "scopes"}
    assert form.is_multistep is False


def test_the_type_is_a_decision_nobody_takes_for_the_reader(client, admin):
    ScopeFactory()
    assert Site._meta.get_field("type").default == "other"

    html = client.get(reverse("assets:site-create"), **DRAWER).content.decode()
    select = html[html.index('name="type"'):]
    select = select[:select.index("</select>")]
    assert 'value="" selected>Choose…<' in select and select.count("selected") == 1

    refused = client.post(reverse("assets:site-create"), {"name": "Head office"}, **DRAWER)
    assert refused.status_code == 200
    assert "Choose a value for &quot;Type&quot;." in refused.content.decode()
    assert not Site.objects.exists()


def test_a_new_site_lists_what_would_make_it_useful(client, admin):
    site = SiteFactory(address="")
    edit = reverse("assets:site-update", kwargs={"pk": site.pk})

    html = client.get(site.get_absolute_url()).content.decode()

    assert [item.key for item in completeness_of(site).advised_missing] == ["address", "hosted_assets"]
    assert "Fill in the address" in html
    assert f'href="{edit}?section=identity"' in html
    assert f'href="{reverse("assets:site-asset-dependency-list")}"' in html


def test_the_empty_register_explains_and_offers_the_first_site(client, admin):
    html = client.get(reverse("assets:site-list")).content.decode()

    assert "No site yet." in html
    create = reverse("assets:site-create")
    assert f'href="{create}"' in html and f'hx-get="{create}"' in html
