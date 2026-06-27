"""Template tags rendering lifecycle workflow state for any element."""

from django import template

register = template.Library()

# Workflow State.tone -> Bootstrap badge context.
_TONE_CLASSES = {
    "neutral": "secondary",
    "muted": "secondary",
    "secondary": "secondary",
    "info": "info",
    "primary": "primary",
    "warning": "warning",
    "success": "success",
    "danger": "danger",
    "dark": "dark",
}


@register.inclusion_tag("includes/workflow_badge.html")
def workflow_badge(obj):
    """Render the lifecycle state badge of any lifecycle-bearing element.

    Engine-agnostic: the ``lifecycle_label`` / ``lifecycle_tone`` properties on
    ``BaseModel`` resolve the current state through whichever engine the model
    runs (the standardised ``core.lifecycle`` step when ``LIFECYCLE_NAME`` is
    set, otherwise the legacy ``core.workflow`` state), so a step like
    ``in_force`` renders with its proper label and tone instead of a raw code.
    """
    label = getattr(obj, "lifecycle_label", None)
    if label is None:
        return {"label": getattr(obj, "workflow_state", ""), "badge_class": "secondary"}
    tone = getattr(obj, "lifecycle_tone", "neutral")
    return {
        "label": label,
        "badge_class": _TONE_CLASSES.get(tone, "secondary"),
    }
