# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""User provisioning via the invitation flow: unusable password, single-use
activation link, and the DRF ``users/invite`` endpoint."""

import pytest
from django.core.exceptions import ValidationError
from django.test import Client
from rest_framework.test import APIClient

from accounts.constants import AccessEventType
from accounts.invitations import build_activation_url, provision_user
from accounts.models import AccessLog, Group, User
from accounts.tests.factories import GroupFactory, PermissionFactory, UserFactory

pytestmark = pytest.mark.django_db

CREATE = "system.users.create"


def _grant(user, codename):
    group = GroupFactory()
    group.permissions.add(PermissionFactory(codename=codename))
    group.users.add(user)


class TestProvisionUser:
    def test_creates_user_with_unusable_password(self):
        actor = UserFactory()
        user = provision_user(email="Jane@Corp.example", last_name="Doe",
                              first_name="Jane", created_by=actor)
        assert user.has_usable_password() is False
        assert user.email == "Jane@corp.example"  # domain normalized
        assert user.created_by_id == actor.pk

    def test_logs_invitation(self):
        actor = UserFactory()
        provision_user(email="log@corp.example", last_name="Doe", created_by=actor)
        assert AccessLog.objects.filter(
            event_type=AccessEventType.USER_INVITED,
            email_attempted="log@corp.example",
        ).exists()

    def test_assigns_groups_by_name(self):
        Group.objects.get_or_create(name="Contributeur")
        user = provision_user(email="g@corp.example", last_name="Doe",
                             group_names=["Contributeur"])
        assert user.custom_groups.filter(name="Contributeur").exists()

    def test_unknown_group_raises(self):
        with pytest.raises(ValidationError):
            provision_user(email="x@corp.example", last_name="Doe",
                          group_names=["Ghost"])
        assert not User.objects.filter(email="x@corp.example").exists()

    def test_duplicate_email_raises(self):
        UserFactory(email="dup@corp.example")
        with pytest.raises(ValidationError):
            provision_user(email="dup@corp.example", last_name="Doe")


class TestActivationView:
    def test_activation_sets_password_and_logs_in(self):
        user = provision_user(email="act@corp.example", last_name="Doe")
        url = build_activation_url(user)  # SITE_URL is empty in tests -> path only
        client = Client()

        assert client.get(url).status_code == 200

        resp = client.post(url, {
            "new_password1": "Str0ng!Pass99",
            "new_password2": "Str0ng!Pass99",
        })
        assert resp.status_code == 302
        user.refresh_from_db()
        assert user.has_usable_password() is True
        assert AccessLog.objects.filter(
            event_type=AccessEventType.ACCOUNT_ACTIVATED, user=user
        ).exists()

    def test_link_is_single_use(self):
        user = provision_user(email="once@corp.example", last_name="Doe")
        url = build_activation_url(user)
        client = Client()
        client.post(url, {"new_password1": "Str0ng!Pass99",
                          "new_password2": "Str0ng!Pass99"})
        # Password changed -> the token no longer validates.
        resp = client.get(url)
        assert b"invalid" in resp.content.lower()

    def test_invalid_token_shows_error(self):
        user = provision_user(email="bad@corp.example", last_name="Doe")
        from django.utils.http import urlsafe_base64_encode
        from django.utils.encoding import force_bytes

        uid = urlsafe_base64_encode(force_bytes(user.pk))
        resp = Client().get(f"/accounts/activate/{uid}/not-a-real-token/")
        assert resp.status_code == 200
        assert b"invalid" in resp.content.lower()


class TestInviteAPI:
    def test_requires_permission(self):
        client = APIClient()
        client.force_authenticate(user=UserFactory())  # no permission
        resp = client.post("/api/v1/users/invite/",
                           {"email": "n@corp.example", "last_name": "Doe"},
                           format="json")
        assert resp.status_code == 403

    def test_invite_provisions_and_returns_activation_url(self):
        actor = UserFactory()
        _grant(actor, CREATE)
        client = APIClient()
        client.force_authenticate(user=actor)
        resp = client.post("/api/v1/users/invite/",
                           {"email": "inv@corp.example", "last_name": "Doe",
                            "first_name": "In"},
                           format="json")
        assert resp.status_code == 201
        body = resp.json()["data"]
        assert body["email"] == "inv@corp.example"
        assert body["activation_url"]
        created = User.objects.get(email="inv@corp.example")
        assert created.has_usable_password() is False

    def test_invite_never_accepts_password(self):
        actor = UserFactory(is_superuser=True)
        client = APIClient()
        client.force_authenticate(user=actor)
        resp = client.post("/api/v1/users/invite/",
                           {"email": "np@corp.example", "last_name": "Doe",
                            "password": "Str0ng!Pass99"},
                           format="json")
        assert resp.status_code == 201
        # The password field is not part of the invite serializer; the account
        # is provisioned with an unusable password regardless.
        assert User.objects.get(email="np@corp.example").has_usable_password() is False
