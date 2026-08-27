"""Tests for supplier sub-processors (sous-délégataires) and subsidiaries (filiales).

Covers the SupplierSubprocessor link model, the parent_company self-FK, their
CRUD views (HTMX drawer), the DRF API and the detail-page rendering.
"""

import pytest
from django.db import IntegrityError
from django.db.utils import DataError
from django.urls import reverse

from accounts.tests.factories import UserFactory
from assets.forms import SupplierSubprocessorForm
from assets.models import Supplier, SupplierSubprocessor
from assets.tests.factories import SupplierFactory, SupplierSubprocessorFactory

HX = {"HTTP_HX_REQUEST": "true", "HTTP_HX_TARGET": "drawer-form-content"}


@pytest.mark.django_db
class TestSubsidiaries:
    def test_parent_company_and_reverse_subsidiaries(self):
        parent = SupplierFactory(name="Parent Co")
        child = SupplierFactory(name="Child Co", parent_company=parent)
        assert child.parent_company == parent
        assert list(parent.subsidiaries.all()) == [child]
        assert child.parent_company_name == "Parent Co"

    def test_parent_deletion_nullifies_child(self):
        parent = SupplierFactory()
        child = SupplierFactory(parent_company=parent)
        parent.delete()
        child.refresh_from_db()
        assert child.parent_company is None


@pytest.mark.django_db
class TestSupplierSubprocessorModel:
    def test_str_and_reference(self):
        a, b = SupplierFactory(), SupplierFactory()
        link = SupplierSubprocessor.objects.create(supplier=a, subprocessor=b)
        assert link.reference.startswith("SSPR-")
        assert str(link) == f"{a.reference} → {b.reference}"
        assert link.supplier_name == a.name
        assert link.subprocessor_name == b.name

    def test_reverse_relations(self):
        a, b = SupplierFactory(), SupplierFactory()
        SupplierSubprocessor.objects.create(supplier=a, subprocessor=b)
        assert a.subprocessors.count() == 1
        assert b.engaged_by.count() == 1

    def test_unique_constraint(self):
        a, b = SupplierFactory(), SupplierFactory()
        SupplierSubprocessor.objects.create(supplier=a, subprocessor=b)
        with pytest.raises(IntegrityError):
            SupplierSubprocessor.objects.create(supplier=a, subprocessor=b)

    def test_self_reference_forbidden_by_constraint(self):
        a = SupplierFactory()
        with pytest.raises((IntegrityError, DataError)):
            SupplierSubprocessor.objects.create(supplier=a, subprocessor=a)

    def test_cascade_on_supplier_delete_but_protect_on_subprocessor(self):
        a, b = SupplierFactory(), SupplierFactory()
        SupplierSubprocessor.objects.create(supplier=a, subprocessor=b)
        # Deleting the délégataire cascades the link.
        a.delete()
        assert SupplierSubprocessor.objects.count() == 0
        # The subprocessor side is PROTECT: cannot delete while engaged.
        c = SupplierFactory()
        SupplierSubprocessor.objects.create(supplier=c, subprocessor=b)
        from django.db.models import ProtectedError
        with pytest.raises(ProtectedError):
            b.delete()


@pytest.mark.django_db
class TestSupplierSubprocessorForm:
    def test_excludes_self_from_choices(self):
        s = SupplierFactory()
        other = SupplierFactory()
        form = SupplierSubprocessorForm(supplier=s)
        choices = list(form.fields["subprocessor"].queryset)
        assert s not in choices
        assert other in choices

    def test_rejects_self(self):
        s = SupplierFactory()
        form = SupplierSubprocessorForm(
            data={"subprocessor": str(s.pk), "criticality": "medium", "status": "active"},
            supplier=s,
        )
        assert not form.is_valid()
        assert "subprocessor" in form.errors

    def test_end_before_start_rejected(self):
        s, b = SupplierFactory(), SupplierFactory()
        form = SupplierSubprocessorForm(
            data={
                "subprocessor": str(b.pk), "criticality": "medium", "status": "active",
                "start_date": "2025-06-01", "end_date": "2025-01-01",
            },
            supplier=s,
        )
        assert not form.is_valid()
        assert "end_date" in form.errors


