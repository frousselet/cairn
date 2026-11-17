# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""Root pytest configuration.

Test settings disable migrations (`MIGRATION_MODULES = _DisableMigrations()`)
so Django creates the schema directly from current models. That bypasses the
~150 historical migrations and cuts test-suite startup by ~5-10x, but it also
skips data migrations that seed reference rows. This module rebuilds the
seed data once per session, after the schema exists.
"""

import pytest


@pytest.fixture(scope="session")
def django_db_setup(django_db_setup, django_db_blocker):
    """Seed permissions and system groups after schema creation."""
    from accounts.reference_data import sync_system_permissions

    with django_db_blocker.unblock():
        sync_system_permissions()
