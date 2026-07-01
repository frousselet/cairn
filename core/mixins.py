import json
import math

from django.contrib.auth import get_user_model
from django.db import models as dj_models
from django.db.models import Count, F, Q
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.utils.dateparse import parse_date
from django.utils.translation import pgettext_lazy

from core.db import NaturalSortKey
from core.query_params import INT_MAX, INT_MIN, parse_int, parse_uuid


class HtmxFormMixin:
    """Mixin for CreateView/UpdateView to serve modal forms via HTMX.

    When the request is an HTMX request, the view renders a modal-friendly
    partial template instead of the full-page template. On successful save,
    it returns an HX-Trigger header to refresh the table body.

    Class attributes:
        modal_template_name: Template for the modal form partial.
        modal_title_create: Title for the create modal.
        modal_title_update: Title for the update modal.
    """

    modal_template_name = None
    modal_title_create = ""
    modal_title_update = ""

    def _is_htmx(self):
        # The drawer flow uses hx-target="#drawer-form-content"; HTMX puts
        # the target id into the HX-Target header. The body carries
        # `hx-boost="true"` for soft-nav, which also sends HX-Request=true
        # but with HX-Boosted=true and HX-Target=page-shell. Distinguishing
        # the two prevents the modal partial (designed to be swapped into
        # the drawer container) from being mistakenly returned for a
        # boosted full-page navigation, which would otherwise render the
        # bare drawer markup full-bleed without the page chrome.
        if self.request.headers.get("HX-Request") != "true":
            return False
        if self.request.headers.get("HX-Boosted") == "true":
            return False
        return self.request.headers.get("HX-Target") == "drawer-form-content"

    def get_template_names(self):
        if self._is_htmx() and self.modal_template_name:
            return [self.modal_template_name]
        return super().get_template_names()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if self._is_htmx():
            is_edit = getattr(self, "object", None) and self.object.pk
            ctx["modal_title"] = self.modal_title_update if is_edit else self.modal_title_create
            ctx["is_modal"] = True
        return ctx

    def form_valid(self, form):
        response = super().form_valid(form)
        if self._is_htmx():
            return HttpResponse(
                status=204,
                headers={"HX-Trigger": "formSaved"},
            )
        return response

    def form_invalid(self, form):
        if self._is_htmx():
            self.object = getattr(self, "object", None)
            return self.render_to_response(self.get_context_data(form=form))
        return super().form_invalid(form)