@pytest.mark.django_db
class TestSupplierSubprocessorViews:
    def _login(self, client):
        client.force_login(UserFactory(is_superuser=True, is_staff=True))

    def test_create_via_drawer(self, client):
        self._login(client)
        s, b = SupplierFactory(), SupplierFactory()
        url = reverse("assets:supplier-subprocessor-create", kwargs={"supplier_pk": s.pk})
        resp = client.post(
            url,
            {"subprocessor": str(b.pk), "purpose": "Hosting", "criticality": "high", "status": "active"},
            **HX,
        )
        assert resp.status_code == 204
        assert resp.headers["HX-Trigger"] == "formSaved"
        link = s.subprocessors.get()
        assert link.subprocessor == b
        assert link.purpose == "Hosting"
        assert link.created_by is not None

    def test_update_and_delete(self, client):
        self._login(client)
        link = SupplierSubprocessorFactory(purpose="Old")
        upd = reverse("assets:supplier-subprocessor-update", kwargs={"pk": link.pk})
        resp = client.post(
            upd,
            {"subprocessor": str(link.subprocessor.pk), "purpose": "New", "criticality": "low", "status": "suspended"},
            **HX,
        )
        assert resp.status_code == 204
        link.refresh_from_db()
        assert link.purpose == "New" and link.status == "suspended"

        dele = reverse("assets:supplier-subprocessor-delete", kwargs={"pk": link.pk})
        resp = client.post(dele, **HX)
        assert resp.status_code == 204
        assert not SupplierSubprocessor.objects.filter(pk=link.pk).exists()

    def test_detail_renders_sections(self, client):
        self._login(client)
        parent = SupplierFactory(name="ParentCorp")
        s = SupplierFactory(parent_company=parent)
        sub = SupplierFactory(name="SubProc SA")
        SupplierSubprocessor.objects.create(supplier=s, subprocessor=sub, purpose="DNS")
        html = client.get(reverse("assets:supplier-detail", kwargs={"pk": s.pk})).content.decode()
        assert "Sub-processors" in html
        assert "SubProc SA" in html
        assert "ParentCorp" in html
        assert "Add sub-processor" in html


@pytest.mark.django_db
class TestSupplierSubprocessorAPI:
    def _login(self, client):
        client.force_login(UserFactory(is_superuser=True, is_staff=True))

    def test_crud_and_self_validation(self, client):
        self._login(client)
        s, b = SupplierFactory(), SupplierFactory()
        create = client.post(
            "/api/v1/assets/supplier-subprocessors/",
            {"supplier": str(s.pk), "subprocessor": str(b.pk), "purpose": "Payments", "criticality": "high"},
            content_type="application/json",
        )
        assert create.status_code == 201, create.content
        # Self-reference is rejected by the serializer.
        bad = client.post(
            "/api/v1/assets/supplier-subprocessors/",
            {"supplier": str(s.pk), "subprocessor": str(s.pk)},
            content_type="application/json",
        )
        assert bad.status_code == 400

    def test_supplier_nested_actions(self, client):
        self._login(client)
        parent = SupplierFactory()
        s = SupplierFactory(parent_company=parent)
        b = SupplierFactory()
        SupplierSubprocessor.objects.create(supplier=s, subprocessor=b)
        subp = client.get(f"/api/v1/assets/suppliers/{s.pk}/subprocessors/")
        assert subp.status_code == 200
        assert len(subp.json()["data"]) == 1
        subs = client.get(f"/api/v1/assets/suppliers/{parent.pk}/subsidiaries/")
        assert subs.status_code == 200
        assert [row["id"] for row in subs.json()["data"]] == [str(s.pk)]
