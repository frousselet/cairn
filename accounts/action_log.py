# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""The action log : every history table read as one list, a page at a time.

Each audited model has its own history table (django-simple-history), and the
action log shows them all together, newest first. Reading every row of every
table to sort them in memory, as this page first did, costs the whole audit
trail on each visit : it grows without bound, and an instance that has been
used for a year could no longer open its own log.

``MergedHistory`` behaves like a list for Django's paginator, but only ever
asks the database for what a page shows :

1. the *keys* of the page (which table, which row, when), from one
   ``UNION ALL`` over the tables, ordered and sliced by the database, which
   walks the ``history_date`` index of each table;
2. the rows behind those keys, one query per table present on the page;
3. the total, one count over the same union.
"""

from django.db.models import Exists, IntegerField, OuterRef, Subquery, Value

from core.history import WORKFLOW_FIELD, EntryKind


class MergedHistory:
    """The rows of ``models`` (history models), newest first, read lazily."""

    def __init__(self, models):
        self.models = list(models)
        self._count = None

    def _keys(self):
        """``(history_id, history_date, source)`` of every row, as one union."""
        parts = [
            model.objects.order_by()
            .annotate(log_source=Value(index, output_field=IntegerField()))
            .values_list("history_id", "history_date", "log_source")
            for index, model in enumerate(self.models)
        ]
        if not parts:
            return None
        return parts[0].union(*parts[1:], all=True) if len(parts) > 1 else parts[0]

    def count(self):
        if self._count is None:
            keys = self._keys()
            self._count = keys.count() if keys is not None else 0
        return self._count

    __len__ = count

    def __getitem__(self, item):
        if not isinstance(item, slice):
            raise TypeError("MergedHistory is read a page at a time")
        keys = self._keys()
        if keys is None:
            return []
        # The table and the row id break ties between rows saved at the same
        # instant, so a row never appears on two pages or on none.
        page = list(keys.order_by("-history_date", "log_source", "-history_id")[item])
        wanted = {}
        for history_id, _date, source in page:
            wanted.setdefault(source, []).append(history_id)
        rows = {}
        for source, ids in wanted.items():
            for row in self._rows(self.models[source], ids):
                rows[(source, row.history_id)] = row
        return [rows[(source, history_id)] for history_id, _date, source in page if (source, history_id) in rows]

    @staticmethod
    def _rows(model, ids):
        """The full rows, with what classifying them needs already attached :
        the lifecycle state of the previous version of the same record."""
        queryset = model.objects.select_related("history_user").filter(history_id__in=ids)
        previous = model.objects.filter(
            id=OuterRef("id"), history_date__lt=OuterRef("history_date"),
        ).order_by("-history_date")
        queryset = queryset.annotate(log_has_previous=Exists(previous))
        if any(field.name == WORKFLOW_FIELD for field in model._meta.fields):
            queryset = queryset.annotate(log_previous_state=Subquery(previous.values(WORKFLOW_FIELD)[:1]))
        return queryset


def entry_kind(record):
    """What a row of the log records : a creation, a deletion, a lifecycle
    transition or a plain update.

    Same answer as ``core.history.classify_record``, read from the annotations
    ``MergedHistory`` attaches instead of one extra query per row.
    """
    if record.history_type == "+":
        return EntryKind.CREATE
    if record.history_type == "-":
        return EntryKind.DELETE
    if (
        getattr(record, "log_has_previous", False)
        and hasattr(record, "log_previous_state")
        and record.log_previous_state != getattr(record, WORKFLOW_FIELD, None)
    ):
        return EntryKind.TRANSITION
    return EntryKind.UPDATE