class SortableListMixin:
    """Mixin for ListView that adds server-side sorting.

    Sort preferences are persisted per user via JS (no URL params).
    Search/filtering is handled client-side via JS.

    Class attributes:
        sortable_fields: dict mapping field names to ORM field paths.
            Example: {"name": "name", "owner": "owner__last_name"}
        default_sort: default sort field (must be a key in sortable_fields).
        default_sort_order: "asc" or "desc".
        sort_view_key: unique key to persist sort preferences per user.
            Defaults to "app_label.model_name" from the view's model.
        natural_sort_fields: set of ORM field suffixes that should use
            natural sorting (pads numbers for correct ordering).
            Defaults to {"reference", "requirement_number"}.
    """

    sortable_fields = {}
    default_sort = None
    default_sort_order = "asc"
    sort_view_key = ""
    natural_sort_fields = {"reference", "requirement_number"}

    def _get_sort_view_key(self):
        if self.sort_view_key:
            return self.sort_view_key
        model = getattr(self, "model", None)
        if model:
            return f"{model._meta.app_label}.{model._meta.model_name}"
        return ""

    def _get_saved_preference(self):
        """Return (sort_field, order) from user's saved preferences, or (None, None)."""
        user = getattr(self.request, "user", None)
        if not user or not user.is_authenticated:
            return None, None
        prefs = getattr(user, "table_preferences", None)
        if not isinstance(prefs, dict):
            return None, None
        view_key = self._get_sort_view_key()
        pref = prefs.get(view_key)
        if isinstance(pref, dict):
            sort_field = pref.get("sort", "")
            order = pref.get("order", "asc")
            if sort_field and sort_field in self.sortable_fields:
                return sort_field, order
        return None, None

    def _resolve_sort(self):
        """Determine the effective sort field and order.

        Priority: saved user preference > class defaults.
        """
        saved_sort, saved_order = self._get_saved_preference()
        if saved_sort:
            return saved_sort, saved_order
        return self.default_sort, self.default_sort_order

    def _needs_natural_sort(self, orm_field):
        """Check if the ORM field path needs natural sorting."""
        field_name = orm_field.rsplit("__", 1)[-1]
        return field_name in self.natural_sort_fields

    def get_queryset(self):
        qs = super().get_queryset()
        qs = self._apply_sorting(qs)
        return qs

    def _apply_sorting(self, qs):
        sort_field, order = self._resolve_sort()
        if sort_field and sort_field in self.sortable_fields:
            orm_field = self.sortable_fields[sort_field]
            if self._needs_natural_sort(orm_field):
                ann_name = f"_nsort_{sort_field}"
                qs = qs.annotate(**{ann_name: NaturalSortKey(F(orm_field))})
                order_field = f"-{ann_name}" if order == "desc" else ann_name
            else:
                order_field = f"-{orm_field}" if order == "desc" else orm_field
            qs = qs.order_by(order_field)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        sort_field, order = self._resolve_sort()
        ctx["current_sort"] = sort_field or ""
        ctx["current_order"] = order or "asc"
        ctx["sort_view_key"] = self._get_sort_view_key()
        # Elided page window (1 … 4 5 6 … 20) for the paginator UI.
        page_obj = ctx.get("page_obj")
        if page_obj is not None and page_obj.paginator.num_pages > 1:
            ctx["page_range"] = page_obj.paginator.get_elided_page_range(
                page_obj.number, on_each_side=1, on_ends=1
            )
        return ctx


class TableBodyPaginatedMixin:
    """For HTMX table-body views: paginate the rows like the full list page and
    return the rows partial PLUS an out-of-band pagination block, so the pager
    (page count, numbers, prev/next) stays in sync with the active filters and
    search on every refresh. The view keeps its rows partial as ``template_name``;
    set ``paginate_by`` to match the list page (defaults to 50)."""

    paginate_by = 50

    def render_to_response(self, context, **response_kwargs):
        rows = render_to_string(self.template_name, context, request=self.request)
        pager = render_to_string(
            "includes/pagination.html", {**context, "oob": True}, request=self.request
        )
        return HttpResponse(rows + pager)


