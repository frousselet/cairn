from django import template

register = template.Library()


@register.filter
def initials(name):
    """Return up to two uppercase initials extracted from a display name.

    Examples::

        "François Rousselet" -> "FR"
        "François"           -> "F"
        "alice"              -> "A"
        ""                   -> "?"

    Replaces the buggy ``{{ name|truncatechars:1 }}`` pattern, which always
    rendered ``...`` because Django's truncatechars counts the marker in
    the length budget.
    """
    parts = [p for p in (name or "").split() if p]
    if not parts:
        return "?"
    if len(parts) == 1:
        return parts[0][0].upper()
    return (parts[0][0] + parts[-1][0]).upper()


@register.simple_tag(takes_context=True)
def has_perm(context, codename):
    """
    Usage: {% has_perm "system.users.read" as can_view_users %}
    Returns True if the current user has the given permission.
    """
    request = context.get("request")
    if request and hasattr(request, "user") and request.user.is_authenticated:
        return request.user.has_perm(codename)
    return False


@register.simple_tag(takes_context=True)
def has_module_perms(context, module):
    """
    Usage: {% has_module_perms "system" as can_admin %}
    Returns True if the user has any permission for the given module.
    """
    request = context.get("request")
    if request and hasattr(request, "user") and request.user.is_authenticated:
        return request.user.has_module_perms(module)
    return False


@register.inclusion_tag("includes/user_badge.html")
def user_badge(user, size=28, link=False, name=True, block=False):
    """Render a user avatar + display name badge.

    Usage:
        {% load accounts_tags %}
        {% user_badge some_user %}
        {% user_badge some_user size=32 link=True %}
        {% user_badge some_user size=24 name=False %}

    Parameters:
        user  - User instance (required)
        size  - Avatar diameter in px (default 28)
        link  - Render name as link to user detail (default False)
        name  - Show display name next to avatar (default True)
        block - Use d-flex instead of d-inline-flex (default False)
    """
    size = int(size)
    if size >= 48:
        font_size = "1.125rem"
    elif size >= 32:
        font_size = ".75rem"
    else:
        font_size = ".625rem"

    avatar_src = ""
    if user and user.avatar:
        if size > 32:
            avatar_src = user.avatar_64 or user.avatar
        elif size > 16:
            avatar_src = user.avatar_32 or user.avatar
        else:
            avatar_src = user.avatar_16 or user.avatar

    initial = initials(user.display_name if user else "")

    return {
        "u": user,
        "sz": size,
        "avatar_src": avatar_src,
        "font_size": font_size,
        "initial": initial,
        "show_name": name,
        "link": link,
        "block": block,
    }


def _avatar_src(user, size):
    """Pick the best avatar rendition for a given diameter (px)."""
    if not (user and user.avatar):
        return ""
    if size > 32:
        return user.avatar_64 or user.avatar
    if size > 16:
        return user.avatar_32 or user.avatar
    return user.avatar_16 or user.avatar


@register.inclusion_tag("includes/user_avatars.html")
def user_avatars(users, size=24, max=5, link=False):
    """Render a compact, overlapping stack of round user avatars (no names).

    Avatars overlap slightly; each carries the user's name as a tooltip. When
    there are more users than ``max``, a trailing ``+N`` chip is shown. Renders
    a muted ``-`` placeholder when there is no user.

    Usage:
        {% load accounts_tags %}
        {% user_avatars scope.managers.all %}
        {% user_avatars ap.assignees.all size=20 max=4 %}
        {% user_avatars scope.managers.all link=True %}

    Parameters:
        users - iterable of User instances (required)
        size  - Avatar diameter in px (default 24)
        max   - Max avatars shown before a "+N" chip (default 5, 0 = no limit)
        link  - Link each avatar to the user detail page (default False)
    """
    size = int(size)
    max = int(max)
    if size >= 48:
        font_size = "1rem"
    elif size >= 32:
        font_size = ".6875rem"
    elif size >= 24:
        font_size = ".5625rem"
    else:
        font_size = ".5rem"

    users = [u for u in (users or []) if u]
    shown = users[:max] if max else users
    overflow = len(users) - len(shown)

    items = [
        {
            "u": u,
            "avatar_src": _avatar_src(u, size),
            "initial": initials(u.display_name),
            "name": u.display_name,
        }
        for u in shown
    ]
    return {
        "items": items,
        "overflow": overflow,
        "sz": size,
        "font_size": font_size,
        "link": link,
    }
