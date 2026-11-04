# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""The three lifecycles of module 8 (controls), generated from the tables in
``controls/constants.py`` (single source of truth). Imported from
``ControlsConfig.ready()``; omitting the import fails silently, so the tests
assert each model resolves the lifecycle it declares."""

from controls.constants import (
    CONTROL_STATES,
    CONTROL_TRANSITIONS,
    RUN_STATES,
    RUN_TRANSITIONS,
    TEST_STATES,
    TEST_TRANSITIONS,
)
from core.lifecycle import lifecycle_from_state_flags, register_lifecycle

CONTROL_LIFECYCLE_NAME = "control"
TEST_LIFECYCLE_NAME = "control_test"
RUN_LIFECYCLE_NAME = "control_test_run"


def _register(name, states, transitions):
    return register_lifecycle(lifecycle_from_state_flags(name, states, transitions, layout="graph"))


CONTROL_LIFECYCLE = _register(CONTROL_LIFECYCLE_NAME, CONTROL_STATES, CONTROL_TRANSITIONS)
TEST_LIFECYCLE = _register(TEST_LIFECYCLE_NAME, TEST_STATES, TEST_TRANSITIONS)
RUN_LIFECYCLE = _register(RUN_LIFECYCLE_NAME, RUN_STATES, RUN_TRANSITIONS)