class ListSummaryMixin:
    """Feed the list page's sticky side rail with a per-state summary.

    Builds a ``list_summary`` context entry (total + per-state counts) for the
    summary card in the rail. The counts are taken from the scope-filtered
    queryset *before* the page's ``?status=`` / type / impact facets, so the rail
    always reflects the whole list the user may see and each count links to its
    ``?status=`` filter.

    To capture the queryset after scope filtering but before the per-view facets,
    place this mixin to the LEFT of :class:`~accounts.mixins.ScopeFilterMixin` in
    the MRO: its ``get_queryset`` then runs outermost, snapshotting the scoped,
    sorted queryset that the view's own ``get_queryset`` later narrows.

    Subclasses set ``status_field`` to the model field whose values are counted
    (``workflow_state`` by default; some models count a domain ``status`` field),
    and ``status_param`` to the query-string key the view reads to filter that
    facet (``status`` by default, e.g. ``compliance_status`` for requirements).
    The two differ when the public facet name is not the field name (a Scope's
    ``?status=`` maps to its ``workflow_state``). A list whose model has no such
    field still gets a total-only summary, so the rail stays consistent across
    every list page.
    """

    status_field = "workflow_state"
    status_param = "status"

    # Tile tone -> (CSS tone class, Bootstrap icon) for the rail KPI tiles.
    _TONE_STYLE = {
        "success": ("success", "check-circle"),
        "warning": ("warning", "hourglass-split"),
        "danger": ("danger", "x-circle"),
        "info": ("accent", "info-circle"),
        "neutral": ("neutral", "circle"),
        "accent": ("accent", "record-circle"),
    }
    # Cycling palette for states with no semantic tone, so a tile is NEVER left
    # flat grey: every state gets a distinct colour + icon.
    _TONE_PALETTE = [
        ("accent", "record-circle"),
        ("warning", "hourglass-split"),
        ("success", "flag"),
        ("danger", "slash-circle"),
        ("accent", "bookmark"),
        ("warning", "clock-history"),
    ]

    def get_queryset(self):
        qs = super().get_queryset()
        # Snapshot the scope/sort-filtered queryset before the view's own status /
        # type facets, so the summary counts reflect the whole visible list.
        self._summary_base_qs = qs
        return qs

    def _lifecycle_states(self, model):
        """Ordered :class:`~core.lifecycle.Step` objects for the model's lifecycle.

        The model's own lifecycle (``LIFECYCLE_NAME``) or the default one; its
        steps (each exposing ``code`` / ``label`` / ``tone``) drive the rail.
        Returns an empty tuple when no lifecycle resolves.
        """
        from core.lifecycle import resolve_lifecycle

        try:
            return resolve_lifecycle(model).steps
        except Exception:
            return ()

    def _state_styles(self, model):
        """Map each status value to (tone, icon) from the model's lifecycle
        tones. Empty for choice-based status fields (those fall back to the
        keyword heuristic)."""
        try:
            field = model._meta.get_field(self.status_field)
        except Exception:
            field = None
        if field is not None and getattr(field, "choices", None):
            return {}
        return {
            state.code: self._TONE_STYLE.get(getattr(state, "tone", "neutral"), self._TONE_STYLE["neutral"])
            for state in self._lifecycle_states(model)
        }

    def _heuristic_style(self, value):
        """Best-effort tone for a status code, so lists without workflow tones
        still read semantically. Returns None when nothing matches (the caller
        then assigns a palette colour, so no tile is ever left flat grey). Order
        matters (danger before success so "non_compliant" isn't read as
        "compliant")."""
        v = str(value).lower()
        if any(k in v for k in ("major", "critical", "non_compliant", "noncompliant", "fail", "reject", "overdue", "blocked", "danger", "expired", "late", "_ko", "cancel")):
            return self._TONE_STYLE["danger"]
        if any(k in v for k in ("minor", "partial", "pending", "progress", "ongoing", "cours", "monitored", "review", "medium", "warning", "draft", "wip")):
            return self._TONE_STYLE["warning"]
        if any(k in v for k in ("compliant", "valid", "active", "done", "complet", "finish", "termin", "resolved", "approved", "success", "closed", "passed", "achiev", "realis")):
            return self._TONE_STYLE["success"]
        if any(k in v for k in ("plan", "scheduled", "prevu", "todo", "backlog", "new", "open", "identif", "draft_new")):
            return self._TONE_STYLE["accent"]
        return None

    def _summary_label_pairs(self, model):
        """Ordered ``(value, label)`` pairs for the status field.

        A field with ``choices`` drives both the labels and their order; the
        bare ``workflow_state`` field has no choices, so its labels and order
        come from the model's registered lifecycle workflow.
        """
        try:
            field = model._meta.get_field(self.status_field)
        except Exception:
            field = None
        if field is not None and getattr(field, "choices", None):
            return [(value, label) for value, label in field.choices]
        return [(state.code, state.label) for state in self._lifecycle_states(model)]

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        base = getattr(self, "_summary_base_qs", None)
        if base is not None:
            model = base.model
            current = self.request.GET.get(self.status_param)
            try:
                # Clear any sort before grouping: an ORDER BY column would
                # otherwise leak into the GROUP BY and split the per-state counts.
                counts = dict(
                    base.order_by()
                    .values_list(self.status_field)
                    .annotate(_c=Count("pk"))
                )
                styles = self._state_styles(model)
                palette_i = 0
                items = []
                for value, label in self._summary_label_pairs(model):
                    count = counts.get(value, 0)
                    if not count:
                        continue
                    style = styles.get(value) or self._heuristic_style(value)
                    # No semantic tone (or a plain neutral one): take the next
                    # palette colour so the tile is never left flat grey.
                    if style is None or style[0] == "neutral":
                        style = self._TONE_PALETTE[palette_i % len(self._TONE_PALETTE)]
                        palette_i += 1
                    items.append(
                        {
                            "value": value,
                            "label": label,
                            "count": count,
                            "active": str(current) == str(value),
                            "tone": style[0],
                            "icon": style[1],
                        }
                    )
                total = sum(counts.values())
            except Exception:
                # Model without the status field (e.g. users, logs): total only.
                items = []
                total = base.count()
            ctx["list_summary"] = {
                "total": total,
                "items": items,
                "param": self.status_param,
            }
        return ctx


