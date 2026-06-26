"""Tests for the autonomous Contract entity and its supplier-detail display."""

import datetime

import pytest
from django.urls import reverse

from assets.models import Contract
from assets.tests.factories import SupplierFactory


@pytest.mark.django_db
class TestContractModel:
    def test_multi_party_and_str(self):
        a = SupplierFactory(name="Acme")
        b = SupplierFactory(name="Globex")
        c = Contract.objects.create(label="Joint MSA", reference="CTR-1")
        c.suppliers.add(a, b)
        assert c.suppliers.count() == 2
        assert str(c) == "Joint MSA"
        # reachable from each party
        assert c in a.contracts.all()
        assert c in b.contracts.all()

    def test_amendment_parent_relation(self):
        s = SupplierFactory()
        parent = Contract.objects.create(label="MSA")
        parent.suppliers.add(s)
        amend = Contract.objects.create(label="Avenant 1", parent=parent)
        amend.suppliers.add(s)
        assert amend.is_amendment is True
        assert parent.is_amendment is False
        assert list(parent.amendments.all()) == [amend]

    def test_is_expired(self):
        today = datetime.date.today()
        past = Contract.objects.create(status="active", end_date=today - datetime.timedelta(days=1))
        future = Contract.objects.create(status="active", end_date=today + datetime.timedelta(days=1))
        terminated = Contract.objects.create(status="terminated", end_date=today - datetime.timedelta(days=1))
        assert past.is_expired is True
        assert future.is_expired is False
        assert terminated.is_expired is False  # only active contracts expire


@pytest.mark.django_db
class TestSupplierDetailContracts:
    def test_only_top_level_contracts_in_context(self, client):
        from accounts.tests.factories import UserFactory

        client.force_login(UserFactory(is_superuser=True, is_staff=True))
        s = SupplierFactory()
        top = Contract.objects.create(label="MSA")
        top.suppliers.add(s)
        amend = Contract.objects.create(label="Avenant", parent=top)
        amend.suppliers.add(s)
        resp = client.get(reverse("assets:supplier-detail", kwargs={"pk": s.pk}))
        assert resp.status_code == 200
        contracts = list(resp.context["contracts"])
        assert top in contracts
        assert amend not in contracts  # amendments are nested, not top-level cards
