"""Tests for the asset lifecycles (standardised core.lifecycle engine)."""

import pytest

from accounts.tests.factories import UserFactory
from assets.constants import EssentialAssetStatus, SupportAssetStatus
from assets.models import EssentialAsset, SupportAsset
from assets.tests.factories import EssentialAssetFactory, SupportAssetFactory
from core.lifecycle import IllegalTransitionError, get_lifecycle, resolve_lifecycle
from core.lifecycle import LifecycleProtectedError  # delete() guard (relocated at decommission)

pytestmark = pytest.mark.django_db


class TestEssentialAssetLifecycle:
    def test_model_resolves_to_specific_lifecycle(self):
        lifecycle = resolve_lifecycle(EssentialAsset)
        assert lifecycle.name == "essential_asset"
        # Generic Draft entry bookends every lifecycle.
        assert lifecycle.initial_step.code == "draft"

    def test_step_codes_match_status_values(self):
        lifecycle = resolve_lifecycle(EssentialAsset)
        assert {s.code for s in lifecycle.steps} == {
            s.value for s in EssentialAssetStatus
        } | {"draft", "archived"}

    def test_governance_flags(self):
        lifecycle = get_lifecycle("essential_asset")
        assert lifecycle.deletable_step_codes == {"draft", "identified"}
        assert lifecycle.linkable_step_codes == {"identified", "active", "under_review"}
        # Decommissioned assets stay in reports (audit history).
        assert lifecycle.reportable_step_codes == {s.value for s in EssentialAssetStatus}

    def test_creation_aligns_state(self):
        asset = EssentialAssetFactory()
        assert asset.workflow_state == asset.status == "draft"

    def test_lifecycle_path(self):
        user = UserFactory()
        asset = EssentialAssetFactory()
        asset.transition_to(EssentialAssetStatus.IDENTIFIED, user)  # leave Draft
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


class TestSupportAssetLifecycle:
    def test_model_resolves_to_specific_lifecycle(self):
        lifecycle = resolve_lifecycle(SupportAsset)
        assert lifecycle.name == "support_asset"
        # Generic Draft entry bookends every lifecycle.
        assert lifecycle.initial_step.code == "draft"

    def test_step_codes_match_status_values(self):
        lifecycle = resolve_lifecycle(SupportAsset)
        assert {s.code for s in lifecycle.steps} == {
            s.value for s in SupportAssetStatus
        } | {"draft", "archived"}

    def test_governance_flags(self):
        lifecycle = get_lifecycle("support_asset")
        assert lifecycle.deletable_step_codes == {"draft", "in_stock", "active"}
        # Consistent with RS-04: no new links on decommissioned / disposed.
        assert lifecycle.linkable_step_codes == {
            "in_stock", "deployed", "active", "under_maintenance",
        }
        assert lifecycle.reportable_step_codes == {s.value for s in SupportAssetStatus}

    def test_disposal_path(self):
        user = UserFactory()
        asset = SupportAssetFactory()  # draft
        # Clean procurement-to-disposal flow (explicit transitions).
        asset.transition_to(SupportAssetStatus.IN_STOCK, user)  # Receive
        asset.transition_to(SupportAssetStatus.DEPLOYED, user)  # Deploy
        asset.transition_to(SupportAssetStatus.ACTIVE, user)  # Commission
        asset.transition_to(SupportAssetStatus.UNDER_MAINTENANCE, user)
        asset.transition_to(SupportAssetStatus.ACTIVE, user)
        asset.transition_to(SupportAssetStatus.DECOMMISSIONED, user)
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
