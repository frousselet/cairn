"""Ask Cairn daily briefing: an LLM-synthesised summary of the day's key metrics.

The widget hands the backend a structured snapshot of the day's GRC metrics; the
backend asks the configured LLM (Mistral by default) to synthesise it into a short
briefing and renders what the model returns. It is fetched **asynchronously** by
the widget (a small endpoint the browser calls after the page has rendered), so
the dashboard never blocks on the LLM - a slow or unreachable provider can only
delay the briefing, never the page. Results are cached per user for a short window,
and shown with an honest "powered by <provider> <model>" note.
"""

import json
import logging

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

logger = logging.getLogger(__name__)

# Human labels for the active provider (mirrors assistant.views.PROVIDER_LABELS).
PROVIDER_LABELS = {
    "mistral": "Mistral",
    "openai": "OpenAI",
    "openai-compatible": "OpenAI",
    "ollama": "Ollama",
    "anthropic": "Anthropic",
    "claude": "Anthropic",
}

BRIEFING_PROMPT = (
    "You are the assistant of Cairn, a Governance, Risk and Compliance platform. "
    "You are given a JSON snapshot of today's GRC metrics for one organisation. "
    "Write a daily briefing for the security / compliance manager in {language}, "
    "in short, direct, complete sentences - concise, plain and factual, not "
    "verbose or literary. Output HTML using ONLY <p>, <b> and <strong> tags - no "
    "other HTML, no markdown, no lists. You may add an emoji sparingly to lighten "
    "the tone - at most ONE per paragraph - but only professional, inoffensive "
    "emojis with no sexual, ambiguous or otherwise inappropriate connotation in a "
    "workplace; when in doubt, use none. Place any emoji at the very START of its "
    "paragraph (right after the opening <p>, before any text or bold lead-in), "
    "never in the middle or at the end. "
    "When ongoing_audits is present, write TWO paragraphs. The first <p> is about "
    "the audit(s) under way: open it with a short bold lead-in in <b>...</b> that "
    "names the standards involved and that audits are in progress (for example "
    "'<b>Audits ISO 27001 et NIS2 en cours :</b>'), then, in plain text, describe "
    "each audit - the standards, the lead auditor (use the exact full name from "
    "lead_auditor) and what it covers, called its scope ('perimetre' in French): "
    "when its covers_entire_scope flag is true say it covers the entire scope, "
    "otherwise ALWAYS name the specific audited_scopes (e.g. 'couvre les perimetres "
    "Corporate IT et Industrial Operations'); never be vague with 'partially' or "
    "'a partial scope' - always say which scopes. Avoid repetition: when audits "
    "share the same lead auditor or standard, state it once for all of them. The "
    "second <p> covers the most critical items as a single flowing SENTENCE (for "
    "example 'Par ailleurs, il y a 2 risques critiques a traiter, 19 exigences non "
    "conformes et 1 plan d'action en retard'), not a terse comma-separated list, "
    "and with NO bold lead-in - the bold <b> lead-in is for the audit paragraph "
    "only. When there is no audit, write a single plain <p> with those items as one "
    "sentence (no bold lead-in). "
    "Name each item with its exact entity, never a vague word like 'point(s)': "
    "critical_risks_to_treat are critical RISKS (risques critiques), "
    "non_compliant_requirements are non-compliant REQUIREMENTS (exigences non "
    "conformes), overdue_action_plans are overdue ACTION PLANS (plans d'action en "
    "retard). These metrics are COUNTS ONLY: you do NOT have the individual names "
    "of the risks, requirements or plans, so state the figure with its entity and "
    "NEVER invent or enumerate individual names such as 'Risque critique 1 et "
    "Risque critique 2'. Use <b>/<strong> only for the audit lead-in, never "
    "anywhere else. Mention only the noteworthy, non-zero metrics and ignore the "
    "rest. Use "
    "the exact figures from the JSON and invent nothing - no figures, no names. "
    "Never state that there is no audit or that nothing is happening."
)


def provider_label():
    """Return the human label for the active backend, e.g. "Mistral"."""
    provider = (settings.AI_ASSISTANT_PROVIDER or "").lower()
    return PROVIDER_LABELS.get(provider, provider.title() or "AI")


# Bump when the prompt, the metrics snapshot or the result shape changes, so
# already-cached briefings are regenerated instead of served stale.
BRIEFING_CACHE_VERSION = "14"

# How long a generated briefing is cached in production (per user). Kept short so
# the briefing tracks the day's metrics as they change rather than freezing.
BRIEFING_CACHE_TTL = 60 * 15  # 15 minutes


def _cache_key(user, language):
    return (
        f"ask_cairn:briefing:{BRIEFING_CACHE_VERSION}:"
        f"{user.pk}:{timezone.localdate().isoformat()}:{language}"
    )


def get_or_generate_briefing(user, language, data):
    """Return the day's AI briefing ``{"text", "provider", "generated_at"}`` or ``None``.

    ``data`` is a dict of the day's GRC metrics. Cached per user for a short
    window (``BRIEFING_CACHE_TTL``); on a miss the LLM is called synchronously and
    the result cached. Returns ``None``
    when the assistant is disabled, there is no data, or generation fails (the
    caller then keeps the fallback). Meant to be called from the async briefing
    endpoint, never from the page render.
    """
    if not settings.AI_ASSISTANT_ENABLED or not data:
        return None
    # In dev (DEBUG) always regenerate: the briefing is being iterated on, so a
    # cache would mask prompt and snapshot changes. In production it is cached
    # briefly per user (BRIEFING_CACHE_TTL).
    use_cache = not settings.DEBUG
    key = _cache_key(user, language)
    if use_cache:
        hit = cache.get(key)
        if hit is not None:
            return hit
    try:
        text = _generate(language, data)
    except Exception:
        logger.exception("Ask Cairn briefing generation failed")
        return None
    if not text:
        return None
    result = {
        "text": text,
        "provider": provider_label(),
        "generated_at": timezone.now().isoformat(),
    }
    if use_cache:
        cache.set(key, result, BRIEFING_CACHE_TTL)
    return result


def _generate(language, data):
    from assistant.providers import get_client

    client = get_client()
    messages = [
        {"role": "system", "content": BRIEFING_PROMPT.format(language=language)},
        {"role": "user", "content": json.dumps(data, ensure_ascii=False)},
    ]
    return (client.chat_text(messages) or "").strip()
