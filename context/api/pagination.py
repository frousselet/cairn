# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
from django.core.exceptions import FieldDoesNotExist
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


def stable_order(queryset):
    """Give ``queryset`` a total order, so its pages neither repeat nor skip a row.

    A database returns the rows of an unordered query in whatever order suits
    it, and that order may differ between two requests : page 2 can then show a
    row page 1 already showed, and another row is never listed. The same
    happens with an order that has ties (``?ordering=priority``). So :

    - an unordered queryset is listed oldest first (``created_at``) when the
      model has that field;
    - the primary key is appended to any order as the final tie-breaker.

    Only querysets of model instances are touched : adding a column to the
    order of a ``values()`` / aggregated or combined query would change what
    it groups by.
    """
    query = getattr(queryset, "query", None)
    model = getattr(queryset, "model", None)
    if query is None or model is None or getattr(queryset, "_fields", None) is not None:
        return queryset
    if query.combinator or query.is_sliced:
        return queryset
    pk_names = {"pk", "-pk", model._meta.pk.name, f"-{model._meta.pk.name}"}
    if queryset.ordered:
        current = list(query.order_by) or list(model._meta.ordering or [])
        if any(isinstance(term, str) and term in pk_names for term in current):
            return queryset
        return queryset.order_by(*current, "pk")
    try:
        model._meta.get_field("created_at")
    except FieldDoesNotExist:
        return queryset.order_by("pk")
    return queryset.order_by("created_at", "pk")


class StandardPagination(PageNumberPagination):
    page_size = 25
    page_size_query_param = "page_size"
    max_page_size = 100

    def paginate_queryset(self, queryset, request, view=None):
        return super().paginate_queryset(stable_order(queryset), request, view=view)

    def get_paginated_response(self, data):
        return Response(
            {
                "status": "success",
                "data": data,
                "meta": {
                    "page": self.page.number,
                    "page_size": self.get_page_size(self.request),
                    "total_count": self.page.paginator.count,
                    "total_pages": self.page.paginator.num_pages,
                },
            }
        )

    def get_paginated_response_schema(self, schema):
        return {
            "type": "object",
            "properties": {
                "status": {"type": "string", "example": "success"},
                "data": schema,
                "meta": {
                    "type": "object",
                    "properties": {
                        "page": {"type": "integer"},
                        "page_size": {"type": "integer"},
                        "total_count": {"type": "integer"},
                        "total_pages": {"type": "integer"},
                    },
                },
            },
        }
