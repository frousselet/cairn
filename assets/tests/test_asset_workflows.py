"""Tests for the asset specific workflows (issue #105, phase 6d)."""

import pytest

from accounts.tests.factories import UserFactory
from assets.constants import EssentialAssetStatus, SupportAssetStatus
from assets.models import EssentialAsset, SupportAsset
from assets.tests.factories import EssentialAssetFactory, SupportAssetFactory
from core.workflow import (
    IllegalTransitionError,
    LifecycleProtectedError,
    deletable_states,
    linkable_states,
    reportable_states,
    resolve_workflow,
)

pytestmark = pytest.mark.django_db


class TestEssentialAssetWorkflow:
    def test_model_resolves_to_specific_workflow(self):
        workflow = resolve_workflow(EssentialAsset)
        assert workflow.name == "essential_asset"
        assert workflow.initial_state.code == "identified"
        assert workflow.subsumes_approval is False

    def test_state_codes_match_status_values(self):
        workflow = resolve_workflow(EssentialAsset)
        assert {s.code for s in workflow.states} == {
            s.value for s in EssentialAssetStatus
        }

    def test_governance_flags(self):
        assert deletable_states(EssentialAsset) == {"identified"}
        assert linkable_states(EssentialAsset) == {
            "identified", "active", "under_review",
        }
        # Decommissioned assets stay in reports (audit history).
        assert reportable_states(EssentialAsset) == {
            s.value for s in EssentialAssetStatus
        }

    def test_creation_aligns_state(self):
        asset = EssentialAssetFactory()
        assert asset.workflow_state == asset.status == "identified"

    def test_lifecycle_path(self):
        user = UserFactory()
        asset = EssentialAssetFactory()
        asset.transition_to(EssentialAssetStatus.ACTIVE, user)
        asset.transition_to(EssentialAssetStatus.UNDER_REVIEW, user)
        asset.transition_to(EssentialAssetStatus.ACTIVE, user)
        asset.transition_to(EssentialAssetStatus.DECOMMISSIONED, user)
        asset.refresh_from_db()
        assert asset.status == "decommissioned"
        with pytest.raises(IllegalTransitionError):
            asset.transition_to(EssentialAssetStatus.ACTIVE, user)

    def test_decommissioned_not_linkable_nor_deletable(self):
        asset = EssentialAssetFactory(status=EssentialAssetStatus.DECOMMISSIONED)
        assert asset.is_linkable is False
        with pytest.raises(LifecycleProtectedError):
            asset.delete()

    def test_legacy_status_write_syncs(self):
        asset = EssentialAssetFactory()
        asset.status = EssentialAssetStatus.ACTIVE
        asset.save()
        asset.refresh_from_db()
        assert asset.workflow_state == "active"


class TestSupportAssetWorkflow:
    def test_model_resolves_to_specific_workflow(self):
        workflow = resolve_workflow(SupportAsset)
        assert workflow.name == "support_asset"
        assert workflow.initial_state.code == "active"  # model creation default

    def test_state_codes_match_status_values(self):
        workflow = resolve_workflow(SupportAsset)
        assert {s.code for s in workflow.states} == {
            s.value for s in SupportAssetStatus
        }

    def test_governance_flags(self):
        assert deletable_states(SupportAsset) == {"in_stock", "active"}
        # Consistent with RS-04: no new links on decommissioned / disposed.
        assert linkable_states(SupportAsset) == {
            "in_stock", "deployed", "active", "under_maintenance",
        }
        assert reportable_states(SupportAsset) == {
            s.value for s in SupportAssetStatus
        }

    def test_disposal_path(self):
        user = UserFactory()
        asset = SupportAssetFactory()  # active
        asset.transition_to(SupportAssetStatus.UNDER_MAINTENANCE, user)
        asset.transition_to(SupportAssetStatus.ACTIVE, user)
        asset.transition_to(SupportAssetStatus.DECOMMISSIONED, user)
        # Decommissioned is not terminal: disposal follows.
        asset.transition_to(SupportAssetStatus.DISPOSED, user)
        asset.refresh_from_db()
        assert asset.status == "disposed"
        with pytest.raises(IllegalTransitionError):
            asset.transition_to(SupportAssetStatus.ACTIVE, user)

    def test_terminal_disposed_not_deletable(self):
        asset = SupportAssetFactory(status=SupportAssetStatus.DISPOSED)
        with pytest.raises(LifecycleProtectedError):
            asset.delete()

    def test_active_asset_remains_deletable(self):
        """Creation default stays deletable (no behavior break for fresh assets)."""
        asset = SupportAssetFactory()  # active
        pk = asset.pk
        asset.delete()
        assert not SupportAsset.objects.filter(pk=pk).exists()

    def test_framework_write_syncs_to_status(self):
        asset = SupportAssetFactory()
        asset.workflow_state = "deployed"
        asset.save()
        asset.refresh_from_db()
        assert asset.status == "deployed"
