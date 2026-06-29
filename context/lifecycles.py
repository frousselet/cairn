"""Standardised lifecycles for the context module (rebuilt engine).

Defines the **scope** and **site** lifecycles.

The **scope** lifecycle is a governance flow for an ISMS perimeter. After the
mandatory Draft entry the perimeter is drafted (``Definition``), submitted for
sign-off (``Validation``) and made authoritative (``In force``); an in-force
perimeter is then periodically re-examined (``Review``), which loops back to
``In force`` for the next cycle. Archived is the exit, reachable from any step
(and a scope can be restored from it). Both the in-force and review steps are
authoritative (count in reports + linkable) - a perimeter under review is still
the active tenancy boundary; everything earlier is not yet authoritative,
preserving the governance the legacy default workflow expressed (only the
validated-equivalent state counted / linked).

    draft -> definition -> validation -> in_force -> review
                                            ^            |
                                            +------------+   (periodic review loop)
    any -> archived ;  archived -> draft (restore)

The **site** lifecycle is the operational flow of a physical location covered by
the ISMS. After the Draft entry the site is brought online (``Commissioning`` ->
``Operational``); an operational site is periodically re-examined (``Review``),
looping back to ``Operational``; it is eventually taken offline
(``Decommissioned``). The operational and review steps are authoritative (count
in reports + linkable) - a site under review is still in service; everything
earlier (still being commissioned) and the decommissioned end are not. Archived
is the from-any exit (and a site can be restored from it).

    draft -> commissioning -> operational -> review
                                  ^   |          |
                                  +---+----------+   (periodic review loop)
                                      v
                                decommissioned
    any -> archived ;  archived -> draft (restore)

Imported from ``ContextConfig.ready()`` so the lifecycles are registered in every
context (tests, management commands, servers).
"""

from django.utils.translation import gettext_lazy as _

from core.lifecycle import (
    ANY,
    Lifecycle,
    Step,
    StepKind,
    Transition,
    archived_step,
    draft_step,
    register_lifecycle,
)

SCOPE_LIFECYCLE_NAME = "scope"


def _build_scope_lifecycle() -> Lifecycle:
    steps = [
        # Mandatory Draft entry (the deletable stub a new scope starts on).
        draft_step(),
        # The operational stages the perimeter walks through. The in-force and
        # review stages are authoritative (count in reports, linkable); the
        # earlier drafting stages are not.
        Step("definition", _("Definition"), kind=StepKind.INTERMEDIATE, tone="info"),
        Step("validation", _("Validation"), kind=StepKind.INTERMEDIATE, tone="warning"),
        Step(
            "in_force",
            _("In force"),
            kind=StepKind.INTERMEDIATE,
            counts_in_reports=True,
            linkable=True,
            tone="success",
        ),
        Step(
            "review",
            _("Review"),
            kind=StepKind.INTERMEDIATE,
            counts_in_reports=True,
            linkable=True,
            tone="warning",
        ),
        # Mandatory Archived exit.
        archived_step(),
    ]

    transitions = [
        # Forward path along the spine (a straight progression, no rework edges).
        Transition("definition", source="draft", label=_("Start definition")),
        Transition("validation", source="definition", label=_("Submit for validation")),
        Transition("in_force", source="validation", label=_("Put in force")),
        # Periodic review of an in-force perimeter, looping back to In force.
        Transition("review", source="in_force", label=_("Start review")),
        Transition("in_force", source="review", label=_("Complete review")),
        # Exit from any step, and restore from the archive.
        Transition("archived", source=ANY, label=_("Archive")),
        Transition("draft", source="archived", label=_("Restore")),
    ]

    # ``graph`` routes the detail-page stepper through the schema-driven directed
    # graph renderer (the same one suppliers use), so the perimeter flow is drawn
    # with arrows, transition labels and the detached Archived exit - visually
    # consistent with every other standardised lifecycle.
    return Lifecycle(SCOPE_LIFECYCLE_NAME, steps, transitions, layout="graph")


SCOPE_LIFECYCLE = register_lifecycle(_build_scope_lifecycle())


SITE_LIFECYCLE_NAME = "site"


def _build_site_lifecycle() -> Lifecycle:
    steps = [
        # Mandatory Draft entry (the deletable stub a new site starts on).
        draft_step(),
        # The operational stages the location walks through. The operational and
        # review stages are authoritative (count in reports, linkable); a site
        # still being commissioned, and a decommissioned one, are not.
        Step("commissioning", _("Commissioning"), kind=StepKind.INTERMEDIATE, tone="info"),
        Step(
            "operational",
            _("Operational"),
            kind=StepKind.INTERMEDIATE,
            counts_in_reports=True,
            linkable=True,
            tone="success",
        ),
        Step(
            "review",
            _("Under review"),
            kind=StepKind.INTERMEDIATE,
            counts_in_reports=True,
            linkable=True,
            tone="warning",
        ),
        # Taken out of service for good. Kept for traceability but no longer
        # authoritative (does not count in reports, not linkable).
        Step("decommissioned", _("Decommissioned"), kind=StepKind.INTERMEDIATE, tone="secondary"),
        # Mandatory Archived exit.
        archived_step(),
    ]

    transitions = [
        # Bring the location online.
        Transition("commissioning", source="draft", label=_("Start commissioning")),
        Transition("operational", source="commissioning", label=_("Bring into service")),
        # Periodic review of an operational site, looping back to Operational.
        Transition("review", source="operational", label=_("Start review")),
        Transition("operational", source="review", label=_("Complete review")),
        # Take the site out of service.
        Transition("decommissioned", source="operational", label=_("Decommission")),
        # Exit from any step, and restore from the archive.
        Transition("archived", source=ANY, label=_("Archive")),
        Transition("draft", source="archived", label=_("Restore")),
    ]

    # ``graph`` routes the detail-page stepper through the schema-driven directed
    # graph renderer (the same one scopes and suppliers use), so the operational
    # flow is drawn with arrows, transition labels and the detached Archived exit.
    return Lifecycle(SITE_LIFECYCLE_NAME, steps, transitions, layout="graph")


SITE_LIFECYCLE = register_lifecycle(_build_site_lifecycle())
