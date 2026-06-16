"""Core building blocks for the generic CSV bulk-import framework.

The framework is declarative: an entity provides an :class:`EntityImporter`
subclass with a list of :class:`ColumnSpec`. The base class then knows how to
parse the CSV, validate every row, generate a sample file and documentation, and
create the objects within a single transaction.

Column-level documentation (``help``/``example`` and the allowed-values column in
:meth:`EntityImporter.column_docs`) is intentionally English-only, mirroring the
framework import samples: the structural reference must stay stable across locales.
User-facing labels, buttons and error messages remain translated.
"""

import csv
import io
from dataclasses import dataclass, field as dc_field
from datetime import datetime
from typing import Callable, Optional

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator, validate_email
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext as _

# Shared upper bound for uploaded import files (10 MB), matching the framework
# import limit in compliance/forms.py.
MAX_IMPORT_FILE_SIZE = 10 * 1024 * 1024

# Sentinel meaning "this column had no value and no default": the field is left
# unset so the model default applies.
_UNSET = object()


class ImportValueError(ValueError):
    """Raised by coercion / resolvers to flag a recoverable, per-row error.

    The message is shown to the user next to the offending row; it never bubbles
    up as a 500.
    """


@dataclass
class ImportContext:
    """Per-row context handed to resolvers."""

    user: object
    warnings: list
    row_number: int


@dataclass
class ColumnSpec:
    """Declarative description of one CSV column.

    ``kind`` drives the built-in coercion: ``str``/``text`` (raw string),
    ``int``, ``date`` (``YYYY-MM-DD``), ``choice`` (validated against
    ``choices``), ``email``, ``url``, ``fk`` and ``m2m``. For ``fk``/``m2m`` a
    ``resolver(raw_value, ctx)`` callable must return the resolved object (or
    list of objects for ``m2m``) and may raise :class:`ImportValueError`.
    """

    name: str
    field: str = ""
    required: bool = False
    kind: str = "str"
    choices: tuple = ()
    default: object = None
    resolver: Optional[Callable] = None
    help: str = ""
    example: str = ""
    # When True the value is written via a post-creation DB update instead of
    # the constructor. Use for ``auto_now_add`` fields such as ``created_at``
    # whose value would otherwise be overwritten on save (e.g. importing the
    # original creation date from a legacy tool).
    post_save: bool = False

    def __post_init__(self):
        if not self.field:
            self.field = self.name


@dataclass
class ValidationResult:
    """Outcome of validating a parsed CSV file."""

    valid: list = dc_field(default_factory=list)
    errors: list = dc_field(default_factory=list)
    warnings: list = dc_field(default_factory=list)
    fatal: list = dc_field(default_factory=list)


@dataclass
class ImportOutcome:
    """Result of executing an import: objects created, updated and skipped."""

    created: list = dc_field(default_factory=list)
    updated: list = dc_field(default_factory=list)
    skipped: list = dc_field(default_factory=list)


