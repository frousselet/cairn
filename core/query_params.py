"""Safe coercion helpers for untrusted request parameters.

List and detail views routinely feed a raw ``request.GET`` / ``request.POST``
value straight into an ORM filter on a typed column (a UUID primary key, an
integer primary key, or a date). When the value is of the wrong type, Django
raises ``ValidationError`` / ``ValueError`` / ``OverflowError`` at query
evaluation time, which is uncaught and surfaces as an HTTP 500 (leaking a
DEBUG traceback in development).

These helpers coerce an untrusted value to the expected type, returning
``None`` when it cannot be parsed, so the caller can simply skip the filter
instead of crashing::

    assessment_id = parse_uuid(request.GET.get("assessment"))
    if assessment_id:
        qs = qs.filter(assessment_id=assessment_id)
"""

import uuid
from datetime import date

from django.utils.dateparse import parse_date

# PostgreSQL ``bigint`` / SQLite signed 64-bit bounds. Filtering an integer
# column with a value outside this range raises ``OverflowError`` on some
# backends, so any out-of-range value is treated as unparseable.
INT_MIN = -9223372036854775808
INT_MAX = 9223372036854775807


def parse_uuid(value):
    """Return *value* as a :class:`uuid.UUID`, or ``None`` if it is not one.

    Accepts an existing ``UUID`` instance or any string Python's ``uuid``
    module can parse; anything else (a malformed string, ``None``, a number)
    yields ``None``.
    """
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, uuid.UUID):
        return value
    try:
        return uuid.UUID(str(value))
    except (ValueError, TypeError, AttributeError):
        return None


def parse_int(value, *, min_value=INT_MIN, max_value=INT_MAX):
    """Return *value* as a bounded ``int``, or ``None`` if it is not a valid,
    in-range integer.

    Bounding the magnitude is what prevents an ``OverflowError`` once the value
    reaches a database integer column.
    """
    if value is None or isinstance(value, bool):
        return None
    try:
        number = int(str(value).strip())
    except (ValueError, TypeError):
        return None
    if number < min_value or number > max_value:
        return None
    return number


def parse_date_param(value):
    """Return *value* as a :class:`datetime.date`, or ``None`` if invalid.

    Accepts an existing ``date`` or an ISO ``YYYY-MM-DD`` string. A string that
    does not match the format, or an out-of-calendar date such as
    ``2020-13-45``, yields ``None`` (``django.utils.dateparse.parse_date``
    returns ``None`` for the former and raises ``ValueError`` for the latter).
    """
    if value is None or value == "":
        return None
    if isinstance(value, date):
        return value
    try:
        return parse_date(str(value))
    except (ValueError, TypeError):
        return None
