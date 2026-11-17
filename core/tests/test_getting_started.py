# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""The first steps of a new instance (``core/getting_started.py``).

An empty instance used to open on "Nothing pressing today - you're all
clear", an overall compliance of 0% in red and two empty matrices. It now
opens on what to do first, until the instance holds its first records.
"""

import pytest
from django.urls import reverse

from accounts.models import Permission
from accounts.tests.factories import GroupFactory, UserFactory
from context.tests.factories import ScopeFactory
from core import getting_started
from core.getting_started import DISMISS_KEY, STEPS, first_steps_for

pytestmark = pytest.mark.django_db


@pytest.fixture
def admin(client):
    user = UserFactory(is_superuser=True)
    client.force_login(user)
    return user


def _member(*codenames):
    user = UserFactory(is_superuser=False)
    group = GroupFactory()
    group.permissions.set(Permission.objects.filter(codename__in=codenames))
    group.users.add(user)
    return user


def _take_every_step():
    from assets.tests.factories import EssentialAssetFactory, SupportAssetFactory
    from compliance.tests.factories import FrameworkFactory
    from risks.tests.factories import RiskAssessmentFactory

    ScopeFactory()
    EssentialAssetFactory()
    SupportAssetFactory()
    FrameworkFactory()
    RiskAssessmentFactory()
    UserFactory()
    UserFactory()


class TestWhatTheListSays:
    def test_an_empty_instance_starts_with_its_scope(self, admin):
        steps = first_steps_for(admin)

        assert [step["key"] for step in steps["steps"]] == [
            "scope", "essential_asset", "support_asset", "framework", "risk_assessment", "team",
        ]
        assert (steps["done"], steps["total"]) == (0, 6)
        assert steps["next"]["key"] == "scope"
        assert steps["next"]["url"] == reverse("context:scope-list")
        assert steps["hidden"] is False

    def test_a_step_is_done_when_the_instance_holds_the_thing(self, admin):
        """Whoever created it : the list describes the instance, not the reader."""
        ScopeFactory()

        steps = first_steps_for(admin)

        assert steps["steps"][0]["done"] is True
        assert steps["next"]["key"] == "essential_asset"
        assert steps["done"] == 1

    def test_the_colleagues_step_counts_the_active_accounts(self, admin):
        UserFactory(is_active=False)
        assert not next(s for s in first_steps_for(admin)["steps"] if s["key"] == "team")["done"]

        UserFactory(is_active=True)
        assert next(s for s in first_steps_for(admin)["steps"] if s["key"] == "team")["done"]

    def test_a_reader_sees_the_steps_they_may_open(self):
        user = _member("context.scope.read", "assets.essential_asset.read", "assets.essential_asset.create")

        steps = first_steps_for(user)

        assert [step["key"] for step in steps["steps"]] == ["scope", "essential_asset"]
        # Shown, with no way to act : the scope is somebody else's to create.
        assert steps["steps"][0]["can_act"] is False
        assert steps["steps"][1]["can_act"] is True

    def test_a_reader_with_nothing_left_to_open_sees_no_list(self):
        ScopeFactory()

        assert first_steps_for(_member("context.scope.read")) is None

    def test_an_instance_that_took_every_step_has_no_list_for_good(self, admin, django_assert_num_queries):
        _take_every_step()

        assert first_steps_for(admin) is None
        # The answer is kept : a running instance pays nothing for it.
        with django_assert_num_queries(0):
            assert first_steps_for(admin) is None

    def test_every_step_leads_somewhere_and_names_real_permissions(self):
        from accounts.constants import PERMISSION_REGISTRY

        codenames = {
            f"{module}.{feature}.{action}"
            for module, features in PERMISSION_REGISTRY.items()
            for feature, spec in features.items()
            for action in spec.get("actions", [])
        }
        for step in STEPS:
            assert reverse(step.url_name)
            assert step.read in codenames and step.act in codenames, step.key
            # One sentence a newcomer understands, not a slogan.
            assert len(str(step.why).split()) >= 10


class TestTheDashboard:
    def test_an_empty_instance_opens_on_its_first_steps(self, client, admin):
        html = client.get(reverse("home")).content.decode()

        assert 'id="first-steps-title"' in html
        assert "Say what is covered" in html
        assert f'href="{reverse("context:scope-list")}"' in html
        assert "0 of 6 done" in html

    def test_it_does_not_claim_all_is_clear(self, client, admin):
        """True of an empty instance, and of no help to whoever opens it."""
        html = client.get(reverse("home")).content.decode()

        assert "all clear" not in html
        assert "Nothing to report yet" in html

    def test_it_shows_no_compliance_rate_before_a_framework_is_followed(self, client, admin):
        html = client.get(reverse("home")).content.decode()

        assert "No framework is followed yet" in html
        # No red arrow, no red bar : nothing has failed, nothing has begun.
        assert 'class="overall-compliance__delta ' not in html
        assert 'class="overall-compliance__bar overall-compliance__bar--none"' in html

    def test_a_started_instance_shows_the_dashboard_alone(self, client, admin):
        _take_every_step()

        html = client.get(reverse("home")).content.decode()

        assert 'id="first-steps-title"' not in html
        assert "Nothing to report yet" not in html

    def test_a_reader_hides_the_list_and_brings_it_back(self, client, admin):
        url = reverse("dashboard-first-steps")

        assert client.post(url).status_code == 302
        admin.refresh_from_db()
        assert DISMISS_KEY in admin.dismissed_helpers
        html = client.get(reverse("home")).content.decode()
        assert 'id="first-steps-title"' not in html
        # Hidden, not lost : the header offers it back while steps remain.
        assert 'name="show" value="1"' in html

        assert client.post(url, {"show": "1"}).status_code == 302
        admin.refresh_from_db()
        assert DISMISS_KEY not in admin.dismissed_helpers
        assert 'id="first-steps-title"' in client.get(reverse("home")).content.decode()

    def test_hiding_it_keeps_the_other_dismissed_helpers(self, client, admin):
        admin.dismissed_helpers = ["context.scope_list"]
        admin.save(update_fields=["dismissed_helpers"])

        client.post(reverse("dashboard-first-steps"))
        admin.refresh_from_db()
        assert admin.dismissed_helpers == ["context.scope_list", DISMISS_KEY]

        client.post(reverse("dashboard-first-steps"), {"show": "1"})
        admin.refresh_from_db()
        assert admin.dismissed_helpers == ["context.scope_list"]

    def test_hiding_needs_a_post_and_a_session(self, client):
        url = reverse("dashboard-first-steps")

        assert client.post(url).status_code == 302  # to the login page
        assert "/accounts/login/" in client.post(url)["Location"]
        client.force_login(UserFactory())
        assert client.get(url).status_code == 405


def test_the_answer_is_forgotten_between_tests():
    """The conftest fixture resets it : a full dataset in one test must not
    hide the first steps from the next."""
    assert getting_started._instance_started is False
