# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""The completeness of a record on the REST API.

Kept apart from :mod:`core.completeness`, which models import : this module
needs Django REST framework, that one must not.
"""

from rest_framework import serializers

from core.completeness import as_payload


class CompletenessSerializerMixin(serializers.Serializer):
    """Add the read-only ``completeness`` of a record to its serializer.

    ``{"complete": bool, "can_advance": bool, "missing": [{"key", "label",
    "blocking"}]}`` : what the record still needs before its lifecycle lets it
    through, as the web page lists it. Served with a single record only : in a
    list it would run the checks of every row (a query per relation checked).
    List the field in ``Meta.fields`` : ``"completeness"``.
    """

    completeness = serializers.SerializerMethodField()

    def get_completeness(self, obj):
        return as_payload(obj)

    def get_fields(self):
        fields = super().get_fields()
        if isinstance(getattr(self, "parent", None), serializers.ListSerializer):
            fields.pop("completeness", None)
        return fields
