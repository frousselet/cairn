"""CSV bulk-import configuration for suppliers.

First consumer of the generic import framework (``core/imports``). It declares
the supplier CSV columns and how to resolve related objects:

- ``owner``  : User looked up by email; blank falls back to the importing user.
- ``type``   : SupplierType looked up by name; error if it does not exist.
- ``scopes`` : Scopes looked up by reference or name; error if not found.
- ``tags``   : Tags looked up by name; created automatically when missing.
"""

from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy as _lazy

from accounts.models import User
from assets.constants import SupplierCriticality, SupplierStatus
from assets.models.supplier import Supplier, SupplierType
from context.models import Scope, Tag
from core.imports import registry
from core.imports.base import ColumnSpec, EntityImporter, ImportValueError


def _resolve_owner(value, ctx):
    """Resolve the supplier owner by email, defaulting to the current user."""
    if not value:
        return ctx.user
    try:
        return User.objects.get(email__iexact=value)
    except User.DoesNotExist:
        raise ImportValueError(
            _('No user found with email "%(email)s".') % {"email": value}
        )


def _resolve_type(value, ctx):
    """Resolve a SupplierType by name (must already exist)."""
    if not value:
        return None
    try:
        return SupplierType.objects.get(name__iexact=value)
    except SupplierType.DoesNotExist:
        raise ImportValueError(
            _('No supplier type named "%(name)s". Create it first.') % {"name": value}
        )
    except SupplierType.MultipleObjectsReturned:
        raise ImportValueError(
            _('Several supplier types match "%(name)s".') % {"name": value}
        )


def _split_multi(value):
    return [part.strip() for part in value.split(";") if part.strip()]


def _resolve_scopes(value, ctx):
    """Resolve scopes by reference or name (all must exist)."""
    if not value:
        return []
    scopes = []
    for token in _split_multi(value):
        scope = Scope.objects.filter(reference__iexact=token).first()
        if scope is None:
            scope = Scope.objects.filter(name__iexact=token).first()
        if scope is None:
            raise ImportValueError(
                _('No scope matching reference or name "%(token)s".') % {"token": token}
            )
        scopes.append(scope)
    return scopes


def _resolve_tags(value, ctx):
    """Resolve tags by name, creating any that do not exist yet."""
    if not value:
        return []
    tags = []
    for name in _split_multi(value):
        tag = Tag.objects.filter(name__iexact=name).first()
        if tag is None:
            tag = Tag.objects.create(name=name)
            ctx.warnings.append(
                _('Tag "%(name)s" will be created.') % {"name": name}
            )
        tags.append(tag)
    return tags


@registry.register
class SupplierImporter(EntityImporter):
    entity_key = "supplier"
    model = Supplier
    app_label = "assets"
    permission_feature = "supplier"
    verbose_name = _lazy("supplier")
    verbose_name_plural = _lazy("suppliers")
    list_url_name = "assets:supplier-list"
    detail_url_name = "assets:supplier-detail"
    # Rows whose exact supplier name already exists are flagged as conflicts;
    # the preview lets the user replace the existing supplier or keep it.
    conflict_field = "name"

    columns = [
        ColumnSpec(
            name="name", required=True, kind="str",
            help="Supplier name.", example="Acme Cloud Services",
        ),
        ColumnSpec(
            name="owner", field="owner", kind="fk", resolver=_resolve_owner,
            help="Owner email. Leave blank to assign yourself.",
            example="jane.doe@example.com",
        ),
        ColumnSpec(
            name="type", field="type", kind="fk", resolver=_resolve_type,
            help="Supplier type name (must already exist).", example="Cloud provider",
        ),
        ColumnSpec(
            name="criticality", kind="choice",
            choices=tuple(c.value for c in SupplierCriticality),
            help="Criticality level.", example="high",
        ),
        ColumnSpec(
            name="status", kind="choice",
            choices=tuple(c.value for c in SupplierStatus),
            help="Lifecycle status.", example="active",
        ),
        ColumnSpec(
            name="description", kind="text",
            help="Short description of what the supplier provides.",
            example="Managed cloud hosting",
        ),
        ColumnSpec(
            name="contact_name", kind="str",
            help="Primary contact person.", example="Jane Doe",
        ),
        ColumnSpec(
            name="contact_email", kind="email",
            help="Primary contact email.", example="contact@acme.example",
        ),
        ColumnSpec(
            name="contact_phone", kind="str",
            help="Primary contact phone.", example="+33 1 23 45 67 89",
        ),
        ColumnSpec(
            name="website", kind="url",
            help="Supplier website URL.", example="https://acme.example",
        ),
        ColumnSpec(
            name="address", kind="text",
            help="Postal address.", example="1 Rue de Paris, 75001 Paris",
        ),
        ColumnSpec(
            name="country", kind="str",
            help="Country of operation.", example="France",
        ),
        ColumnSpec(
            name="contract_reference", kind="str",
            help="Governing contract reference.", example="CT-2026-001",
        ),
        ColumnSpec(
            name="contract_start_date", kind="date",
            help="Contract start date (YYYY-MM-DD).", example="2026-01-01",
        ),
        ColumnSpec(
            name="contract_end_date", kind="date",
            help="Contract end date (YYYY-MM-DD).", example="2026-12-31",
        ),
        ColumnSpec(
            name="notes", kind="text",
            help="Free-form notes.", example="Renewal under negotiation",
        ),
        ColumnSpec(
            name="scopes", field="scopes", kind="m2m", resolver=_resolve_scopes,
            help="Scope references or names, separated by ';' (must exist).",
            example="SCOP-1;SCOP-2",
        ),
        ColumnSpec(
            name="tags", field="tags", kind="m2m", resolver=_resolve_tags,
            help="Tag names, separated by ';' (created if missing).",
            example="PII;EU",
        ),
        ColumnSpec(
            name="created_at", field="created_at", kind="datetime", post_save=True,
            help="Original creation date from the previous tool "
                 "(YYYY-MM-DD or YYYY-MM-DD HH:MM). Defaults to now.",
            example="2023-05-12",
        ),
    ]