class PredefinedFilterMixin:
    """Combinable rail filters for a list page: predefined facets + text rules.

    ``filter_groups`` declares multi-select facets. Each entry is a dict
    ``{"param", "field", "label", "options"}`` where ``options`` is an iterable
    of ``(value, label)`` pairs (e.g. a ``TextChoices.choices``). A facet is
    multi-valued: every selected option in a group is OR-combined
    (``field__in=[...]``) and groups are AND-combined, so the user can stack them
    freely. Values are read with ``getlist`` so the same widget serves the
    full-page view and its HTMX table-body view.

    ``text_filters`` declares free-text rules with an operator. Each entry is a
    dict ``{"param", "field", "label"}`` read from two query keys: ``<param>_op``
    (one of :attr:`TEXT_OPERATORS`) and ``<param>_q`` (the value). Operators map
    to ORM lookups: is / contains / starts-with, plus a negated is-not.

    The view calls :meth:`filter_queryset_predefined` inside ``get_queryset``;
    ``get_context_data`` exposes ``list_filters`` and ``list_text_filters`` for
    ``includes/list_rail_filters.html``.
    """

    filter_groups = []
    text_filters = []
    # Hard cap on the toolbar search length, mirroring the global search: an
    # unbounded ?q= builds an equally long LIKE pattern, which raises
    # OperationalError on SQLite and is an unbounded-work DoS vector elsewhere.
    max_search_length = 128

    # value -> (label, ORM lookup, negate). Order drives the operator dropdown.
    TEXT_OPERATORS = [
        ("contains", pgettext_lazy("filter operator", "contains"), "icontains", False),
        ("is", pgettext_lazy("filter operator", "is"), "iexact", False),
        ("starts", pgettext_lazy("filter operator", "starts with"), "istartswith", False),
        ("isnot", pgettext_lazy("filter operator", "is not"), "iexact", True),
    ]

    def _text_operator(self, code):
        for value, _label, lookup, negate in self.TEXT_OPERATORS:
            if value == code:
                return lookup, negate
        return None

    def filter_queryset_predefined(self, qs):
        # Server-side text search (the toolbar search box, ?q=), OR-combined
        # across the view's search_fields, so it narrows the real queryset and
        # the pagination reflects it. A query wrapped in double quotes ("A.5.1")
        # means an exact (case-insensitive) match; otherwise it is a substring.
        search = self.request.GET.get("q", "").strip()[: self.max_search_length]
        search_fields = getattr(self, "search_fields", None)
        if search and search_fields:
            if len(search) >= 2 and search[0] == '"' and search[-1] == '"':
                term, lookup = search[1:-1].strip(), "iexact"
            else:
                term, lookup = search, "icontains"
            if term:
                cond = Q()
                for field in search_fields:
                    cond |= Q(**{f"{field}__{lookup}": term})
                qs = qs.filter(cond)
        for group in self.filter_groups:
            values = self.request.GET.getlist(group["param"])
            if values:
                qs = qs.filter(**{f"{group['field']}__in": values})
        for rule in self.text_filters:
            value = self.request.GET.get(f"{rule['param']}_q", "").strip()
            if not value:
                continue
            op = self._text_operator(self.request.GET.get(f"{rule['param']}_op", "contains"))
            if not op:
                continue
            lookup, negate = op
            cond = {f"{rule['field']}__{lookup}": value}
            qs = qs.exclude(**cond) if negate else qs.filter(**cond)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        groups = []
        active_count = 0
        for group in self.filter_groups:
            selected = set(self.request.GET.getlist(group["param"]))
            if selected:
                active_count += 1
            groups.append(
                {
                    "label": group["label"],
                    "param": group["param"],
                    "options": [
                        {"value": v, "label": label, "checked": v in selected}
                        for v, label in group["options"]
                    ],
                }
            )
        text_rules = []
        for rule in self.text_filters:
            current_op = self.request.GET.get(f"{rule['param']}_op", "contains")
            value = self.request.GET.get(f"{rule['param']}_q", "")
            if value.strip():
                active_count += 1
            text_rules.append(
                {
                    "label": rule["label"],
                    "param": rule["param"],
                    "value": value,
                    "operators": [
                        {"value": v, "label": label, "selected": v == current_op}
                        for v, label, _lookup, _negate in self.TEXT_OPERATORS
                    ],
                }
            )
        ctx["list_filters"] = groups
        ctx["list_text_filters"] = text_rules
        ctx["list_filters_count"] = active_count
        ctx["list_filters_active"] = active_count > 0
        return ctx