class EntityImporter:
    """Base class for a per-entity CSV importer.

    Subclasses set the class attributes below and provide ``columns``. The
    generic views drive ``parse_csv`` -> ``validate`` -> ``execute``.
    """

    entity_key: str = ""
    model = None
    app_label: str = ""
    permission_feature: str = ""
    verbose_name: str = ""
    verbose_name_plural: str = ""
    list_url_name: str = ""
    detail_url_name: str = ""
    columns: list = []
    delimiter: str = ","
    multi_delimiter: str = ";"
    # When set, rows whose value for this field matches an existing object
    # (case-insensitive) are flagged as conflicts in the preview, where the
    # user chooses per row to replace the existing object or keep it. A field
    # matching several existing objects is reported as an ambiguous error.
    conflict_field: str = None

    # ── Parsing ───────────────────────────────────────────────

    def parse_csv(self, file_obj):
        """Return a list of ``{column: stripped_value}`` dicts from a CSV file.

        Handles a UTF-8 BOM and strips header/value whitespace.
        """
        raw = file_obj.read()
        if isinstance(raw, bytes):
            text = raw.decode("utf-8-sig")
        else:
            text = raw
        reader = csv.DictReader(io.StringIO(text), delimiter=self.delimiter)
        if reader.fieldnames is None:
            return []
        header_map = {(h or "").strip(): h for h in reader.fieldnames}
        rows = []
        for raw_row in reader:
            row = {}
            for clean, original in header_map.items():
                if not clean:
                    continue
                value = raw_row.get(original, "")
                row[clean] = (value or "").strip()
            rows.append(row)
        return rows

    # ── Validation ────────────────────────────────────────────

    def validate(self, rows, user):
        """Validate parsed rows, resolving FKs/M2Ms and coercing types.

        Returns a :class:`ValidationResult`. ``fatal`` holds whole-file problems
        (empty file, missing required columns); ``errors`` holds per-row problems
        with their messages; ``valid`` holds rows ready to be created.
        """
        result = ValidationResult()

        if not rows:
            result.fatal.append(_("The file contains no data rows."))
            return result

        present = set(rows[0].keys())
        missing = [c.name for c in self.columns if c.required and c.name not in present]
        if missing:
            result.fatal.append(
                _("Missing required column(s): %(cols)s.") % {"cols": ", ".join(missing)}
            )
            return result

        for index, raw in enumerate(rows, start=2):  # row 1 is the header
            if not any(v for v in raw.values()):
                continue  # skip blank lines

            ctx = ImportContext(user=user, warnings=[], row_number=index)
            row_errors = []
            fields = {}
            m2m = {}
            post = {}

            for spec in self.columns:
                value = raw.get(spec.name, "")
                try:
                    resolved = self._coerce(spec, value, ctx)
                except ImportValueError as exc:
                    row_errors.append(str(exc))
                    continue
                if resolved is _UNSET:
                    continue
                if spec.kind == "m2m":
                    m2m[spec.field] = resolved
                elif spec.post_save:
                    post[spec.field] = resolved
                else:
                    fields[spec.field] = resolved

            conflict = None
            if self.conflict_field and not row_errors and self.conflict_field in fields:
                conflict, conflict_error = self._detect_conflict(fields[self.conflict_field])
                if conflict_error:
                    row_errors.append(conflict_error)

            result.warnings.extend(ctx.warnings)
            if row_errors:
                result.errors.append(
                    {"row_number": index, "raw": raw, "messages": row_errors}
                )
            else:
                result.valid.append(
                    {
                        "row_number": index,
                        "raw": raw,
                        "fields": fields,
                        "m2m": m2m,
                        "post": post,
                        "conflict": conflict,
                    }
                )

        # De-duplicate warnings while preserving order.
        seen = set()
        result.warnings = [w for w in result.warnings if not (w in seen or seen.add(w))]
        return result

    def _detect_conflict(self, value):
        """Return ``(conflict, error)`` for an existing object matching ``value``.

        ``conflict`` is ``{"pk", "label"}`` when exactly one object matches,
        ``None`` when none match, and ``error`` is set when several match.
        """
        qs = self.model.objects.filter(**{f"{self.conflict_field}__iexact": value})
        existing = list(qs[:2])
        if len(existing) > 1:
            return None, (
                _('Several existing records already match "%(val)s" on '
                  '%(field)s; disambiguate before importing.')
                % {"val": value, "field": self.conflict_field}
            )
        if existing:
            return {"pk": str(existing[0].pk), "label": str(existing[0])}, None
        return None, None

    def _coerce(self, spec, value, ctx):
        """Coerce / resolve a single cell. Raises ImportValueError on failure."""
        value = (value or "").strip()

        # FK / M2M resolution is delegated to the spec resolver, which decides
        # how to handle a blank value (e.g. owner -> current user, tags -> []).
        if spec.kind in ("fk", "m2m"):
            if spec.resolver is None:
                raise ImportValueError(
                    _('Column "%(col)s" has no resolver.') % {"col": spec.name}
                )
            return spec.resolver(value, ctx)

        if not value:
            if spec.required:
                raise ImportValueError(
                    _('Column "%(col)s" is required.') % {"col": spec.name}
                )
            if spec.default is not None:
                return spec.default
            return _UNSET

        if spec.kind in ("str", "text"):
            return value

        if spec.kind == "int":
            try:
                return int(value)
            except (TypeError, ValueError):
                raise ImportValueError(
                    _('Column "%(col)s" must be a whole number (got "%(val)s").')
                    % {"col": spec.name, "val": value}
                )

        if spec.kind == "date":
            try:
                return datetime.strptime(value, "%Y-%m-%d").date()
            except ValueError:
                raise ImportValueError(
                    _('Column "%(col)s" must be a date in YYYY-MM-DD format (got "%(val)s").')
                    % {"col": spec.name, "val": value}
                )

        if spec.kind == "datetime":
            parsed = None
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
                try:
                    parsed = datetime.strptime(value, fmt)
                    break
                except ValueError:
                    continue
            if parsed is None:
                raise ImportValueError(
                    _('Column "%(col)s" must be a date or date-time in YYYY-MM-DD[ HH:MM] format (got "%(val)s").')
                    % {"col": spec.name, "val": value}
                )
            if settings.USE_TZ and timezone.is_naive(parsed):
                parsed = timezone.make_aware(parsed)
            return parsed

        if spec.kind == "choice":
            allowed = {c.lower(): c for c in spec.choices}
            if value.lower() not in allowed:
                raise ImportValueError(
                    _('Invalid value "%(val)s" for "%(col)s". Allowed: %(allowed)s.')
                    % {"val": value, "col": spec.name, "allowed": ", ".join(spec.choices)}
                )
            return allowed[value.lower()]

        if spec.kind == "email":
            try:
                validate_email(value)
            except ValidationError:
                raise ImportValueError(
                    _('Column "%(col)s" must be a valid email address (got "%(val)s").')
                    % {"col": spec.name, "val": value}
                )
            return value

        if spec.kind == "url":
            try:
                URLValidator()(value)
            except ValidationError:
                raise ImportValueError(
                    _('Column "%(col)s" must be a valid URL (got "%(val)s").')
                    % {"col": spec.name, "val": value}
                )
            return value

        return value

    # ── Execution ─────────────────────────────────────────────

    @transaction.atomic
    def execute(self, valid_rows, user):
        """Apply every valid row inside a single transaction.

        A row with no conflict is created. A row whose ``conflict`` is set is
        updated in place when ``replace`` is truthy, otherwise it is skipped
        (the existing object is kept untouched). Returns an
        :class:`ImportOutcome` with the created / updated / skipped objects.
        """
        outcome = ImportOutcome()
        has_created_by = any(
            getattr(f, "name", None) == "created_by"
            for f in self.model._meta.get_fields()
        )
        exclude = [c.field for c in self.columns if c.kind == "m2m"] + ["reference"]

        for vr in valid_rows:
            conflict = vr.get("conflict")
            if conflict:
                if not vr.get("replace"):
                    outcome.skipped.append(conflict)
                    continue
                outcome.updated.append(self._apply_update(vr, conflict, exclude))
            else:
                outcome.created.append(self._apply_create(vr, user, has_created_by, exclude))
        return outcome

    def _full_clean(self, obj, vr, exclude):
        try:
            obj.full_clean(exclude=exclude)
        except ValidationError as exc:
            raise ImportValueError(
                _("Row %(row)s: %(err)s")
                % {"row": vr["row_number"], "err": "; ".join(_flatten_errors(exc))}
            )

    def _set_m2m(self, obj, vr):
        for field_name, objects in vr.get("m2m", {}).items():
            getattr(obj, field_name).set(objects)

    def _apply_create(self, vr, user, has_created_by, exclude):
        obj = self.model(**vr["fields"])
        if has_created_by:
            obj.created_by = user
        self._full_clean(obj, vr, exclude)
        obj.save()
        self._set_m2m(obj, vr)
        # Apply post-save overrides (e.g. a legacy created_at) via a direct DB
        # update so auto_now_add does not clobber the imported value.
        post = vr.get("post", {})
        if post:
            self.model.objects.filter(pk=obj.pk).update(**post)
            for field_name, value in post.items():
                setattr(obj, field_name, value)
        return obj

    def _apply_update(self, vr, conflict, exclude):
        obj = self.model.objects.get(pk=conflict["pk"])
        for field_name, value in vr["fields"].items():
            setattr(obj, field_name, value)
        self._full_clean(obj, vr, exclude)
        obj.save()
        self._set_m2m(obj, vr)
        # Deliberately ignore the post-save bucket on update: the original
        # creation date (created_at) of the existing record must be preserved.
        return obj

    # ── Sample & documentation ────────────────────────────────

    def generate_sample_csv(self):
        """Return a ``BytesIO`` with a header row and one example data row."""
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow([c.name for c in self.columns])
        writer.writerow([c.example for c in self.columns])
        return io.BytesIO(buf.getvalue().encode("utf-8-sig"))

    def column_docs(self):
        """Return per-column documentation rows (English-only) for the UI/sample."""
        docs = []
        for c in self.columns:
            allowed = ", ".join(c.choices) if c.kind == "choice" else ""
            docs.append(
                {
                    "name": c.name,
                    "required": c.required,
                    "kind": c.kind,
                    "allowed": allowed,
                    "help": c.help,
                }
            )
        return docs


def _flatten_errors(exc):
    """Flatten a Django ValidationError into a list of readable strings."""
    messages = []
    if hasattr(exc, "message_dict"):
        for field, errs in exc.message_dict.items():
            messages.append(f"{field}: {', '.join(errs)}")
    else:
        messages.extend(exc.messages)
    return messages
