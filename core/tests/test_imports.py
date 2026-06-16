"""Tests for the generic CSV bulk-import framework (core/imports).

The base behaviour is exercised through the concrete SupplierImporter so the
real column configuration is covered at the same time.
"""

import io
from datetime import date

import pytest
from django.utils import timezone

from accounts.tests.factories import UserFactory
from assets.imports import SupplierImporter
from assets.models import Supplier
from assets.tests.factories import SupplierFactory, SupplierTypeFactory
from context.models import Tag
from context.tests.factories import ScopeFactory
from core.imports import registry

pytestmark = pytest.mark.django_db


def _csv(text):
    return io.BytesIO(text.encode("utf-8"))


def _csv_bom(text):
    return io.BytesIO(text.encode("utf-8-sig"))


HEADER = (
    "name,owner,type,criticality,status,description,contact_name,contact_email,"
    "contact_phone,website,address,country,contract_reference,contract_start_date,"
    "contract_end_date,notes,scopes,tags,created_at"
)


class TestRegistry:
    def test_supplier_importer_is_registered(self):
        assert registry.get("supplier") is SupplierImporter

    def test_unknown_entity_returns_none(self):
        assert registry.get("does-not-exist") is None


class TestParsing:
    def test_parse_strips_bom_and_whitespace(self):
        importer = SupplierImporter()
        rows = importer.parse_csv(_csv_bom(f"{HEADER}\n  Acme  ,,,,,,,,,,,,,,,,,\n"))
        assert rows[0]["name"] == "Acme"

    def test_empty_file_is_fatal(self):
        importer = SupplierImporter()
        result = importer.validate(importer.parse_csv(_csv("")), UserFactory())
        assert result.fatal


class TestValidation:
    def test_missing_required_column_is_fatal(self):
        importer = SupplierImporter()
        rows = importer.parse_csv(_csv("owner,type\njane@example.com,X\n"))
        result = importer.validate(rows, UserFactory())
        assert result.fatal
        assert not result.valid

    def test_blank_name_is_row_error(self):
        # Row carries a value (criticality) so it is not skipped as a blank
        # line, but the required name is missing -> a per-row error.
        importer = SupplierImporter()
        rows = importer.parse_csv(_csv(f"{HEADER}\n,,,high,,,,,,,,,,,,,,\n"))
        result = importer.validate(rows, UserFactory())
        assert result.valid == []
        assert len(result.errors) == 1
        assert result.errors[0]["row_number"] == 2

    def test_owner_defaults_to_current_user(self):
        importer = SupplierImporter()
        user = UserFactory()
        rows = importer.parse_csv(_csv(f"{HEADER}\nAcme,,,,,,,,,,,,,,,,,\n"))
        result = importer.validate(rows, user)
        assert result.valid[0]["fields"]["owner"] == user

    def test_owner_resolved_by_email(self):
        importer = SupplierImporter()
        owner = UserFactory(email="owner@corp.example")
        rows = importer.parse_csv(
            _csv(f"{HEADER}\nAcme,owner@corp.example,,,,,,,,,,,,,,,,\n")
        )
        result = importer.validate(rows, UserFactory())
        assert result.valid[0]["fields"]["owner"] == owner

    def test_unknown_owner_email_is_error(self):
        importer = SupplierImporter()
        rows = importer.parse_csv(
            _csv(f"{HEADER}\nAcme,ghost@corp.example,,,,,,,,,,,,,,,,\n")
        )
        result = importer.validate(rows, UserFactory())
        assert not result.valid
        assert "ghost@corp.example" in result.errors[0]["messages"][0]

    def test_unknown_type_is_error(self):
        importer = SupplierImporter()
        rows = importer.parse_csv(_csv(f"{HEADER}\nAcme,,NoSuchType,,,,,,,,,,,,,,,\n"))
        result = importer.validate(rows, UserFactory())
        assert not result.valid
        assert result.errors

    def test_known_type_resolved_by_name(self):
        importer = SupplierImporter()
        stype = SupplierTypeFactory(name="Cloud provider")
        rows = importer.parse_csv(
            _csv(f"{HEADER}\nAcme,,Cloud provider,,,,,,,,,,,,,,,\n")
        )
        result = importer.validate(rows, UserFactory())
        assert result.valid[0]["fields"]["type"] == stype

    def test_invalid_choice_is_error(self):
        importer = SupplierImporter()
        rows = importer.parse_csv(_csv(f"{HEADER}\nAcme,,,nope,,,,,,,,,,,,,,\n"))
        result = importer.validate(rows, UserFactory())
        assert not result.valid

    def test_invalid_date_is_error(self):
        importer = SupplierImporter()
        rows = importer.parse_csv(
            _csv(f"{HEADER}\nAcme,,,,,,,,,,,,,31-12-2026,,,,\n")
        )
        result = importer.validate(rows, UserFactory())
        assert not result.valid

    def test_invalid_email_and_url_are_errors(self):
        importer = SupplierImporter()
        rows = importer.parse_csv(
            _csv(f"{HEADER}\nAcme,,,,,,,not-an-email,,not-a-url,,,,,,,,\n")
        )
        result = importer.validate(rows, UserFactory())
        assert not result.valid
        assert len(result.errors[0]["messages"]) == 2

    def test_unknown_scope_is_error(self):
        importer = SupplierImporter()
        rows = importer.parse_csv(
            _csv(f"{HEADER}\nAcme,,,,,,,,,,,,,,,,SCOP-999,\n")
        )
        result = importer.validate(rows, UserFactory())
        assert not result.valid

    def test_scope_resolved_by_reference(self):
        importer = SupplierImporter()
        scope = ScopeFactory()
        rows = importer.parse_csv(
            _csv(f"{HEADER}\nAcme,,,,,,,,,,,,,,,,{scope.reference},\n")
        )
        result = importer.validate(rows, UserFactory())
        assert list(result.valid[0]["m2m"]["scopes"]) == [scope]

    def test_tags_are_auto_created_with_warning(self):
        importer = SupplierImporter()
        rows = importer.parse_csv(_csv(f"{HEADER}\nAcme,,,,,,,,,,,,,,,,,PII;EU\n"))
        result = importer.validate(rows, UserFactory())
        assert Tag.objects.filter(name="PII").exists()
        assert Tag.objects.filter(name="EU").exists()
        assert len(result.valid[0]["m2m"]["tags"]) == 2
        assert any("PII" in w for w in result.warnings)

    def test_blank_lines_are_skipped(self):
        importer = SupplierImporter()
        rows = importer.parse_csv(_csv(f"{HEADER}\nAcme,,,,,,,,,,,,,,,,,\n,,,,,,,,,,,,,,,,,\n"))
        result = importer.validate(rows, UserFactory())
        assert len(result.valid) == 1


