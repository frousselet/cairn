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

from assets.constants import EssentialAssetStatus, SupportAssetStatus
from core.lifecycle import (
    ANY,
    Lifecycle,
    Step,
    StepKind,
    Transition,
    archived_step,
    draft_step,
    lifecycle_from_json,
    lifecycle_from_state_flags,
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
# Draft (the generic engine entry) -> Contract draft ("projet de contrat") ->
# Under signature -> In force. While in force it runs a recurring review cycle
# (In force <-> Under review) and may Expire. An expired contract is NOT renewed
# in place: a new contract supersedes it ("annule et remplace"). Any state can
# be Archived (the exit; archived contracts stay in reports for traceability).
# The step codes are exactly the ``ContractStatus`` values, so the legacy
# ``status`` field stays coherent with ``workflow_state`` via
# ``sync_legacy_status`` in ``Contract.save()``.
CONTRACT_LIFECYCLE_NAME = "contract"


def _build_contract_lifecycle() -> Lifecycle:
    steps = [
        # The mandatory generic Draft entry (not a contract stage on its own).
        draft_step(),
        Step(
            "drafting",
            _("Contract draft"),
            kind=StepKind.INTERMEDIATE,
            counts_in_reports=True,
            tone="secondary",
        ),
        Step(
            "signing",
            _("Under signature"),
            kind=StepKind.INTERMEDIATE,
            counts_in_reports=True,
            tone="info",
        ),
        Step(
            "active",
            _("In force"),
            kind=StepKind.INTERMEDIATE,
            counts_in_reports=True,
            linkable=True,
            tone="success",
        ),
        # Periodic contract review: the contract stays in force while reviewed,
        # then loops back to In force for the next review round.
        Step(
            "under_review",
            _("Under review"),
            kind=StepKind.INTERMEDIATE,
            counts_in_reports=True,
            linkable=True,
            tone="info",
        ),
        Step(
            "expired",
            _("Expired"),
            kind=StepKind.INTERMEDIATE,
            counts_in_reports=True,
            tone="warning",
        ),
        Step(
            "archived",
            _("Archived"),
            kind=StepKind.ARCHIVED,
            counts_in_reports=True,
            tone="dark",
        ),
    ]
    transitions = [
        Transition("drafting", source="draft", label=_("Start drafting")),
        Transition("signing", source="drafting", label=_("Send for signature")),
        Transition("active", source="signing", label=_("Bring into force")),
        # Recurring review cycle: in force <-> under review.
        Transition("under_review", source="active", label=_("Start review")),
        Transition("active", source="under_review", label=_("Reviewed")),
        # Expiry. No renewal in place: an expired contract is replaced by a new
        # one (supersedes / "annule et remplace").
        Transition("expired", source="active", label=_("Expire")),
        # Exit from any step. (No requires_comment: the lifecycle stepper UI
        # does not collect a comment yet - that gating is a later phase, and the
        # supplier archive transition is unrestricted for the same reason.)
        Transition("archived", source=ANY, label=_("Archive")),
    ]
    # "graph" routes the detail stepper to the schema-driven directed-graph
    # renderer (dagre + D3, like Suppliers / Scopes): the review back-edge
    # (under_review -> active) draws as a loop and Archive as the archived exit.
    return Lifecycle(CONTRACT_LIFECYCLE_NAME, steps, transitions, layout="graph")


CONTRACT_LIFECYCLE = register_lifecycle(_build_contract_lifecycle())


# ── Certificate lifecycle ───────────────────────────────────────────────────
#
# Draft (the generic engine entry) -> Assessment (the certification audit is
# under way) -> Certified (the certificate is granted and in force) -> Under
# renewal (the recertification / surveillance audit). The recurring
# recertification cycle (Certified <-> Under renewal) is the only non-terminal
# branch. Suspended and Expired are TERMINAL outcomes of the renewal: the body
# suspended the certificate, or it lapsed. There is no reinstatement and no
# renewal in place - re-certifying means issuing a new certificate that
# supersedes this one ("annule et remplace"), so the full history is kept; the
# only move out of a terminal state is Archive. Any state can be Archived (the
# exit; archived certificates stay in reports for traceability). The step codes
# are exactly the ``CertificateStatus`` values, so the legacy ``status`` field
# stays coherent with ``workflow_state`` via ``sync_legacy_status`` in
# ``Certificate.save()``.
CERTIFICATE_LIFECYCLE_NAME = "certificate"


def _build_certificate_lifecycle() -> Lifecycle:
    steps = [
        # The mandatory generic Draft entry (application / preparation stage).
        draft_step(),
        # The certification audit is under way (not certified yet).
        Step(
            "assessment",
            _("Assessment"),
            kind=StepKind.INTERMEDIATE,
            counts_in_reports=True,
            tone="info",
        ),
        # Granted and in force.
        Step(
            "certified",
            _("Certified"),
            kind=StepKind.INTERMEDIATE,
            counts_in_reports=True,
            linkable=True,
            tone="success",
        ),
        # Recertification / surveillance audit: the certificate stays in force
        # while renewed, then loops back to Certified for the next cycle.
        Step(
            "under_renewal",
            _("Under renewal"),
            kind=StepKind.INTERMEDIATE,
            counts_in_reports=True,
            linkable=True,
            tone="info",
        ),
        # Terminal outcome: suspended by the certification body. The only move
        # out is Archive (no reinstatement).
        Step(
            "suspended",
            _("Suspended"),
            kind=StepKind.INTERMEDIATE,
            counts_in_reports=True,
            tone="dark",
        ),
        # Terminal outcome: the certificate lapsed. Replaced by a new one via
        # supersedes, never renewed in place.
        Step(
            "expired",
            _("Expired"),
            kind=StepKind.INTERMEDIATE,
            counts_in_reports=True,
            tone="dark",
        ),
        Step(
            "archived",
            _("Archived"),
            kind=StepKind.ARCHIVED,
            counts_in_reports=True,
            tone="dark",
        ),
    ]
    transitions = [
        # Linear path to certification.
        Transition("assessment", source="draft", label=_("Start assessment")),
        Transition("certified", source="assessment", label=_("Certify")),
        # Recurring recertification cycle: certified <-> under renewal (the only
        # non-terminal branch).
        Transition("under_renewal", source="certified", label=_("Start renewal")),
        Transition("certified", source="under_renewal", label=_("Renewed")),
        # Suspended and Expired are terminal outcomes of the renewal: no
        # reinstatement, no renewal in place. The only move out of them is the
        # from-any Archive below.
        Transition("suspended", source="under_renewal", label=_("Suspend")),
        Transition("expired", source="under_renewal", label=_("Expire")),
        # Exit from any step (archived certificates stay in reports).
        Transition("archived", source=ANY, label=_("Archive")),
    ]
    # "graph" routes the detail stepper to the directed-graph renderer: the
    # recertification back-edge (under_renewal -> certified) draws cleanly, the
    # Suspended / Expired leaves read as terminal, and Archive is the exit.
    return Lifecycle(CERTIFICATE_LIFECYCLE_NAME, steps, transitions, layout="graph")


CERTIFICATE_LIFECYCLE = register_lifecycle(_build_certificate_lifecycle())


# ── Essential asset ─────────────────────────────────────────
#
# The information / business-asset lifecycle, ported from the legacy
# essential_asset workflow (same step codes, labels and governance flags). A
# freshly identified asset is the deletable entry; active and under-review are
# authoritative operational stages (an asset is periodically re-examined,
# looping Active <-> Under review); decommissioned is the exit, kept in reports
# as audit history. Rendered with the directed-graph stepper.

ESSENTIAL_ASSET_LIFECYCLE_NAME = "essential_asset"

# (code, label, counts_in_reports, linkable, deletable, is_initial, is_terminal, tone)
_ESSENTIAL_ASSET_STEPS = [
    (EssentialAssetStatus.IDENTIFIED.value, EssentialAssetStatus.IDENTIFIED.label, True, True, True, True, False, "secondary"),
    (EssentialAssetStatus.ACTIVE.value, EssentialAssetStatus.ACTIVE.label, True, True, False, False, False, "success"),
    (EssentialAssetStatus.UNDER_REVIEW.value, EssentialAssetStatus.UNDER_REVIEW.label, True, True, False, False, False, "warning"),
    (EssentialAssetStatus.DECOMMISSIONED.value, EssentialAssetStatus.DECOMMISSIONED.label, True, False, False, False, True, "dark"),
]

_ESSENTIAL_ASSET_TRANSITIONS = [
    (EssentialAssetStatus.IDENTIFIED.value, EssentialAssetStatus.ACTIVE.value, EssentialAssetStatus.ACTIVE.label),
    (EssentialAssetStatus.IDENTIFIED.value, EssentialAssetStatus.DECOMMISSIONED.value, EssentialAssetStatus.DECOMMISSIONED.label),
    (EssentialAssetStatus.ACTIVE.value, EssentialAssetStatus.UNDER_REVIEW.value, EssentialAssetStatus.UNDER_REVIEW.label),
    (EssentialAssetStatus.UNDER_REVIEW.value, EssentialAssetStatus.ACTIVE.value, EssentialAssetStatus.ACTIVE.label),
    (EssentialAssetStatus.UNDER_REVIEW.value, EssentialAssetStatus.DECOMMISSIONED.value, EssentialAssetStatus.DECOMMISSIONED.label),
    (EssentialAssetStatus.ACTIVE.value, EssentialAssetStatus.DECOMMISSIONED.value, EssentialAssetStatus.DECOMMISSIONED.label),
]

ESSENTIAL_ASSET_LIFECYCLE = register_lifecycle(
    lifecycle_from_state_flags(
        ESSENTIAL_ASSET_LIFECYCLE_NAME,
        _ESSENTIAL_ASSET_STEPS,
        _ESSENTIAL_ASSET_TRANSITIONS,
        layout="graph",
    )
)


# ── Support asset ───────────────────────────────────────────
#
# The IT-infrastructure lifecycle, ported from the legacy support_asset
# workflow. A support asset is created Active (the entry); In stock covers
# hardware received but not yet deployed; Active <-> Under maintenance is the
# operational cycle; Decommissioned then Disposed are the end of service
# (Disposed is the exit). Every stage stays in reports (decommissioned and
# disposed assets are audit history), terminal-bound stages are not linkable.

SUPPORT_ASSET_LIFECYCLE_NAME = "support_asset"

# The support-asset (IT infrastructure) lifecycle, authored as an explicit JSON
# document : a clean, mostly-linear procurement-to-disposal flow with a single
# maintenance loop and a single Archived exit. Draft is the entry, Archived the
# exit; every move between them is stated explicitly (no "from any state"
# shortcut), e.g. Decommissioned is reachable only from Active / Under
# maintenance. This is the reference example for the JSON-driven, admin-editable
# lifecycle framework - edit the ``support_asset`` row in Administration ->
# Lifecycles to re-shape it without touching code.
SUPPORT_ASSET_DEFINITION = {
    "layout": "graph",
    "steps": [
        {"code": "draft", "label": "Draft", "kind": "draft",
         "deletable": True, "tone": "neutral"},
        {"code": "in_stock", "label": "In stock", "kind": "intermediate",
         "counts_in_reports": True, "linkable": True, "deletable": True, "tone": "secondary"},
        {"code": "deployed", "label": "Deployed", "kind": "intermediate",
         "counts_in_reports": True, "linkable": True, "tone": "info"},
        {"code": "active", "label": "Active", "kind": "intermediate",
         "counts_in_reports": True, "linkable": True, "deletable": True, "tone": "success"},
        {"code": "under_maintenance", "label": "Under maintenance", "kind": "intermediate",
         "counts_in_reports": True, "linkable": True, "tone": "warning"},
        {"code": "decommissioned", "label": "Decommissioned", "kind": "intermediate",
         "counts_in_reports": True, "tone": "dark"},
        {"code": "disposed", "label": "Disposed", "kind": "intermediate",
         "counts_in_reports": True, "tone": "dark"},
        {"code": "archived", "label": "Archived", "kind": "archived", "tone": "muted"},
    ],
    "transitions": [
        {"source": "draft", "target": "in_stock", "label": "Receive"},
        {"source": "in_stock", "target": "deployed", "label": "Deploy"},
        {"source": "deployed", "target": "active", "label": "Commission"},
        {"source": "active", "target": "under_maintenance", "label": "Start maintenance"},
        {"source": "under_maintenance", "target": "active", "label": "Complete maintenance"},
        {"source": "active", "target": "decommissioned", "label": "Decommission"},
        {"source": "under_maintenance", "target": "decommissioned", "label": "Decommission"},
        {"source": "decommissioned", "target": "disposed", "label": "Dispose"},
        {"source": "disposed", "target": "archived", "label": "Archive"},
        {"source": "archived", "target": "draft", "label": "Restore"},
    ],
}

SUPPORT_ASSET_LIFECYCLE = register_lifecycle(
    lifecycle_from_json(SUPPORT_ASSET_LIFECYCLE_NAME, SUPPORT_ASSET_DEFINITION)
)
