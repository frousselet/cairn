# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""The three lifecycles of module 7 (documents), generated from the tables in
``documents/constants.py`` (single source of truth). Imported from
``DocumentsConfig.ready()``; omitting the import fails silently, so the tests
assert each model resolves the lifecycle it declares."""

from core.lifecycle import lifecycle_from_state_flags, register_lifecycle
from documents.constants import (
    CAMPAIGN_STATES,
    CAMPAIGN_TRANSITIONS,
    POLICY_STATES,
    POLICY_TRANSITIONS,
    VERSION_STATES,
    VERSION_TRANSITIONS,
)

POLICY_LIFECYCLE_NAME = "policy"
VERSION_LIFECYCLE_NAME = "policy_version"
CAMPAIGN_LIFECYCLE_NAME = "acknowledgement_campaign"


def _register(name, states, transitions):
    return register_lifecycle(lifecycle_from_state_flags(name, states, transitions, layout="graph"))


POLICY_LIFECYCLE = _register(POLICY_LIFECYCLE_NAME, POLICY_STATES, POLICY_TRANSITIONS)
VERSION_LIFECYCLE = _register(VERSION_LIFECYCLE_NAME, VERSION_STATES, VERSION_TRANSITIONS)
CAMPAIGN_LIFECYCLE = _register(CAMPAIGN_LIFECYCLE_NAME, CAMPAIGN_STATES, CAMPAIGN_TRANSITIONS)