class TestExecution:
    def test_execute_creates_suppliers_with_reference_and_created_by(self):
        importer = SupplierImporter()
        user = UserFactory()
        rows = importer.parse_csv(_csv(f"{HEADER}\nAcme,,,high,active,,,,,,,,,,,,,\n"))
        result = importer.validate(rows, user)
        outcome = importer.execute(result.valid, user)
        assert len(outcome.created) == 1
        assert outcome.updated == []
        supplier = Supplier.objects.get(name="Acme")
        assert supplier.reference.startswith("SUPP-")
        assert supplier.created_by == user
        assert supplier.owner == user
        assert supplier.criticality == "high"

    def test_execute_sets_m2m(self):
        importer = SupplierImporter()
        user = UserFactory()
        scope = ScopeFactory()
        rows = importer.parse_csv(
            _csv(f"{HEADER}\nAcme,,,,,,,,,,,,,,,,{scope.reference},PII\n")
        )
        result = importer.validate(rows, user)
        importer.execute(result.valid, user)
        supplier = Supplier.objects.get(name="Acme")
        assert list(supplier.scopes.all()) == [scope]
        assert supplier.tags.filter(name="PII").exists()

    def test_execute_is_atomic(self):
        """A failure mid-batch rolls back every row created in the call."""
        importer = SupplierImporter()
        user = UserFactory()
        # Two valid rows, then poison the second so full_clean fails on save.
        rows = importer.parse_csv(
            _csv(f"{HEADER}\nGood,,,,,,,,,,,,,,,,,\nBad,,,,,,,,,,,,,,,,,\n")
        )
        result = importer.validate(rows, user)
        result.valid[1]["fields"]["name"] = "x" * 300  # exceeds max_length=255
        with pytest.raises(Exception):
            importer.execute(result.valid, user)
        assert Supplier.objects.count() == 0


