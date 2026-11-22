# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""A lifecycle transition asks for the permission to change the record.

A transition names the permission it needs (``permission_action``), or the
roles and users it is restricted to. Twenty-two lifecycles declared neither on
any of their transitions, and such a transition was "open" : allowed to anyone
who could reach the record. On the generic transition endpoint, which checks
nothing else, and on the MCP transition tools, which ask for the read
permission only, a reader (or a user with no permission on the module at all)
could put a scope in force, activate an asset or accept a risk.

``core.lifecycle.user_can_perform`` now treats an undeclared transition as a
change of the record : it asks for ``.update`` (or ``.approve``, which implies
it) on the entity.

A second family : a verdict kept for a stricter permission (validating an
EBIOS RM workshop, validating or closing an action plan, closing a management
review) that only the dedicated view, REST action or MCP tool asked for. The
lifecycle named nothing, so the generic endpoint and the generic MCP tools
performed the same move for whoever could edit the record. Each of these
lifecycles now names the permission of its gated transitions, and a state an
MCP tool writes directly is held to it as well.
"""

import pytest
from django.apps import apps
from django.urls import reverse

from accounts.models import Permission
from accounts.tests.factories import GroupFactory, UserFactory
from assets.tests.factories import EssentialAssetFactory
from context.models.base import BaseModel
from context.tests.factories import ScopeFactory
from core.lifecycle import (
    DEFAULT_PERMISSION_ACTIONS,
    Transition,
    resolve_lifecycle,
    user_can_perform,
)

pytestmark = pytest.mark.django_db

#: Models whose transitions ask for a permission that does not exist, known
#: and reported to the maintainer : only a superuser can move them until their
#: model names its permission feature (or the feature gains the action).
LOCKED_FOR_NOW = {
    "context.SwotAnalysis": "its feature is context.swot",
    "assets.AssetGroup": "its feature is assets.group",
    "compliance.Finding": "compliance.finding has no approve action for the default lifecycle's validation",
    "risks.RiskCriteria": "its feature is risks.criteria",
    "risks.ISO27005Risk": "its feature is risks.iso27005",
}


def _user_with(*codenames):
    """A user of an unrestricted group holding exactly these permissions."""
    user = UserFactory(is_superuser=False)
    group = GroupFactory()
    group.permissions.set(Permission.objects.filter(codename__in=codenames))
    group.users.add(user)
    return user


def _complete_scope(**kwargs):
    scope = ScopeFactory(boundaries="No exclusion.", **kwargs)
    scope.managers.add(UserFactory())
    return scope


class TestTheRule:
    def test_an_undeclared_transition_asks_for_update_or_approve(self):
        scope = ScopeFactory()
        move = resolve_lifecycle(scope).find_transition("draft", "definition")
        assert move.permission_action == "" and not move.is_restricted

        assert not user_can_perform(move, scope, _user_with())
        assert not user_can_perform(move, scope, _user_with("context.scope.read"))
        # The permission of another module is not the one asked for.
        assert not user_can_perform(move, scope, _user_with("assets.essential_asset.update"))
        assert user_can_perform(move, scope, _user_with("context.scope.update"))
        assert user_can_perform(move, scope, _user_with("context.scope.approve"))
        assert user_can_perform(move, scope, UserFactory(is_superuser=True))
        assert DEFAULT_PERMISSION_ACTIONS == ("update", "approve")

    def test_a_declared_permission_is_the_one_asked_for(self):
        scope = ScopeFactory()
        move = Transition("in_force", source="validation", permission_action="approve")

        assert not user_can_perform(move, scope, _user_with("context.scope.update"))
        assert user_can_perform(move, scope, _user_with("context.scope.approve"))

    def test_a_restriction_to_users_still_decides_alone(self):
        """The owner named by a restricted transition needs no other permission."""
        scope = ScopeFactory()
        owner = _user_with()
        move = Transition("in_force", source="validation", allowed_users=lambda instance: [owner])

        assert user_can_perform(move, scope, owner)
        assert not user_can_perform(move, scope, _user_with("context.scope.update"))

    def test_nobody_is_not_a_user(self):
        scope = ScopeFactory()
        move = resolve_lifecycle(scope).find_transition("draft", "definition")

        assert not user_can_perform(move, scope, None)

    def test_every_entity_can_still_be_moved_by_who_may_change_it(self):
        """The rule must lock nobody out : for each model whose lifecycle has an
        undeclared transition, the permission it now asks for exists."""
        from accounts.constants import PERMISSION_REGISTRY

        codenames = {
            f"{module}.{feature}.{action}"
            for module, features in PERMISSION_REGISTRY.items()
            for feature, spec in features.items()
            for action in spec.get("actions", [])
        }
        locked = []
        for model in apps.get_models():
            if not (isinstance(model, type) and issubclass(model, BaseModel)):
                continue
            lifecycle = resolve_lifecycle(model)
            if not any(not t.permission_action and not t.is_restricted for t in lifecycle.transitions):
                continue
            namespace = model().workflow_perm_namespace
            if not any(f"{namespace}.{action}" in codenames for action in DEFAULT_PERMISSION_ACTIONS):
                locked.append(f"{model._meta.label} ({namespace})")
        assert locked == []

    def test_every_transition_asks_for_a_permission_that_exists(self):
        """The permission a transition names is built on the model's
        ``workflow_perm_namespace``, derived from its name unless it says
        otherwise. Nine rows of an EBIOS RM workshop asked theirs of a feature
        that does not exist (``risks.fearedevent``) : only a superuser could
        move them. The test above reads the transitions that name nothing;
        this one reads them all."""
        from accounts.constants import PERMISSION_REGISTRY

        codenames = {
            f"{module}.{feature}.{action}"
            for module, features in PERMISSION_REGISTRY.items()
            for feature, spec in features.items()
            for action in spec.get("actions", [])
        }
        locked, seen = [], set()
        for model in apps.get_models():
            if not (isinstance(model, type) and issubclass(model, BaseModel)) or model.__name__.startswith("Historical"):
                continue
            namespace = model().workflow_perm_namespace
            asked = {t.permission_action or "update" for t in resolve_lifecycle(model).transitions if not t.is_restricted}
            missing = sorted(
                action for action in asked
                if f"{namespace}.{action}" not in codenames
                and not (action == "update" and f"{namespace}.approve" in codenames)
            )
            if not missing:
                continue
            if model._meta.label in LOCKED_FOR_NOW:
                seen.add(model._meta.label)
                continue
            locked.append(f"{model._meta.label} asks {namespace}.{'/'.join(missing)}")
        assert locked == [], "Name the permission feature of the model (workflow_perm_namespace) :\n" + "\n".join(locked)
        assert set(LOCKED_FOR_NOW) <= seen, f"No longer locked, take them off the list : {sorted(set(LOCKED_FOR_NOW) - seen)}"


class TestTheGenericEndpoint:
    def _url(self, obj):
        return reverse(
            "workflow:transition",
            kwargs={"app_label": obj._meta.app_label, "model": obj._meta.model_name, "pk": obj.pk},
        )

    def test_a_user_with_no_permission_on_scopes_cannot_put_one_in_force(self, client):
        scope = _complete_scope(workflow_state="validation")
        client.force_login(_user_with("assets.essential_asset.read"))

        client.post(self._url(scope), {"target_status": "in_force"})

        scope.refresh_from_db()
        assert scope.workflow_state == "validation"

    def test_a_reader_cannot_move_nor_archive_a_scope(self, client):
        scope = _complete_scope()
        client.force_login(_user_with("context.scope.read"))

        for target in ("definition", "archived"):
            client.post(self._url(scope), {"target_status": target})
            scope.refresh_from_db()
            assert scope.workflow_state == "draft"

    def test_a_reader_cannot_activate_an_asset(self, client):
        asset = EssentialAssetFactory(workflow_state="identified")
        client.force_login(_user_with("assets.essential_asset.read"))

        client.post(self._url(asset), {"target_status": "active"})

        asset.refresh_from_db()
        assert asset.workflow_state == "identified"

    def test_who_may_change_the_record_moves_it(self, client):
        scope = _complete_scope()
        client.force_login(_user_with("context.scope.read", "context.scope.update"))

        client.post(self._url(scope), {"target_status": "definition"})

        scope.refresh_from_db()
        assert scope.workflow_state == "definition"


class TestTheOtherSurfaces:
    def test_the_lifecycle_bar_offers_a_reader_no_move(self, client):
        scope = _complete_scope()
        client.force_login(_user_with("context.scope.read"))

        response = client.get(reverse("context:scope-detail", kwargs={"pk": scope.pk}))

        assert response.status_code == 200
        # No step of the bar is a button : the reader sees the path, not a move.
        assert "lc-step--action" not in response.content.decode()

    def test_the_lifecycle_bar_offers_an_editor_the_next_step(self, client):
        scope = _complete_scope()
        client.force_login(_user_with("context.scope.read", "context.scope.update"))

        html = client.get(reverse("context:scope-detail", kwargs={"pk": scope.pk})).content.decode()

        assert "lc-step--action" in html
        assert 'name="target_status" value="definition"' in html

    def test_the_mcp_transition_tool_refuses_a_reader(self):
        """The tool is registered with the read permission : the move itself asks more."""
        from mcp.tools import _transition_handler

        scope = _complete_scope()
        reader = _user_with("context.scope.read")

        result = _transition_handler(type(scope), "context.scope")(
            reader, {"id": str(scope.pk), "target_state": "definition"},
        )

        scope.refresh_from_db()
        assert scope.workflow_state == "draft"
        assert "error" in str(result).lower() or "not" in str(result).lower()

    def test_the_mcp_tool_lists_a_reader_no_move(self):
        from mcp.tools import _allowed_transitions_handler

        scope = _complete_scope()

        listed = _allowed_transitions_handler(type(scope), "context.scope")(
            _user_with("context.scope.read"), {"id": str(scope.pk)},
        )

        assert not listed.get("transitions")

    def test_the_rest_api_refuses_a_reader(self):
        from rest_framework.test import APIClient

        scope = _complete_scope()
        api = APIClient()
        api.force_authenticate(_user_with("context.scope.read"))

        response = api.post(
            f"/api/v1/context/scopes/{scope.pk}/transition/", {"target_state": "definition"}, format="json",
        )

        scope.refresh_from_db()
        assert response.status_code == 403
        assert scope.workflow_state == "draft"


class TestAVerdictAsksForItsOwnPermission:
    """What one surface asked for alone is asked for wherever the move is made."""

    def _url(self, obj):
        return reverse(
            "workflow:transition",
            kwargs={"app_label": obj._meta.app_label, "model": obj._meta.model_name, "pk": obj.pk},
        )

    def _workshop(self, state="under_review"):
        """Workshop 1 of a study, with the deliverables its validation waits for :
        what is tested here is who may give the verdict, not what the workshop lacks."""
        from assets.tests.factories import SupportAssetFactory
        from risks.tests.factories import EbiosAssessmentFactory, FearedEventFactory

        assessment = EbiosAssessmentFactory()
        baseline = assessment.ebios_security_baseline
        event = FearedEventFactory(baseline=baseline)
        baseline.essential_assets.add(event.essential_asset)
        baseline.support_assets.add(SupportAssetFactory())
        workshop = assessment.ebios_workshops.get(workshop_number=1)
        type(workshop).objects.filter(pk=workshop.pk).update(workflow_state=state)
        workshop.refresh_from_db()
        return workshop

    # ── The lifecycles name it ──────────────────────────────────────────────

    def test_the_action_plan_lifecycle_names_what_its_table_asks_for(self):
        from compliance.constants import (
            ACTION_PLAN_CANCELLABLE_STATUSES,
            ACTION_PLAN_TRANSITION_PERMISSIONS,
            ActionPlanStatus,
        )
        from compliance.models import ComplianceActionPlan

        lifecycle = resolve_lifecycle(ComplianceActionPlan)

        for (source, target), codename in ACTION_PLAN_TRANSITION_PERMISSIONS.items():
            transition = lifecycle.find_transition(source.value, target.value)
            assert transition is not None, f"{source} -> {target} is not a transition"
            assert f"compliance.action_plan.{transition.permission_action}" == codename
        for source in ACTION_PLAN_CANCELLABLE_STATUSES:
            transition = lifecycle.find_transition(source.value, ActionPlanStatus.CANCELLED.value)
            assert transition.permission_action == "cancel"

    def test_the_verdict_of_a_workshop_and_the_closure_of_a_review_are_named(self):
        from reports.models import ManagementReview
        from risks.models import EbiosWorkshopProgress

        workshop = resolve_lifecycle(EbiosWorkshopProgress)
        review = resolve_lifecycle(ManagementReview)

        assert workshop.find_transition("under_review", "validated").permission_action == "validate"
        assert workshop.find_transition("under_review", "rejected").permission_action == "validate"
        assert review.find_transition("held", "closed").permission_action == "approve"
        # Conducting the workshop and preparing the review stay with who may edit them.
        assert workshop.find_transition("in_progress", "under_review").permission_action == ""
        assert review.find_transition("in_preparation", "held").permission_action == ""

    # ── The generic endpoint ────────────────────────────────────────────────

    @pytest.mark.parametrize("target", ["validated", "rejected"])
    def test_who_conducts_an_ebios_workshop_does_not_give_its_verdict(self, client, target):
        workshop = self._workshop()
        client.force_login(_user_with("risks.ebios_assessment.read", "risks.ebios_assessment.update"))

        client.post(self._url(workshop), {"target_status": target, "comment": "Reviewed."})

        workshop.refresh_from_db()
        assert workshop.workflow_state == "under_review"

    def test_who_may_validate_the_study_gives_the_verdict(self, client):
        workshop = self._workshop()
        client.force_login(_user_with(
            "risks.ebios_assessment.read", "risks.ebios_assessment.update", "risks.ebios_assessment.validate",
        ))

        client.post(self._url(workshop), {"target_status": "validated"})

        workshop.refresh_from_db()
        assert workshop.workflow_state == "validated"

    @pytest.mark.parametrize("state, target", [
        ("to_validate", "to_implement"),
        ("to_implement", "implementation_to_validate"),
        ("implementation_to_validate", "validated"),
        ("validated", "closed"),
        ("to_define", "cancelled"),
    ])
    def test_who_edits_an_action_plan_does_not_validate_implement_close_or_cancel_it(self, client, state, target):
        from compliance.tests.factories import ComplianceActionPlanFactory

        plan = ComplianceActionPlanFactory()
        type(plan).objects.filter(pk=plan.pk).update(workflow_state=state)
        client.force_login(_user_with("compliance.action_plan.read", "compliance.action_plan.update"))

        client.post(self._url(plan), {"target_status": target, "comment": "Done."})

        plan.refresh_from_db()
        assert plan.workflow_state == state

    def test_who_may_validate_an_action_plan_still_does(self, client):
        from compliance.tests.factories import ComplianceActionPlanFactory

        plan = ComplianceActionPlanFactory()
        type(plan).objects.filter(pk=plan.pk).update(workflow_state="to_validate")
        client.force_login(_user_with(
            "compliance.action_plan.read", "compliance.action_plan.update", "compliance.action_plan.validate",
        ))

        client.post(self._url(plan), {"target_status": "to_implement"})

        plan.refresh_from_db()
        assert plan.workflow_state == "to_implement"

    def test_who_prepares_a_management_review_does_not_close_it(self, client):
        from reports.tests.factories import ManagementReviewFactory

        review = ManagementReviewFactory()
        type(review).objects.filter(pk=review.pk).update(workflow_state="held")
        client.force_login(_user_with("reports.management_review.read", "reports.management_review.update"))

        client.post(self._url(review), {"target_status": "closed"})

        review.refresh_from_db()
        assert review.workflow_state == "held"

    # ── The MCP server ──────────────────────────────────────────────────────

    def test_the_generic_mcp_tool_refuses_to_validate_an_action_plan(self):
        from compliance.tests.factories import ComplianceActionPlanFactory
        from mcp.tools import _transition_handler

        plan = ComplianceActionPlanFactory()
        type(plan).objects.filter(pk=plan.pk).update(workflow_state="to_validate")
        editor = _user_with("compliance.action_plan.read", "compliance.action_plan.update")

        _transition_handler(type(plan), "compliance.action_plan")(
            editor, {"id": str(plan.pk), "target_state": "to_implement"},
        )

        plan.refresh_from_db()
        assert plan.workflow_state == "to_validate"

    @pytest.mark.parametrize("state, written", [
        ("under_review", "validated"),
        ("under_review", "rejected"),
        # No transition leads from "not started" to "validated" : the write is
        # a jump, and every transition into the step asks for the permission.
        ("not_started", "validated"),
    ])
    def test_a_verdict_written_as_a_field_is_refused_all_the_same(self, state, written):
        """``status`` is a plain argument of the update tool : it was written
        without a word to whoever held ``update``."""
        from mcp.tools import _update_handler

        workshop = self._workshop(state)
        editor = _user_with("risks.ebios_assessment.read", "risks.ebios_assessment.update")

        result = _update_handler(type(workshop), ["status", "notes"])(
            editor, {"id": str(workshop.pk), "status": written, "notes": "Looks fine to me."},
        )

        workshop.refresh_from_db()
        assert workshop.workflow_state == state
        # The refusal rolls the whole write back, the other fields included.
        assert workshop.notes == ""
        assert "not allowed" in str(result)

    def test_a_workshop_is_not_created_already_validated(self):
        from mcp.tools import _create_handler
        from risks.models import EbiosWorkshopProgress
        from risks.tests.factories import EbiosAssessmentFactory

        assessment = EbiosAssessmentFactory()
        editor = _user_with("risks.ebios_assessment.read", "risks.ebios_assessment.update")
        before = EbiosWorkshopProgress.objects.count()

        result = _create_handler(
            EbiosWorkshopProgress, ["assessment_id", "workshop_number", "iteration_number", "status"],
        )(editor, {
            "assessment_id": str(assessment.pk), "workshop_number": 4, "iteration_number": 2, "status": "validated",
        })

        assert EbiosWorkshopProgress.objects.count() == before
        assert "not allowed" in str(result)

    def test_a_step_an_ordinary_transition_leads_to_is_still_written(self):
        from mcp.tools import _update_handler

        workshop = self._workshop("not_started")
        editor = _user_with("risks.ebios_assessment.read", "risks.ebios_assessment.update")

        _update_handler(type(workshop), ["status"])(editor, {"id": str(workshop.pk), "status": "in_progress"})

        workshop.refresh_from_db()
        assert workshop.workflow_state == "in_progress"

    def test_who_may_validate_writes_the_verdict(self):
        from mcp.tools import _update_handler

        workshop = self._workshop()
        validator = _user_with(
            "risks.ebios_assessment.read", "risks.ebios_assessment.update", "risks.ebios_assessment.validate",
        )

        _update_handler(type(workshop), ["status"])(validator, {"id": str(workshop.pk), "status": "validated"})

        workshop.refresh_from_db()
        assert workshop.workflow_state == "validated"


class TestACommitmentAsksForApproval:
    """Accepting a risk and putting a scope in force commit the organization.

    Both asked for the permission to change the record only : the person who
    drafted the acceptance or the perimeter could put it in force alone. They
    ask for ``approve`` now, held by the RSSI / DPO and the administrators,
    not by a contributor (``accounts.constants.SYSTEM_GROUPS``).
    """

    def _url(self, obj):
        return reverse(
            "workflow:transition",
            kwargs={"app_label": obj._meta.app_label, "model": obj._meta.model_name, "pk": obj.pk},
        )

    def _draft_acceptance(self):
        from risks.tests.factories import RiskAcceptanceFactory

        return RiskAcceptanceFactory(status="draft")

    def test_the_lifecycles_name_the_approve_permission(self):
        from context.models import Scope
        from risks.models import RiskAcceptance

        assert resolve_lifecycle(Scope).find_transition("validation", "in_force").permission_action == "approve"
        assert resolve_lifecycle(RiskAcceptance).find_transition("draft", "active").permission_action == "approve"
        # The other moves stay with who may change the record.
        assert resolve_lifecycle(Scope).find_transition("definition", "validation").permission_action == ""
        assert resolve_lifecycle(RiskAcceptance).find_transition("active", "revoked").permission_action == ""

    def test_a_contributor_holds_update_but_not_approve(self):
        from accounts.constants import SYSTEM_GROUPS

        contributor = SYSTEM_GROUPS["Contributeur"]["filter"]
        steering = SYSTEM_GROUPS["RSSI / DPO"]["filter"]
        for codename in ("context.scope.approve", "risks.acceptance.approve"):
            assert not contributor(codename) and steering(codename)
        assert contributor("context.scope.update") and contributor("risks.acceptance.update")

    def test_who_drafts_a_scope_does_not_put_it_in_force(self, client):
        scope = _complete_scope(workflow_state="validation")
        client.force_login(_user_with("context.scope.read", "context.scope.update"))

        client.post(self._url(scope), {"target_status": "in_force"})

        scope.refresh_from_db()
        assert scope.workflow_state == "validation"

    def test_who_may_approve_puts_a_scope_in_force(self, client):
        scope = _complete_scope(workflow_state="validation")
        client.force_login(_user_with("context.scope.read", "context.scope.update", "context.scope.approve"))

        client.post(self._url(scope), {"target_status": "in_force"})

        scope.refresh_from_db()
        assert scope.workflow_state == "in_force"

    def test_who_drafts_an_acceptance_does_not_accept_the_risk(self, client):
        acceptance = self._draft_acceptance()
        client.force_login(_user_with("risks.acceptance.read", "risks.acceptance.update"))

        client.post(self._url(acceptance), {"target_status": "active"})

        acceptance.refresh_from_db()
        assert acceptance.workflow_state == "draft"

    def test_who_may_approve_accepts_the_risk(self, client):
        acceptance = self._draft_acceptance()
        client.force_login(_user_with("risks.acceptance.read", "risks.acceptance.update", "risks.acceptance.approve"))

        client.post(self._url(acceptance), {"target_status": "active"})

        acceptance.refresh_from_db()
        assert acceptance.workflow_state == "active"

    def test_an_acceptance_is_not_created_already_active_through_mcp(self):
        from mcp.tools import _create_handler
        from risks.models import RiskAcceptance
        from risks.tests.factories import RiskFactory

        risk = RiskFactory()
        editor = _user_with("risks.acceptance.read", "risks.acceptance.create", "risks.acceptance.update",
                            "risks.risk.read")
        before = RiskAcceptance.objects.count()

        result = _create_handler(RiskAcceptance, ["risk_id", "justification", "status"])(
            editor, {"risk_id": str(risk.pk), "justification": "Residual risk within appetite.", "status": "active"},
        )

        assert RiskAcceptance.objects.count() == before
        assert "not allowed" in str(result)

    def test_the_lifecycle_bar_offers_put_in_force_to_who_may_approve_only(self, client):
        scope = _complete_scope(workflow_state="validation")
        url = scope.get_absolute_url()

        client.force_login(_user_with("context.scope.read", "context.scope.update"))
        drafter_page = client.get(url).content.decode()
        client.force_login(_user_with("context.scope.read", "context.scope.update", "context.scope.approve"))
        approver_page = client.get(url).content.decode()

        assert 'value="in_force"' not in drafter_page
        assert 'value="in_force"' in approver_page
