"""Keep the ``LifecycleDefinition`` table in sync with the code-declared lifecycles.

On every ``post_migrate`` we ensure a JSON row exists for each registered
lifecycle and refresh the JSON of *system* rows the admin has not customized, so
the database is the editable single source of truth while code changes to a
built-in default still flow through. Rows the admin has edited
(``is_customized``) are never overwritten.
"""

import logging

from django.db.models.signals import post_migrate
from django.dispatch import receiver

logger = logging.getLogger(__name__)


@receiver(post_migrate)
def sync_lifecycle_definitions(sender, **kwargs):
    # Run once, when the core app finishes migrating (every app's ready() has
    # already registered its lifecycles by then, so the registry is complete).
    if getattr(sender, "name", None) != "core":
        return
    try:
        from core.lifecycle import (
            LIFECYCLE_REGISTRY,
            clear_lifecycle_cache,
            lifecycle_to_json,
        )
        from core.models import LifecycleDefinition
    except Exception:
        return

    for name, lifecycle in list(LIFECYCLE_REGISTRY.items()):
        try:
            definition = lifecycle_to_json(lifecycle)
            label = name.replace("_", " ").capitalize()
            row = LifecycleDefinition.objects.filter(name=name).first()
            if row is None:
                LifecycleDefinition.objects.create(
                    name=name, label=label, definition=definition, is_system=True,
                )
            elif row.is_system and not row.is_customized and row.definition != definition:
                row.definition = definition
                row.save()
        except Exception:
            # DB not ready or a race during parallel test setup: skip quietly,
            # the engine falls back to the code default until the next migrate.
            logger.debug("Lifecycle sync skipped for %r", name, exc_info=True)
            return

    try:
        clear_lifecycle_cache()
    except Exception:
        pass
