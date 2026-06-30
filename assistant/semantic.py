"""Semantic search helpers: embed-text building and in-Python cosine ranking.

The corpus here (a GRC instance's requirements) is small enough that a
brute-force cosine over stored embeddings is instant, so no vector database is
needed. Embeddings live in ``SemanticIndex`` as plain JSON lists, which keeps
the column portable across PostgreSQL and the SQLite test database.
"""

import logging
import math
import threading
import time

from django.conf import settings
from django.core.cache import cache
from django.db import connections
from django.db.models import Max
from django.utils.html import strip_tags

from assistant.models import SemanticIndex, content_hash
from assistant.providers import get_client

logger = logging.getLogger(__name__)

# Cache lock so concurrent triggers (startup hook + admin button + a double
# click) do not run overlapping rebuilds. Best-effort dedupe; the rebuild is
# idempotent anyway.
REBUILD_LOCK_KEY = "assistant:semantic:rebuild-lock"
REBUILD_LOCK_TTL = 1800  # seconds
# How often the startup rebuild re-probes readiness while the instance is still
# being set up (first-run onboarding: migrations running, no user yet).
READINESS_POLL_INTERVAL = 5  # seconds


def requirement_text(requirement):
    """Build the text embedded for a requirement (number, name, description)."""
    parts = [
        requirement.requirement_number or "",
        requirement.name or "",
        strip_tags(requirement.description or ""),
        strip_tags(requirement.guidance or ""),
    ]
    return "\n".join(p.strip() for p in parts if p and p.strip())


def cosine(a, b):
    """Cosine similarity between two equal-length vectors (0 if degenerate)."""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = na = nb = 0.0
    for x, y in zip(a, b):
        dot += x * y
        na += x * x
        nb += y * y
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (math.sqrt(na) * math.sqrt(nb))


def rank_object_ids(query_vector, content_type, limit):
    """Return up to ``limit`` object ids ranked by cosine to ``query_vector``."""
    scored = []
    rows = SemanticIndex.objects.filter(content_type=content_type).values_list(
        "object_id", "embedding"
    )
    for object_id, embedding in rows:
        score = cosine(query_vector, embedding)
        if score > 0:
            scored.append((score, object_id))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [object_id for _, object_id in scored[:limit]]


def embed_query(text):
    """Embed a single query string; returns the vector or None on failure."""
    vectors = get_client().embed([text])
    return vectors[0] if vectors else None


def upsert_embedding(content_type, obj, text, vector):
    """Create or update the SemanticIndex row for one object."""
    model = settings.AI_ASSISTANT_EMBED_MODEL
    SemanticIndex.objects.update_or_create(
        content_type=content_type,
        object_id=obj.pk,
        defaults={
            "text": text,
            "content_hash": content_hash(model, text),
            "embedding": vector,
            "model_name": model,
        },
    )


def rebuild_index(*, force=False, batch_size=32, progress=None):
    """Build or refresh the requirement semantic index (synchronous).

    Idempotent: only requirements whose text or embedding model changed are
    re-embedded (unless ``force``); embeddings of deleted requirements are
    pruned. ``progress`` (if given) is called as ``progress(done, total)`` after
    each batch. Returns ``{"embedded": int, "pruned": int}``. Raises
    ``AssistantError`` if the provider embedding call fails.
    """
    from compliance.models import Requirement

    batch_size = max(1, batch_size)
    model = settings.AI_ASSISTANT_EMBED_MODEL
    content_type = SemanticIndex.REQUIREMENT

    existing = dict(
        SemanticIndex.objects.filter(content_type=content_type).values_list(
            "object_id", "content_hash"
        )
    )
    pending, seen = [], set()
    for req in Requirement.objects.all().iterator():
        seen.add(req.pk)
        text = requirement_text(req)
        if not text:
            continue
        if not force and existing.get(req.pk) == content_hash(model, text):
            continue
        pending.append((req, text))

    stale_ids = set(existing) - seen
    if stale_ids:
        SemanticIndex.objects.filter(
            content_type=content_type, object_id__in=stale_ids
        ).delete()

    client = get_client()
    done = 0
    for start in range(0, len(pending), batch_size):
        chunk = pending[start:start + batch_size]
        vectors = client.embed([text for _, text in chunk])
        for (obj, text), vector in zip(chunk, vectors):
            upsert_embedding(content_type, obj, text, vector)
            done += 1
        if progress is not None:
            progress(done, len(pending))
    return {"embedded": done, "pruned": len(stale_ids)}


