# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""The reference rows the application expects in an empty database.

On a deployment they are written by the data migrations. A database whose
schema is built straight from the models (the test suite, the throwaway
instance the accessibility audit runs against) never executes a migration :
this rebuilds the same rows from the registries in ``accounts/constants.py``.
"""


def sync_system_permissions():
    """Create every registered permission and the system groups holding them.

    Idempotent : an existing permission is left as it is, and a system group
    gets exactly the permissions its definition selects.
    """
    from accounts.constants import SYSTEM_GROUPS, get_all_permissions
    from accounts.models import Group, Permission

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
        group.permissions.set([
            perm for codename, perm in codename_to_perm.items() if group_def["filter"](codename)
        ])
