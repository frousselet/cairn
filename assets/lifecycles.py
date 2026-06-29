"""Standardised lifecycles for the assets module (rebuilt engine).

Currently defines the **supplier** lifecycle: a branching, cyclic supplier-risk
lifecycle. After a one-off ``Integration`` step the supplier enters a recurring
review cycle (``Risk questionnaire`` -> ``Evaluation`` -> ``Compliant`` /
``Non-compliant``) that loops back to the questionnaire for the next review
round. The mandatory Draft entry and Archived exit bookend it; Archived is
reachable from any step (and a supplier can be restored from it). Transition
forms and role restrictions are intentionally left for a later phase.

Topology (codes):

    draft -> integration -> risk_questionnaire -> evaluation
                                  ^                    |
                                  |          +---------+---------+
                                  |          |                   |
                                  |     compliant           non_compliant
                                  |          |                   |
                                  +----------+-------------------+   (loop back)
    any -> archived ;  archived -> draft (restore)

``integration`` happens once (entry path only); the recurring cycle is
``risk_questionnaire`` (step 2) -> ``evaluation`` (step 3) -> the branch pair
(``compliant`` 4a / ``non_compliant`` 4b) -> back to step 2.

Imported from ``AssetsConfig.ready()`` so the lifecycle is registered in every
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

SUPPLIER_LIFECYCLE_NAME = "supplier"

# The operational stages of the supplier-risk lifecycle.
# (code, label, tone)
_SUPPLIER_STAGES = [
    ("integration", _("Onboarding"), "info"),
    ("risk_questionnaire", _("Risk questionnaire"), "info"),
    ("evaluation", _("Evaluation"), "info"),
    ("compliant", _("Compliant asset"), "success"),
    ("non_compliant", _("Non-compliant asset"), "warning"),
    ("compensatory_measures", _("Compensatory measures"), "info"),
]

#: The step the recurring review cycle loops back to (step 2). Both branch
#: outcomes return here for the next round; ``integration`` (step 1) is on the
#: entry path only and is never revisited.
SUPPLIER_CYCLE_ENTRY = "risk_questionnaire"


def _build_supplier_lifecycle() -> Lifecycle:
    steps = [draft_step()]
    for code, label, tone in _SUPPLIER_STAGES:
        steps.append(
            Step(
                code,
                label,
                kind=StepKind.INTERMEDIATE,
                counts_in_reports=True,
                linkable=True,
                tone=tone,
            )
        )
    steps.append(archived_step())

    transitions = [
        # Entry path (single pass through integration).
        Transition("integration", source="draft", label=_("Start onboarding")),
        Transition(
            "risk_questionnaire", source="integration", label=_("Send risk questionnaire")
        ),
        # Recurring review cycle: questionnaire -> evaluation -> branch.
        Transition("evaluation", source="risk_questionnaire", label=_("Start evaluation")),
        # Terminal binary branch off the evaluation.
        Transition("compliant", source="evaluation", label=_("Mark compliant")),
        Transition("non_compliant", source="evaluation", label=_("Mark non-compliant")),
        # Compliant outcome loops back to step 2 for the next review round.
        Transition(
            "risk_questionnaire", source="compliant", label=_("New review cycle")
        ),
        # Non-compliant goes through compensatory measures, then is re-evaluated.
        Transition(
            "compensatory_measures", source="non_compliant", label=_("Add compensatory measures")
        ),
        Transition(
            "evaluation", source="compensatory_measures", label=_("Re-evaluate")
        ),
        # Exit from any step, and restore from the archive.
        Transition("archived", source=ANY, label=_("Archive")),
        Transition("draft", source="archived", label=_("Restore")),
    ]

    return Lifecycle(SUPPLIER_LIFECYCLE_NAME, steps, transitions, layout="cycle")


SUPPLIER_LIFECYCLE = register_lifecycle(_build_supplier_lifecycle())


# ── Contract lifecycle ──────────────────────────────────────────────────────
#
# A contract moves Draft -> Active, can Expire (and be Renewed back to Active),
# and can be Terminated from any state (the Archived exit; terminated contracts
# stay in reports for audit history). The step codes are exactly the
# ``ContractStatus`` values, so the legacy ``status`` field stays coherent with
# ``workflow_state`` via ``sync_legacy_status`` in ``Contract.save()``.
CONTRACT_LIFECYCLE_NAME = "contract"


def _build_contract_lifecycle() -> Lifecycle:
    steps = [
        draft_step(),
        Step(
            "active",
            _("Active"),
            kind=StepKind.INTERMEDIATE,
            counts_in_reports=True,
            linkable=True,
            tone="success",
        ),
        Step(
            "expired",
            _("Expired"),
            kind=StepKind.INTERMEDIATE,
            counts_in_reports=True,
            tone="warning",
        ),
        # Terminated is the Archived exit, but kept in reports for traceability.
        Step(
            "terminated",
            _("Terminated"),
            kind=StepKind.ARCHIVED,
            counts_in_reports=True,
            tone="dark",
        ),
    ]
    transitions = [
        Transition("active", source="draft", label=_("Activate")),
        Transition("expired", source="active", label=_("Expire")),
        Transition("active", source="expired", label=_("Renew")),
        Transition(
            "terminated", source=ANY, label=_("Terminate"), requires_comment=True
        ),
    ]
    return Lifecycle(CONTRACT_LIFECYCLE_NAME, steps, transitions, layout="line")


CONTRACT_LIFECYCLE = register_lifecycle(_build_contract_lifecycle())