class TestConflicts:
    def test_no_conflict_when_name_is_new(self):
        importer = SupplierImporter()
        rows = importer.parse_csv(_csv(f"{HEADER}\nFresh,,,,,,,,,,,,,,,,,,\n"))
        result = importer.validate(rows, UserFactory())
        assert result.valid[0]["conflict"] is None

    def test_existing_name_is_flagged_as_conflict(self):
        existing = SupplierFactory(name="Acme")
        importer = SupplierImporter()
        rows = importer.parse_csv(_csv(f"{HEADER}\nAcme,,,,,,,,,,,,,,,,,,\n"))
        result = importer.validate(rows, UserFactory())
        conflict = result.valid[0]["conflict"]
        assert conflict is not None
        assert conflict["pk"] == str(existing.pk)

    def test_conflict_matching_is_case_insensitive(self):
        SupplierFactory(name="Acme")
        importer = SupplierImporter()
        rows = importer.parse_csv(_csv(f"{HEADER}\nACME,,,,,,,,,,,,,,,,,,\n"))
        result = importer.validate(rows, UserFactory())
        assert result.valid[0]["conflict"] is not None

    def test_ambiguous_name_is_row_error(self):
        SupplierFactory(name="Acme")
        SupplierFactory(name="Acme")
        importer = SupplierImporter()
        rows = importer.parse_csv(_csv(f"{HEADER}\nAcme,,,,,,,,,,,,,,,,,,\n"))
        result = importer.validate(rows, UserFactory())
        assert not result.valid
        assert result.errors

    def test_conflict_skipped_when_not_replaced(self):
        existing = SupplierFactory(name="Acme", criticality="low")
        importer = SupplierImporter()
        user = UserFactory()
        rows = importer.parse_csv(_csv(f"{HEADER}\nAcme,,,high\n"))
        result = importer.validate(rows, user)
        # replace flag not set -> keep existing untouched
        outcome = importer.execute(result.valid, user)
        assert outcome.created == []
        assert len(outcome.skipped) == 1
        existing.refresh_from_db()
        assert existing.criticality == "low"
        assert Supplier.objects.filter(name="Acme").count() == 1

    def test_conflict_updates_existing_when_replaced(self):
        existing = SupplierFactory(name="Acme", criticality="low")
        importer = SupplierImporter()
        user = UserFactory()
        rows = importer.parse_csv(_csv(f"{HEADER}\nAcme,,,high\n"))
        result = importer.validate(rows, user)
        result.valid[0]["replace"] = True
        outcome = importer.execute(result.valid, user)
        assert outcome.created == []
        assert len(outcome.updated) == 1
        existing.refresh_from_db()
        assert existing.criticality == "high"
        assert Supplier.objects.filter(name="Acme").count() == 1

    def test_replace_preserves_original_created_at(self):
        existing = SupplierFactory(name="Acme")
        original_created = existing.created_at
        importer = SupplierImporter()
        user = UserFactory()
        # CSV carries a created_at, which must be ignored on replacement.
        rows = importer.parse_csv(_csv(f"{HEADER}\nAcme,,,,,,,,,,,,,,,,,,2000-01-01\n"))
        result = importer.validate(rows, user)
        result.valid[0]["replace"] = True
        importer.execute(result.valid, user)
        existing.refresh_from_db()
        assert existing.created_at == original_created


class TestLegacyCreatedAt:
    def test_created_at_is_imported_over_auto_now_add(self):
        importer = SupplierImporter()
        user = UserFactory()
        rows = importer.parse_csv(
            _csv(f"{HEADER}\nAcme,,,,,,,,,,,,,,,,,,2020-01-15\n")
        )
        result = importer.validate(rows, user)
        # created_at is routed to the post-save bucket, not the constructor.
        assert "created_at" not in result.valid[0]["fields"]
        assert result.valid[0]["post"]["created_at"].year == 2020
        importer.execute(result.valid, user)
        supplier = Supplier.objects.get(name="Acme")
        # Stored as an aware datetime; compare in the project's local timezone.
        assert timezone.localtime(supplier.created_at).date() == date(2020, 1, 15)

    def test_blank_created_at_falls_back_to_now(self):
        importer = SupplierImporter()
        user = UserFactory()
        rows = importer.parse_csv(_csv(f"{HEADER}\nAcme,,,,,,,,,,,,,,,,,,\n"))
        result = importer.validate(rows, user)
        assert result.valid[0]["post"] == {}
        importer.execute(result.valid, user)
        assert Supplier.objects.get(name="Acme").created_at is not None

    def test_invalid_created_at_is_error(self):
        importer = SupplierImporter()
        rows = importer.parse_csv(
            _csv(f"{HEADER}\nAcme,,,,,,,,,,,,,,,,,,15/01/2020\n")
        )
        result = importer.validate(rows, UserFactory())
        assert not result.valid
        assert result.errors


class TestSample:
    def test_sample_has_header_and_example_row(self):
        importer = SupplierImporter()
        content = importer.generate_sample_csv().getvalue().decode("utf-8-sig")
        lines = content.splitlines()
        assert lines[0].startswith("name,owner,type")
        assert "Acme Cloud Services" in lines[1]

    def test_column_docs_cover_all_columns(self):
        importer = SupplierImporter()
        docs = importer.column_docs()
        assert len(docs) == len(importer.columns)
        criticality = next(d for d in docs if d["name"] == "criticality")
        assert "high" in criticality["allowed"]
