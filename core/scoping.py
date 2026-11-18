# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""Single source of truth for resolving a model's path to `context.Scope`.

Scope tenancy used to be answered in four places, each with its own copy of
the same three-branch decision. Two of them (`ScopeFilterMixin` and
`ScopeFilterAPIMixin`) grew support for a `scope_parent_lookup`, so a child
row could inherit its parent's scopes. The other two - the generic workflow
transition and history endpoints - and the MCP list layer did not, and fell
through to "no filtering" for any model without its own `scopes` M2M. A
child row was therefore readable, transitionable and fully auditable from
outside its scope.

Resolution happens here so a model that declares `scope_parent_lookup` is
honoured by every surface at once, and so a future surface has one function
to call rather than a pattern to reproduce.
"""
from django.apps import apps
from django.db.models import Q


def resolve_scope_lookup(model, explicit=None):
    """Return the ORM path from `model` to scope ids, or None when unscoped.

    `explicit` lets a view or viewset override the model-level declaration,
    preserving the historical behaviour of the two mixins.
    """
    if explicit:
        return explicit
    Scope = apps.get_model("context", "Scope")
    if model is Scope or getattr(model, "_meta", None) and model._meta.label == "context.Scope":
        return "id"
    lookup = getattr(model, "scope_parent_lookup", None)
    if lookup:
        return lookup
    if any(f.name == "scopes" for f in model._meta.many_to_many):
        return "scopes"
    return None


def filter_queryset_by_scopes(qs, scope_ids, explicit=None):
    """Restrict `qs` to rows reachable from `scope_ids`.

    A model whose parent relation is optional sets `scope_parent_optional`.
    Without it the join is an INNER JOIN and every row with no parent is
    dropped, which for a register holding parentless rows means hiding them
    from everyone but a superuser. With it, parentless rows stay visible,
    matching `object_in_scopes`.
    """
    lookup = resolve_scope_lookup(qs.model, explicit)
    if lookup is None:
        return qs
    if lookup == "id":
        return qs.filter(id__in=scope_ids)
    if _requires_every_scope(qs.model, lookup, explicit):
        # Filed under at least one scope, and under none the user is not given.
        Scope = apps.get_model("context", "Scope")
        beyond = qs.model._base_manager.filter(
            **{f"{lookup}__in": Scope._base_manager.exclude(id__in=scope_ids)}
        ).values("pk")
        return qs.filter(**{f"{lookup}__isnull": False}).exclude(pk__in=beyond).distinct()
    alternates = _alternate_lookups(qs.model, explicit)
    matches = Q(**{f"{lookup}__id__in": scope_ids})
    for alternate in alternates:
        matches |= Q(**{f"{alternate}__id__in": scope_ids})
    if getattr(qs.model, "scope_parent_optional", False):
        # Parentless rows stay visible, but only when no alternate parent
        # files them either : a row reachable through an alternate parent is
        # scoped by that parent.
        orphan = Q(**{f"{lookup}__isnull": True})
        for alternate in alternates:
            orphan &= Q(**{f"{alternate}__isnull": True})
        matches |= orphan
    return qs.filter(matches).distinct()


def _requires_every_scope(model, lookup, explicit=None):
    """Whether a row of `model` is reached only by who is given **every** scope it is filed under.

    The usual rule is "one scope in common" : a record filed under two scopes
    belongs to both. A model sets ``scope_requires_every_scope = True`` when
    its rows are *made from* what several scopes hold (a generated report) :
    sharing one scope must not open what was drawn from the other. Such a row
    filed under no scope covers everything, and is reached by nobody the
    scopes restrict.
    """
    return bool(not explicit and lookup == "scopes" and getattr(model, "scope_requires_every_scope", False))


def _alternate_lookups(model, explicit=None):
    """Extra parent paths of a row that may be filed under one of several
    parents (``scope_parent_alternates``), e.g. a nonconformity raised by an
    audit, an incident or a control test. Ignored when a surface passes an
    explicit lookup."""
    if explicit:
        return ()
    return tuple(getattr(model, "scope_parent_alternates", ()) or ())


class AuthenticationRequired(Exception):
    """A record was asked for by a visitor who is not signed in.

    Raised by `get_scoped_object_or_404` : a view that fetches its parent
    record before its login check ran (in `dispatch`) must still send the
    visitor to the login page, not answer 404, and must never hand the record
    over. `accounts.middleware.AuthenticationRequiredMiddleware` turns it into
    that redirect.
    """


def user_can_reach(user, obj):
    """Whether `user` may act on `obj`, as far as scope tenancy goes.

    A superuser and a user no group restricts reach everything. Anyone else
    reaches what is filed under one of their scopes (`object_in_scopes`). A
    visitor who is not signed in reaches nothing through this door : a public
    surface fetches its records explicitly.
    """
    if not getattr(user, "is_authenticated", False):
        return False
    if user.is_superuser:
        return True
    allowed = user.get_allowed_scope_ids()
    return allowed is None or object_in_scopes(obj, allowed)


def scoped_queryset(user, qs, explicit=None):
    """`qs` restricted to the records `user` may reach.

    The queryset side of `get_scoped_object_or_404` : for a selection made of
    identifiers taken from the request (a bulk action, the records a report
    is generated from), or a record looked up without a 404.
    """
    if not getattr(user, "is_authenticated", False):
        return qs.none()
    if user.is_superuser:
        return qs
    allowed = user.get_allowed_scope_ids()
    if allowed is None:
        return qs
    return filter_queryset_by_scopes(qs, allowed, explicit)


def narrow_scope_ids(user, requested=None):
    """The scope ids a selection may cover for `user`, `None` meaning no limit.

    A superuser, or a user no group restricts, gets what was asked (`None`
    when nothing was). A user restricted to some scopes gets the asked ids
    that are theirs, or all of theirs when none was asked : an empty list
    when nothing of what was asked is theirs, which must select nothing (a
    caller tests `is not None`, never the truth of the list).
    """
    requested = list(requested) if requested else None
    if not getattr(user, "is_authenticated", False):
        return []
    if user.is_superuser:
        return requested
    allowed = user.get_allowed_scope_ids()
    if allowed is None:
        return requested
    if requested is None:
        return list(allowed)
    mine = {str(scope_id) for scope_id in allowed}
    return [scope_id for scope_id in requested if str(scope_id) in mine]


def get_scoped_object_or_404(user, klass, *args, **kwargs):
    """`get_object_or_404`, refusing a record filed outside the user's scopes.

    The one way a view fetches a record named by the request (an identifier
    in the URL or in the body) when it is not a generic single-record view,
    which `accounts.views.PermissionRequiredMixin.get_object` already guards.
    A permission says what a user may do, their scopes on which records :
    a view that checks the first and fetches with `get_object_or_404` lets a
    user restricted to one scope act on the records of another by their
    address. The answer to a record out of reach is the one of an unknown
    record (404) : it does not tell whether the record exists.

    `klass` is a model, a manager or a queryset, as for `get_object_or_404`.
    A model with no path to the scopes is returned as found. A visitor who is
    not signed in is sent to the login page (`AuthenticationRequired`) before
    anything is fetched.
    """
    from django.http import Http404
    from django.shortcuts import get_object_or_404

    if not getattr(user, "is_authenticated", False):
        raise AuthenticationRequired
    obj = get_object_or_404(klass, *args, **kwargs)
    if not user_can_reach(user, obj):
        raise Http404
    return obj


def get_scoped_object_or_none(user, klass, *args, **kwargs):
    """The record asked for, or `None` when it is unknown or out of reach.

    `get_scoped_object_or_404` for a lookup that is optional (a record named
    by a query parameter, a reference kept in the session) : the caller goes
    on without it. Same rule : a record filed under no scope stays reachable,
    one filed under another scope does not.
    """
    if not getattr(user, "is_authenticated", False):
        return None
    from django.core.exceptions import ValidationError

    queryset = klass if hasattr(klass, "filter") else klass._default_manager
    try:
        obj = queryset.filter(*args, **kwargs).first()
    except (ValueError, TypeError, ValidationError):
        # A malformed identifier names no record.
        return None
    if obj is None or not user_can_reach(user, obj):
        return None
    return obj


def object_in_scopes(obj, scope_ids):
    """Whether `obj` is visible to a user allowed `scope_ids`.

    An object that carries no scope at all stays visible. That is deliberate
    and matches the guard this replaces : scoping restricts what has been
    filed under a perimeter, it does not hide records nobody has filed yet.
    The exception is a model whose rows are made from what several scopes
    hold (`_requires_every_scope`) : every scope of the row is needed, and a
    row filed under none is out of reach.
    """
    model = type(obj)
    lookup = resolve_scope_lookup(model)
    if lookup is None:
        return True
    base = model._default_manager.filter(pk=obj.pk)
    if lookup == "id":
        return base.filter(id__in=scope_ids).exists()
    if _requires_every_scope(model, lookup):
        filed = set(getattr(obj, lookup).values_list("pk", flat=True))
        return bool(filed) and filed <= set(scope_ids)
    lookups = (lookup, *_alternate_lookups(model))
    filed = Q()
    for path in lookups:
        filed |= Q(**{f"{path}__isnull": False})
    if not base.filter(filed).exists():
        return True
    reachable = Q()
    for path in lookups:
        reachable |= Q(**{f"{path}__id__in": scope_ids})
    return base.filter(reachable).exists()


# ── Relations : what a user may point a record at ───────────────────────────


def is_restricted(user):
    """Whether the scopes of their groups limit what `user` reaches."""
    if not getattr(user, "is_authenticated", False):
        return True
    return not user.is_superuser and user.get_allowed_scope_ids() is not None


def selectable(user, queryset, keep=()):
    """`queryset` narrowed to what `user` may point a record at.

    A relation is a way to reach a record : choosing it in a form, or naming
    its identifier in a request, links it to one's own, shows its name back
    and may copy what it holds (a support asset inherits the security needs
    of the essential assets it is attached to). So a relation offers and
    accepts what the registers show the user (`scoped_queryset`), and nothing
    else. `keep` names the rows the record already holds : a link set by
    someone with a wider reach stays valid, so that saving the record again
    neither fails nor drops it.

    A model with no path to the scopes, and a user nothing restricts, get the
    queryset as it is.
    """
    if not is_restricted(user) or resolve_scope_lookup(queryset.model) is None:
        return queryset
    within = scoped_queryset(user, queryset.model._base_manager.all()).values("pk")
    condition = Q(pk__in=within)
    keep = [pk for pk in keep if pk is not None]
    if keep:
        condition |= Q(pk__in=keep)
    return queryset.filter(condition)


def held_by(instance, name):
    """The keys of the rows the relation `name` of a saved `instance` holds."""
    from django.core.exceptions import FieldDoesNotExist

    if instance is None or getattr(instance, "pk", None) is None or instance._state.adding:
        return []
    try:
        field = instance._meta.get_field(name)
    except FieldDoesNotExist:
        return []
    if field.many_to_many and not field.auto_created:
        return list(getattr(instance, name).values_list("pk", flat=True))
    if field.many_to_one or field.one_to_one:
        attname = getattr(field, "attname", None)
        value = getattr(instance, attname, None) if attname else None
        return [value] if value is not None else []
    return []


def restrict_form_relations(form, user):
    """Make the relation fields of `form` offer what `user` may select.

    A select or a picker over a scoped model listed every record : the names
    of the records of another scope were printed into the page, and one of
    them could be chosen and saved. Each such field now offers what the user
    may select (`selectable`), plus what the record already holds.

    A user limited to some scopes files what they create under one of them :
    the scopes of a new record are then required, since a record filed under
    nothing is one its own author no longer finds in the register.

    Called by `accounts.views.PermissionRequiredMixin.get_form` for every
    generic form view; a view that builds a form by hand calls it itself
    (`core/tests/test_scoping.py` walks the views and fails on one that does
    not). Returns the form.
    """
    if not is_restricted(user):
        return form
    instance = getattr(form, "instance", None)
    creating = instance is None or getattr(instance, "pk", None) is None or instance._state.adding
    for name, field in form.fields.items():
        queryset = getattr(field, "queryset", None)
        if queryset is None or resolve_scope_lookup(queryset.model) is None:
            continue
        field.queryset = selectable(user, queryset, keep=held_by(instance, name))
        _trim_choices(form, name, field)
        if creating and name == "scopes" and resolve_scope_lookup(queryset.model) == "id":
            field.required = True
    return form


def restrict_formset_relations(formset, user):
    """`restrict_form_relations` for every form of `formset`, the blank one included."""
    if not is_restricted(user):
        return formset
    for form in formset.forms:
        restrict_form_relations(form, user)
    try:
        blank = formset.empty_form
    except Exception:  # noqa: BLE001 - a formset with no template form has none to restrict
        blank = None
    if blank is not None:
        restrict_form_relations(blank, user)
        # ``empty_form`` is rebuilt at each access : the restricted one is the
        # one the template must render.
        formset.__dict__["empty_form"] = blank
    return formset


def _trim_choices(form, name, field):
    """Drop from the hand-made choices of `field` what its queryset no longer holds.

    A field whose choices were written by the form (a tree of sites, options
    grouped under a heading) keeps showing them whatever its queryset becomes;
    a tree widget keeps the data it was built from.
    """
    allowed = None

    def keys():
        nonlocal allowed
        if allowed is None:
            allowed = {str(pk) for pk in field.queryset.values_list("pk", flat=True)}
        return allowed

    def kept(choices):
        result = []
        for value, label in choices:
            if isinstance(label, (list, tuple)):
                inner = kept(label)
                if inner:
                    result.append((value, inner))
            elif value in ("", None) or str(getattr(value, "value", value)) in keys():
                result.append((value, label))
        return result

    if "_choices" in field.__dict__:
        field.choices = kept(list(field.__dict__["_choices"]))
    build_tree = getattr(field.widget, "build_tree_data", None)
    if build_tree is not None:
        value = form[name].value()
        if getattr(field.widget, "allow_multiple_selected", False) or isinstance(value, (list, tuple)):
            selected = [str(getattr(item, "pk", item)) for item in (value or [])]
        else:
            selected = getattr(value, "pk", value)
        build_tree(field.queryset, selected)
