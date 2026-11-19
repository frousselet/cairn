# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""An asset group is created on one screen, then filled on its page.

What every entity of the usability standard does is checked for all of them
in ``core/tests/test_usability_standard.py``. This file holds what is
particular to the group : its members. The interface listed them and offered
no way to choose them (the REST API and the MCP server alone could); the
group page now has a *Members* card that opens the dialog which picks them.
"""

import pytest
from django.urls import reverse

from accounts.tests.factories import UserFactory
from assets.forms import AssetGroupCreateForm
from assets.models import AssetGroup
from assets.tests.factories import SupportAssetFactory
from context.tests.factories import ScopeFactory
from core.completeness import completeness_of

pytestmark = pytest.mark.django_db

DRAWER = {"HTTP_HX_REQUEST": "true", "HTTP_HX_TARGET": "drawer-form-content"}


@pytest.fixture
def admin(client):
    user = UserFactory(is_superuser=True)
    client.force_login(user)
    return user


def _group(**kwargs):
    return AssetGroup.objects.create(name="Production servers", type="hardware", **kwargs)


def test_creation_asks_what_the_group_gathers_and_who_to_ask(admin):
    ScopeFactory()
    ScopeFactory()

    form = AssetGroupCreateForm(user=admin)

    assert list(form.fields) == ["scopes", "name", "description", "type", "owner"]
    assert form.is_multistep is False


def test_a_new_group_asks_for_its_members_first(client, admin):
    group = _group()
    edit = reverse("assets:group-update", kwargs={"pk": group.pk})

    html = client.get(group.get_absolute_url()).content.decode()

    assert [item.key for item in completeness_of(group).advised_missing] == ["members"]
    assert "Add members" in html
    assert f'href="{edit}?section=members"' in html
    assert "No support asset in this group yet." in html


def test_the_members_card_picks_them(client, admin):
    group = _group()
    first, second = SupportAssetFactory(name="Payroll server"), SupportAssetFactory(name="Mail server")
    edit = reverse("assets:group-update", kwargs={"pk": group.pk})

    dialog = client.get(f"{edit}?section=members", **DRAWER).content.decode()
    assert "Payroll server" in dialog and "Mail server" in dialog

    response = client.post(edit, {"_section": "members", "members": [str(first.pk), str(second.pk)]}, **DRAWER)

    assert response.status_code == 204, response.content.decode()[:300]
    assert set(group.members.all()) == {first, second}
    assert completeness_of(group).is_complete
    page = client.get(group.get_absolute_url()).content.decode()
    assert "Payroll server" in page and "Add members" not in page


def test_saving_the_identity_leaves_the_members_alone(client, admin):
    group = _group()
    member = SupportAssetFactory()
    group.members.set([member])
    edit = reverse("assets:group-update", kwargs={"pk": group.pk})

    response = client.post(
        edit, {"_section": "identity", "name": "Renamed", "type": "hardware", "status": "active", "description": ""},
        **DRAWER,
    )

    assert response.status_code == 204, response.content.decode()[:300]
    group.refresh_from_db()
    assert group.name == "Renamed"
    assert list(group.members.all()) == [member]


def test_the_empty_register_explains_and_offers_the_first_group(client, admin):
    html = client.get(reverse("assets:group-list")).content.decode()

    assert "No asset group yet." in html
    create = reverse("assets:group-create")
    assert f'href="{create}"' in html and f'hx-get="{create}"' in html
