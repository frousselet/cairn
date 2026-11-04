# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""Services of module 8 shared by the web, REST and MCP surfaces.

- :func:`create_controls_from_requirements` (RG-CTL-05);
- :func:`requirement_coverage` : per applicable requirement of a framework,
  its reportable controls with their state and effectiveness (RG-CTL-18).
"""

from django.db import transaction
from django.utils.translation import gettext as _

from controls.constants import CONTROL_IMPLEMENTED, CONTROL_PLANNED
from core.lifecycle import reportable


class ImplementationSummary:
    """RG-CTL-18 : the *Implementation* column of the SoA."""

    IMPLEMENTED = "implemented"
    PARTIAL = "partial"
    PLANNED = "planned"
    NONE = "none"

    @classmethod
    def label(cls, value):
        return {
            cls.IMPLEMENTED: _("Implemented"),
            cls.PARTIAL: _("Partially implemented"),
            cls.PLANNED: _("Planned"),
            cls.NONE: _("No control"),
        }[value]


def summarise_implementation(states):
    """``states`` : the lifecycle steps of a requirement's reportable controls."""
    states = list(states)
    if not states:
        return ImplementationSummary.NONE
    implemented = sum(1 for s in states if s == CONTROL_IMPLEMENTED)
    if implemented == len(states):
        return ImplementationSummary.IMPLEMENTED
    if implemented:
        return ImplementationSummary.PARTIAL
    if all(s == CONTROL_PLANNED for s in states):
        return ImplementationSummary.PLANNED
    return ImplementationSummary.PARTIAL


def create_controls_from_requirements(framework, user, requirement_ids=None, scope_ids=None):
    """RG-CTL-05 : one proposed control per applicable requirement with no
    control yet. Returns ``(created, skipped)`` lists : the new controls, and
    the requirements left out because a control already covers them (any
    step, a retired one included : re-covering a requirement is a decision,
    not a bulk action) or because they are not applicable.
    """
    from controls.models import Control

    requirements = framework.requirements.all().order_by("requirement_number", "created_at")
    if requirement_ids is not None:
        requirements = requirements.filter(pk__in=list(requirement_ids))
    if scope_ids is None:
        scope_ids = list(framework.scopes.values_list("pk", flat=True))
    created, skipped = [], []
    with transaction.atomic():
        for requirement in requirements.select_for_update():
            if not requirement.is_applicable or requirement.controls.exists():
                skipped.append(requirement)
                continue
            control = Control.objects.create(
                name=(requirement.name or requirement.requirement_number)[:255],
                description=requirement.description or requirement.name,
                owner=requirement.owner,
                created_by=user,
            )
            control.requirements.add(requirement)
            if scope_ids:
                control.scopes.set(scope_ids)
            created.append(control)
    return created, skipped


def requirement_coverage(framework):
    """RG-CTL-18 : rows for every reportable, applicable requirement of
    ``framework``, each with its reportable controls (state, effectiveness)
    and the implementation summary."""
    from controls.models import Control

    requirements = reportable(framework.requirements.filter(is_applicable=True)).order_by(
        "requirement_number", "created_at"
    )
    rows = []
    for requirement in requirements:
        controls = list(reportable(Control.objects.filter(requirements=requirement)).order_by("reference"))
        summary = summarise_implementation(c.workflow_state for c in controls)
        rows.append({
            "requirement": requirement,
            "controls": controls,
            "implementation": summary,
            "implementation_label": ImplementationSummary.label(summary),
        })
    return rows
