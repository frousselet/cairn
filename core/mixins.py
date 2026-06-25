from django.db.models import Count, F
from django.http import HttpResponse
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

from core.db import NaturalSortKey


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
        return ctx


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

    def get_queryset(self):
        qs = super().get_queryset()
        # Snapshot the scope/sort-filtered queryset before the view's own status /
        # type facets, so the summary counts reflect the whole visible list.
        self._summary_base_qs = qs
        return qs

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
        from core.workflow import get_workflow, workflow_name_for

        try:
            workflow = get_workflow(workflow_name_for(model))
        except Exception:
            return []
        return [(state.code, state.label) for state in workflow.states]

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
                items = [
                    {
                        "value": value,
                        "label": label,
                        "count": counts.get(value, 0),
                        "active": str(current) == str(value),
                    }
                    for value, label in self._summary_label_pairs(model)
                    if counts.get(value, 0)
                ]
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