def rebuild_index_async(*, force=False):
    """Run :func:`rebuild_index` once in a guarded background daemon thread.

    Returns True if a rebuild was started, False if semantic search is off or a
    rebuild is already running (the cache lock dedupes the startup hook, the
    admin button and accidental double triggers). All failures are logged inside
    the thread, never raised to the caller.
    """
    if not settings.AI_ASSISTANT_SEMANTIC_ENABLED:
        return False
    if not cache.add(REBUILD_LOCK_KEY, "1", REBUILD_LOCK_TTL):
        return False

    def _worker():
        try:
            result = rebuild_index(force=force)
            logger.info(
                "Semantic index rebuilt: %(embedded)s embedded, %(pruned)s pruned",
                result,
            )
        except Exception:
            logger.exception("Semantic index rebuild failed")
        finally:
            cache.delete(REBUILD_LOCK_KEY)
            # A worker thread owns its own DB connections; close them so they
            # are not leaked back to the pool.
            connections.close_all()

    threading.Thread(target=_worker, name="semantic-rebuild", daemon=True).start()
    return True


def rebuild_index_on_startup():
    """Background rebuild for the server boot hook, deferred until the instance
    is ready.

    On a fresh database the first-run migrations have not created the index or
    requirement tables yet (and the migration may still be running during
    onboarding), so the worker waits until the schema is migrated and the
    instance is initialised before touching the ORM. The rebuild lock is acquired
    only once that point is reached, so it is not held during the wait. A
    brand-new instance has no requirements to index, so this is effectively a
    no-op until real content exists.

    Returns True if the deferred rebuild thread was started, False if semantic
    search is disabled.
    """
    if not settings.AI_ASSISTANT_SEMANTIC_ENABLED:
        return False

    def _worker():
        from core.onboarding import runner
        from core.onboarding.state import instance_ready

        try:
            # Wait for the schema and the first user. While an onboarding
            # migration or seed is in flight, stay off the database entirely (no
            # readiness probe): on SQLite a stray read contends with the job's
            # write lock and stalls it.
            while runner.is_running() or not instance_ready():
                connections.close_all()
                time.sleep(READINESS_POLL_INTERVAL)
            if not cache.add(REBUILD_LOCK_KEY, "1", REBUILD_LOCK_TTL):
                return
            try:
                result = rebuild_index(force=False)
                logger.info(
                    "Semantic index rebuilt: %(embedded)s embedded, %(pruned)s pruned",
                    result,
                )
            finally:
                cache.delete(REBUILD_LOCK_KEY)
        except Exception:
            logger.exception("Semantic index rebuild failed")
        finally:
            # A worker thread owns its own DB connections; close them so they
            # are not leaked back to the pool.
            connections.close_all()

    threading.Thread(target=_worker, name="semantic-rebuild", daemon=True).start()
    return True


def index_status():
    """Snapshot for the admin UI: feature state, counts, freshness, capability."""
    from compliance.models import Requirement

    provider = (settings.AI_ASSISTANT_PROVIDER or "mistral").lower()
    rows = SemanticIndex.objects.filter(content_type=SemanticIndex.REQUIREMENT)
    return {
        "enabled": settings.AI_ASSISTANT_SEMANTIC_ENABLED,
        "embeddings_supported": provider not in ("anthropic", "claude"),
        "embed_model": settings.AI_ASSISTANT_EMBED_MODEL,
        "indexed": rows.count(),
        "total": Requirement.objects.count(),
        "last_updated": rows.aggregate(Max("updated_at"))["updated_at__max"],
        "running": cache.get(REBUILD_LOCK_KEY) is not None,
    }
