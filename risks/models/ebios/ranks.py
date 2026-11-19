# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""Rows that keep a rank among the rows of their parent."""

from django.db import models


class RankedInParent:
    """A row whose ``order`` is unique among the rows of its parent.

    The steps of an attack path and the techniques of an operational scenario
    are read in order, and the database refuses two rows of one rank under
    the same parent. A reader is not asked where a new row stands : it comes
    last. ``RANK_PARENT`` names the relation to the parent.
    """

    RANK_PARENT = "scenario"

    def come_last_when_unranked(self):
        """Give a new row with no rank the one after the last row of its parent.

        Called before saving by the surfaces that let the rank be left out
        (the web form, the MCP tools).
        """
        parent_id = getattr(self, f"{self.RANK_PARENT}_id", None)
        if not self._state.adding or self.order or not parent_id:
            return
        siblings = type(self).objects.filter(**{f"{self.RANK_PARENT}_id": parent_id})
        self.order = (siblings.aggregate(last=models.Max("order"))["last"] or 0) + 1
