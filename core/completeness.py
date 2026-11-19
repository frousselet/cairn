# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""What a record still needs before it is complete.

A record is created with the few fields that make it exist, then completed on
its own page ("create short, complete on the record", see
``docs/sdk/usability-standard.md``). Asking less at creation must not lower
what the record is worth once it is relied upon : this module is how a model
says what *complete* means, so that

- the detail page lists what is missing, each line opening the dialog that
  fills it (``{% completeness_card %}``);
- the lifecycle refuses to move an incomplete record to a step that makes it
  authoritative, and says what is missing (:func:`refuse_if_incomplete`,
  called by ``core.lifecycle_service.perform_transition`` once the move is
  legal and allowed : the web interface, the REST API and the MCP server all
  go through it. The MCP create and update tools, which may write a state
  directly for an import, call it as well);
- the API and the MCP server report the same list (:func:`as_payload`).

A model declares it once::

    class Scope(BaseModel):
        COMPLETENESS = Completeness(
            Requirement(
                "managers", _("assign a manager"),
                fields=["managers"], section="managers",
            ),
            Requirement(
                "sites", _("list the sites it covers"),
                fields=["included_sites"], section="sites", blocking=False,
            ),
            before=("validation", "in_force"),
        )

A label is an action in the infinitive, **without a capital** : it is shown
capitalised as a line of the list, and as written inside the sentence of a
refusal ("... this remains to be done : assign a manager.").
"""

from __future__ import annotations

import html
from dataclasses import dataclass

from django.db import models
from django.utils.html import strip_tags
from django.utils.text import capfirst
from django.utils.translation import gettext as _

__all__ = [
    "Completeness",
    "Requirement",
    "as_payload",
    "completeness_of",
    "is_filled",
    "refuse_if_incomplete",
]


def is_filled(obj, name) -> bool:
    """Whether the attribute ``name`` of ``obj`` holds an answer.

    A relation to many holds one when it has a row, a text when something is
    left once its markup and spaces are removed (an emptied rich-text field
    stores ``<p><br></p>``), any other value when it is not ``None``. A
    boolean is always an answer : ``False`` is one.
    """
    value = getattr(obj, name, None)
    if value is None:
        return False
    if isinstance(value, models.Manager):
        if getattr(obj, "pk", None) is None or obj._state.adding:
            return False
        return value.all().exists()
    if isinstance(value, str):
        return bool(html.unescape(strip_tags(value)).replace("\xa0", " ").strip())
    if isinstance(value, (list, tuple, dict, set)):
        return bool(value)
    return True


class Requirement:
    """One thing a record needs before it is complete.

    ``key``      : stable identifier (API, MCP, tests).
    ``label``    : the act, in the infinitive, without a capital.
    ``fields``   : attributes that must all hold an answer.
    ``any_of``   : attributes of which one at least must hold an answer.
    ``check``    : ``callable(obj) -> bool`` for anything else.
    ``section``  : key of the form section that fills it (``Step(key=...)``).
    ``href``     : ``callable(obj) -> url`` for what is done on another page
        (attaching the support assets of an essential asset), when no section
        of the record's own form fills it.
    ``blocking`` : ``True`` (default) when the lifecycle waits for it,
        ``False`` for an advice the record can do without.
    ``when``     : ``callable(obj) -> bool`` for a requirement that concerns
        some records of the model only (each workshop of an EBIOS RM study
        has its own deliverables). A record it does not concern is neither
        asked for it nor credited with it : the requirement is left out of
        its report.
    """

    __slots__ = ("key", "label", "fields", "any_of", "check", "section", "href", "blocking", "when")

    def __init__(self, key, label, *, fields=(), any_of=(), check=None, section=None, href=None, blocking=True,
                 when=None):
        if not (fields or any_of or check):
            raise ValueError(f"Requirement '{key}' tests nothing : give fields, any_of or check.")
        self.key = key
        self.label = label
        self.fields = tuple(fields)
        self.any_of = tuple(any_of)
        self.check = check
        self.section = section
        self.href = href
        self.blocking = blocking
        self.when = when

    def concerns(self, obj) -> bool:
        """Whether ``obj`` is one of the records the requirement is about."""
        return self.when is None or bool(self.when(obj))

    def is_met(self, obj) -> bool:
        if any(not is_filled(obj, name) for name in self.fields):
            return False
        if self.any_of and not any(is_filled(obj, name) for name in self.any_of):
            return False
        if self.check is not None and not self.check(obj):
            return False
        return True

    def __repr__(self):
        return f"Requirement({self.key!r})"


@dataclass(frozen=True)
class Item:
    """A requirement and whether the record meets it."""

    requirement: Requirement
    met: bool
    #: Where it is done, when it is not a section of the record's own form.
    href: str = ""

    @property
    def key(self):
        return self.requirement.key

    @property
    def label(self):
        """The act, capitalised : a line of the list."""
        return capfirst(str(self.requirement.label))

    @property
    def section(self):
        return self.requirement.section

    @property
    def blocking(self):
        return self.requirement.blocking


@dataclass(frozen=True)
class Report:
    """What a record has, and what it still needs."""

    items: tuple
    #: Label of the step the record cannot reach while a blocking item is
    #: missing, or ``""`` when it already stands on (or past) such a step.
    gate_label: str = ""

    @property
    def missing(self):
        return [item for item in self.items if not item.met]

    @property
    def blocking_missing(self):
        return [item for item in self.items if not item.met and item.blocking]

    @property
    def advised_missing(self):
        return [item for item in self.items if not item.met and not item.blocking]

    @property
    def done(self):
        return sum(1 for item in self.items if item.met)

    @property
    def total(self):
        return len(self.items)

    @property
    def can_advance(self):
        """Nothing the lifecycle waits for is missing."""
        return not self.blocking_missing

    @property
    def is_complete(self):
        """Nothing at all is missing."""
        return not self.missing


class Completeness:
    """The requirements of a model, and the steps that wait for them.

    ``before`` lists the codes of the lifecycle steps a record cannot enter
    while a blocking requirement is missing, in the order the lifecycle
    walks them.
    """

    def __init__(self, *requirements, before=()):
        keys = [r.key for r in requirements]
        duplicated = sorted({k for k in keys if keys.count(k) > 1})
        if duplicated:
            raise ValueError(f"Completeness : duplicated requirement key(s) {', '.join(duplicated)}.")
        self.requirements = tuple(requirements)
        self.before = tuple(before)

    def evaluate(self, obj) -> Report:
        items = []
        for requirement in self.requirements:
            if not requirement.concerns(obj):
                continue
            met = requirement.is_met(obj)
            href = requirement.href(obj) if (requirement.href and not met) else ""
            items.append(Item(requirement, met, href or ""))
        return Report(items=tuple(items), gate_label=self._gate_label(obj))

    def _gate_label(self, obj):
        """Label of the first gated step, unless the record stands on one."""
        if not self.before or getattr(obj, "workflow_state", None) in self.before:
            return ""
        try:
            return str(obj.get_lifecycle().step(self.before[0]).label)
        except Exception:
            return ""


def completeness_of(obj):
    """The :class:`Report` of ``obj``, or ``None`` when its model declares none."""
    spec = getattr(type(obj), "COMPLETENESS", None)
    if spec is None:
        return None
    return spec.evaluate(obj)


def refuse_if_incomplete(obj, target):
    """Refuse to move ``obj`` to ``target`` while a blocking item is missing.

    Raises :class:`core.lifecycle.DomainRefusalError`, whose sentence names
    the step and what remains to be done : it is shown as is by the web
    interface, the REST API and the MCP server.
    """
    spec = getattr(type(obj), "COMPLETENESS", None)
    if spec is None or target not in spec.before:
        return
    missing = [item for item in spec.evaluate(obj).items if not item.met and item.blocking]
    if not missing:
        return
    from core.lifecycle import DomainRefusalError

    try:
        step = str(obj.get_lifecycle().step(target).label)
    except Exception:
        step = str(target)
    raise DomainRefusalError(
        _('Before moving to "%(step)s", this remains to be done : %(todo)s.')
        % {"step": step, "todo": " ; ".join(str(item.requirement.label) for item in missing)}
    )


def as_payload(obj):
    """The completeness of ``obj`` as plain data (REST API, MCP), or ``None``."""
    report = completeness_of(obj)
    if report is None:
        return None
    return {
        "complete": report.is_complete,
        "can_advance": report.can_advance,
        "missing": [
            {"key": item.key, "label": item.label, "blocking": item.blocking}
            for item in report.missing
        ],
    }
