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
    from accounts.constants import SYSTEM_GROUPS, get_all_permissions
    from accounts.models import Group, Permission

    with django_db_blocker.unblock():
        codename_to_perm = {}
        for codename, name, module, feature, action in get_all_permissions():
            perm, _ = Permission.objects.get_or_create(
                codename=codename,
                defaults={
                    "name": name,
                    "module": module,
                    "feature": feature,
                    "action": action,
                    "is_system": True,
                },
            )
            codename_to_perm[codename] = perm

        for group_name, group_def in SYSTEM_GROUPS.items():
            group, _ = Group.objects.get_or_create(
                name=group_name,
                defaults={
                    "description": str(group_def["description"]),
                    "is_system": True,
                },
            )
            matching = [
                perm
                for codename, perm in codename_to_perm.items()
                if group_def["filter"](codename)
            ]
            group.permissions.set(matching)