class ColumnPreferenceMixin:
    """Per-user column visibility and order for a list page's table.

    Declare the table's columns on the view as ``columns``: a list of dicts
    ``{"key", "label", "always"}`` in their natural order. ``always`` marks a
    column that can never be hidden (e.g. the reference or name). The user's
    saved layout (``User.column_preferences[view_key] = {order, hidden}``) is
    merged over that default, and ``get_context_data`` exposes ``list_columns``
    (ordered, each with ``visible`` / ``always``) plus ``column_view_key`` for
    the Columns menu and the client-side apply/persist script. New columns
    shipped later append at the end and default to visible.
    """

    columns = []

    def get_column_view_key(self):
        model = getattr(self, "model", None)
        if model is not None:
            return f"{model._meta.app_label}.{model._meta.model_name}"
        return ""

    def _column_preference(self):
        user = getattr(self.request, "user", None)
        prefs = getattr(user, "column_preferences", None) if user else None
        if not isinstance(prefs, dict):
            return {}
        pref = prefs.get(self.get_column_view_key())
        return pref if isinstance(pref, dict) else {}

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if self.columns:
            by_key = {c["key"]: c for c in self.columns}
            pref = self._column_preference()
            saved_order = [k for k in pref.get("order", []) if k in by_key]
            # Saved order first, then any columns added since (kept visible).
            ordered = saved_order + [c["key"] for c in self.columns if c["key"] not in saved_order]
            hidden = set(pref.get("hidden", []))
            ctx["list_columns"] = [
                {
                    "key": key,
                    "label": by_key[key]["label"],
                    "always": by_key[key].get("always", False),
                    "visible": by_key[key].get("always", False) or key not in hidden,
                }
                for key in ordered
            ]
            ctx["column_view_key"] = self.get_column_view_key()
        return ctx


def _op(label):
    return pgettext_lazy("filter operator", label)


