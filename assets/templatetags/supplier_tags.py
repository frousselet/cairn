from django import template

from accounts.templatetags.accounts_tags import initials

register = template.Library()


def _logo_src(supplier, size):
    """Pick the best supplier logo rendition for a given diameter (px)."""
    if not (supplier and supplier.logo):
        return ""
    if size <= 16:
        return supplier.logo_16 or supplier.logo
    if size <= 32:
        return supplier.logo_32 or supplier.logo
    return supplier.logo_64 or supplier.logo


@register.inclusion_tag("includes/supplier_avatars.html")
def supplier_avatars(suppliers, size=24, max=5, link=True):
    """Render a compact, overlapping stack of supplier logos (no names).

    Mirrors ``{% user_avatars %}`` but for suppliers: each chip shows the
    supplier logo (or its initials) and carries the supplier name as a
    tooltip. A trailing ``+N`` chip appears past ``max``; a muted ``-``
    placeholder is shown when there is no supplier.

    Usage:
        {% load supplier_tags %}
        {% supplier_avatars supplier_type.suppliers.all %}
        {% supplier_avatars supplier_type.suppliers.all size=20 max=4 link=False %}
    """
    size = int(size)
    max = int(max)
    if size >= 32:
        font_size = ".6875rem"
    elif size >= 24:
        font_size = ".5625rem"
    else:
        font_size = ".5rem"

    suppliers = [s for s in (suppliers or []) if s]
    shown = suppliers[:max] if max else suppliers
    overflow = len(suppliers) - len(shown)

    items = [
        {
            "s": s,
            "logo_src": _logo_src(s, size),
            "initial": initials(s.name),
            "name": s.name,
        }
        for s in shown
    ]
    return {
        "items": items,
        "overflow": overflow,
        "sz": size,
        "font_size": font_size,
        "link": link,
    }
