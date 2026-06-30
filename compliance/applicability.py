"""Risk-driven applicability for compliance requirements.

When a :class:`~compliance.models.Framework` has
``applicability_managed_by_risks`` enabled, the applicability of each of its
requirements is derived automatically instead of being set by hand: a
requirement is applicable when at least one of its linked risks is in a
reportable (active) lifecycle state, and not applicable otherwise.

``Requirement.is_applicable`` stays a stored field so every existing consumer
(SoA report, Section/Framework recalculation, ``is_applicable`` filters) keeps
working unchanged; this module is the single, idempotent place that keeps it in
sync with the risk register.
"""

from django.utils.translation import gettext_lazy as _

from core.lifecycle import reportable

APPLICABLE_AUTO_JUSTIFICATION = _(
    "Automatically applicable: at least one active risk is linked to this "
    "requirement."
)
NOT_APPLICABLE_AUTO_JUSTIFICATION = _(
    "Automatically not applicable: no active risk is linked to this requirement."
)


def framework_is_managed(framework):
    """True when *framework* derives its requirements' applicability from risks."""
    return bool(framework and framework.applicability_managed_by_risks)


def recompute_requirement_applicability(requirement):
    """Refresh ``requirement.is_applicable`` from its linked risks.

    No-op when the requirement's framework does not manage applicability. The
    write is idempotent and only persisted when a value actually changes, so it
    is safe to call from signals, forms, the API and MCP. Saving the requirement
    triggers the existing ``_recalculate_chain`` post-save signal, which refreshes
    the parent Section and Framework compliance levels.
    """
    framework = requirement.framework
    if not framework_is_managed(framework):
        return False

    applicable = reportable(requirement.linked_risks.all()).exists()
    justification = str(
        APPLICABLE_AUTO_JUSTIFICATION if applicable
        else NOT_APPLICABLE_AUTO_JUSTIFICATION
    )
    if (
        requirement.is_applicable == applicable
        and requirement.applicability_justification == justification
    ):
        return False

    requirement.is_applicable = applicable
    requirement.applicability_justification = justification
    requirement.save(
        update_fields=[
            "is_applicable",
            "applicability_justification",
            "updated_at",
        ]
    )
    return True