class AdvancedFilterMixin:
    """Generic "filter on any field" builder for a list page.

    Introspects the model's own fields plus declared relations into a registry of
    filterable fields, each classified by type with the operators it supports:

    - text (char / text): contains / is / starts with / is not
    - number, date: = / > / >= / < / <=
    - choice (a field with ``choices``): is / is not
    - boolean: is
    - person (FK/M2M to the user model), relation (other FK/M2M): is any of /
      is none of (multi-value)

    Rules are sent as repeated ``rule`` query params, each a JSON object
    ``{"f": field_key, "o": operator, "v": value}`` (``v`` is a list for
    person/relation). :meth:`filter_queryset_advanced` validates every rule
    against the registry (only known fields, operators and lookups are ever
    applied) and ANDs them onto the queryset. ``get_context_data`` exposes
    ``filter_fields_json`` (the registry) and ``filter_rules_json`` (the active
    rules) for the offcanvas rule-builder script.
    """

    advanced_filters = True
    filter_exclude = frozenset(
        {
            "id", "password", "version",
            "created_by", "created_at", "updated_at", "last_login", "tags",
        }
    )
    filter_extra_fields = []  # extra relation field names (ORM paths) to include
    filter_max_options = 200

    OPERATORS = {
        "text": [("contains", _op("contains")), ("is", _op("is")), ("starts", _op("starts with")), ("isnot", _op("is not"))],
        "number": [("eq", "="), ("gt", ">"), ("gte", "≥"), ("lt", "<"), ("lte", "≤")],
        "date": [("eq", "="), ("gt", ">"), ("gte", "≥"), ("lt", "<"), ("lte", "≤")],
        "choice": [("is", _op("is")), ("isnot", _op("is not"))],
        "boolean": [("is", _op("is"))],
        "person": [("in", _op("is any of")), ("notin", _op("is none of"))],
        "relation": [("in", _op("is any of")), ("notin", _op("is none of"))],
    }
    _TEXT_LOOKUPS = {"contains": ("icontains", False), "is": ("iexact", False), "starts": ("istartswith", False), "isnot": ("iexact", True)}
    _SCALAR_LOOKUPS = {"eq": "exact", "gt": "gt", "gte": "gte", "lt": "lt", "lte": "lte"}

    def _classify_field(self, field):
        if getattr(field, "choices", None):
            return "choice"
        if isinstance(field, (dj_models.ForeignKey, dj_models.ManyToManyField)):
            return "person" if field.related_model is get_user_model() else "relation"
        if isinstance(field, dj_models.BooleanField):
            return "boolean"
        if isinstance(field, (dj_models.DateField, dj_models.DateTimeField)):
            return "date"
        if isinstance(field, (dj_models.IntegerField, dj_models.FloatField, dj_models.DecimalField)):
            return "number"
        if isinstance(field, (dj_models.CharField, dj_models.TextField)):
            return "text"
        return None

    def _iter_model_fields(self):
        for field in self.model._meta.get_fields():
            if field.name in self.filter_exclude:
                continue
            if field.many_to_many and not field.auto_created:
                yield field
            elif getattr(field, "concrete", False) and not field.auto_created:
                yield field

    def get_filter_fields(self):
        """Return the registry: ordered list of field definitions (plain dicts)."""
        fields = []
        for field in self._iter_model_fields():
            ftype = self._classify_field(field)
            if not ftype:
                continue
            definition = {
                "key": field.name,
                "orm": field.name,
                "label": str(getattr(field, "verbose_name", field.name)).capitalize(),
                "type": ftype,
                "datetime": isinstance(field, dj_models.DateTimeField),
                "operators": [{"value": v, "label": str(label)} for v, label in self.OPERATORS[ftype]],
            }
            if ftype == "choice":
                definition["options"] = [{"value": str(v), "label": str(label)} for v, label in field.choices]
            elif ftype in ("person", "relation"):
                rel = field.related_model
                definition["options"] = [
                    {"value": str(o.pk), "label": str(o)}
                    for o in rel._default_manager.all()[: self.filter_max_options]
                ]
                # Remember the related PK type so a rule's values can be
                # validated against it (a UUID PK rejects a non-UUID value, an
                # integer PK rejects an out-of-range one) before they reach the
                # ORM, instead of crashing the list with a 500.
                pk_field = rel._meta.pk
                if isinstance(pk_field, dj_models.UUIDField):
                    definition["pk_kind"] = "uuid"
                elif isinstance(pk_field, dj_models.IntegerField):
                    definition["pk_kind"] = "int"
                else:
                    definition["pk_kind"] = "other"
            fields.append(definition)
        return fields

    def _build_condition(self, definition, op, value):
        """Return (lookup_kwargs, negate) for a rule, or (None, False) if invalid."""
        ftype = definition["type"]
        orm = definition["orm"]
        if ftype == "text":
            spec = self._TEXT_LOOKUPS.get(op)
            if not spec or not str(value).strip():
                return None, False
            lookup, negate = spec
            return {f"{orm}__{lookup}": value}, negate
        if ftype in ("number", "date"):
            lookup = self._SCALAR_LOOKUPS.get(op)
            if not lookup:
                return None, False
            parsed = self._parse_scalar(ftype, value)
            if parsed is None:
                return None, False
            path = f"{orm}__date" if (ftype == "date" and definition.get("datetime")) else orm
            return {f"{path}__{lookup}": parsed}, False
        if ftype == "choice":
            if not str(value).strip():
                return None, False
            return {orm: value}, op == "isnot"
        if ftype == "boolean":
            return {orm: str(value).lower() in ("true", "1", "yes", "on")}, False
        if ftype in ("person", "relation"):
            ids = value if isinstance(value, list) else [value]
            ids = [i for i in ids if i not in (None, "")]
            # Validate each id against the related PK type, dropping any the
            # database could not handle (a non-UUID for a UUID PK raises
            # ValidationError; an oversized integer for an integer PK raises
            # OverflowError). An empty result means the rule matches nothing,
            # so it is skipped rather than applied.
            pk_kind = definition.get("pk_kind")
            if pk_kind == "uuid":
                ids = [u for u in (parse_uuid(i) for i in ids) if u is not None]
            elif pk_kind == "int":
                ids = [n for n in (parse_int(i) for i in ids) if n is not None]
            if not ids:
                return None, False
            return {f"{orm}__in": ids}, op == "notin"
        return None, False

    @staticmethod
    def _parse_scalar(ftype, value):
        text = str(value).strip()
        if not text:
            return None
        if ftype == "date":
            # parse_date returns None for an unparseable string but raises
            # ValueError on a well-formed yet out-of-calendar date such as
            # "2024-02-30"; treat both as "no value".
            try:
                return parse_date(text)
            except (TypeError, ValueError):
                return None
        if "." in text:
            try:
                number = float(text)
            except (TypeError, ValueError):
                return None
            # Reject inf / nan so a non-finite value never reaches the column.
            return number if math.isfinite(number) else None
        # Bound the magnitude so an oversized integer (e.g. 10**40) cannot
        # raise OverflowError when it reaches an integer column.
        return parse_int(text, min_value=INT_MIN, max_value=INT_MAX)

    def filter_queryset_advanced(self, qs):
        if not self.advanced_filters:
            return qs
        by_key = {f["key"]: f for f in self.get_filter_fields()}
        needs_distinct = False
        for raw in self.request.GET.getlist("rule"):
            try:
                rule = json.loads(raw)
            except (TypeError, ValueError):
                continue
            # A rule must be an object; a bare JSON scalar/array (e.g. ?rule=5)
            # has no .get and would raise AttributeError.
            if not isinstance(rule, dict):
                continue
            definition = by_key.get(rule.get("f"))
            if not definition:
                continue
            cond, negate = self._build_condition(definition, rule.get("o"), rule.get("v"))
            if cond is None:
                continue
            qs = qs.exclude(**cond) if negate else qs.filter(**cond)
            if definition["type"] in ("person", "relation"):
                needs_distinct = True
        return qs.distinct() if needs_distinct else qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if self.advanced_filters:
            ctx["filter_fields_json"] = json.dumps(self.get_filter_fields())
            ctx["filter_rules_json"] = json.dumps(
                [r for r in (_safe_json(raw) for raw in self.request.GET.getlist("rule")) if r is not None]
            )
        return ctx


def _safe_json(raw):
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        return None


class SavedFilterMixin:
    """Expose the user's saved filters for this list (own + shared).

    Adds ``saved_filters`` (each: id, name, query, is_shared, owned) and
    ``saved_filter_view_key`` to the context so the offcanvas can list, apply,
    save and delete them. The view key is the same ``app_label.model_name`` used
    by the column preferences.
    """

    def get_saved_filter_view_key(self):
        model = getattr(self, "model", None)
        return f"{model._meta.app_label}.{model._meta.model_name}" if model else ""

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = getattr(self.request, "user", None)
        if user and user.is_authenticated:
            from django.db.models import Q

            from accounts.models import SavedFilter

            key = self.get_saved_filter_view_key()
            saved = (
                SavedFilter.objects.filter(Q(owner=user) | Q(is_shared=True), view_key=key)
                .select_related("owner")
            )
            ctx["saved_filters"] = [
                {
                    "id": str(f.id),
                    "name": f.name,
                    "query": f.query,
                    "is_shared": f.is_shared,
                    "owned": f.owner_id == user.id,
                }
                for f in saved
            ]
            ctx["saved_filter_view_key"] = key
        return ctx
