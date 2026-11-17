# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""Reusable declarative step model for modal forms.

A form mixes in :class:`SteppedFormMixin` and declares ``steps`` as an
ordered list of :class:`Step` (title, icon, field names). The modal shell
reads this metadata to render the stepper (multi-step) or the completion
meter (single-step) and to lay out the fields, so entity templates carry
no field markup. This is the single source of truth for a form's grouping
and ordering.

A step is also a **section** of the record : a step that carries a ``key``
can be opened on its own (``FormClass(..., section="key")``), which is how a
detail page edits one card at a time instead of walking the whole form.

See ``docs/brand/brand-guidelines.md`` (Forms section) for the doctrine and
``docs/sdk/usability-standard.md`` for the rules a form is held to.
"""

from django import forms
from django.core.exceptions import NON_FIELD_ERRORS, ImproperlyConfigured, ValidationError
from django.forms.utils import pretty_name
from django.forms.widgets import CheckboxInput, ChoiceWidget, FileInput
from django.utils.functional import lazy
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy


def _col_class(width):
    """Bootstrap column class for a field placed in a multi-column row."""
    if width is None:
        return "col-sm"
    if width == "auto":
        return "col-auto"
    return f"col-sm-{width}"


def _row_cells(item):
    """Normalize one ``Step.fields`` entry into a list of (name, width) cells.

    A plain field name renders full width (a one-cell row). A list / tuple
    renders its members side by side on one row; each member is either a
    field name (equal-width column) or a ``(name, width)`` pair, where width
    is ``"auto"`` or a Bootstrap span (1-12).
    """
    if isinstance(item, str):
        return [(item, None)]
    cells = []
    for sub in item:
        if isinstance(sub, str):
            cells.append((sub, None))
        else:
            cells.append((sub[0], sub[1]))
    return cells


class UnknownSectionError(LookupError):
    """A form was asked for a section none of its steps carries."""


class Step:
    """One group of fields in a modal form.

    ``title``  : translatable label shown in the stepper / section header.
    ``icon``   : Bootstrap icon name without the ``bi-`` prefix.
    ``fields`` : ordered layout entries. Each entry is either a field name
        (rendered full width) or a list of cells rendered side by side on
        one row, where a cell is a field name or a ``(name, width)`` pair
        (width = ``"auto"`` or a Bootstrap span 1-12). Example::

            Step(_("Identity"), "diagram-3", [
                [("icon", "auto"), "name"],   # icon + name on one row
                "parent_scope",
                "description",
            ])

    ``key``    : a stable slug naming the step as a **section** of the record.
        With it the step opens on its own (``?section=<key>``), which is how a
        card of the detail page is edited without walking the whole form.
    ``intro``  : one sentence, shown above the fields, that says in plain
        words what the section is about. It is where a notion is explained
        once, rather than in the helper of each of its fields.
    """

    __slots__ = ("title", "icon", "fields", "key", "intro")

    def __init__(self, title, icon, fields, *, key=None, intro=None):
        self.title = title
        self.icon = icon
        self.fields = tuple(fields)
        self.key = key
        self.intro = intro

    def field_names(self):
        """Flat list of every field name in the step, row layout aside."""
        names = []
        for item in self.fields:
            names.extend(name for name, _ in _row_cells(item))
        return names

    def __repr__(self):
        return f"Step({self.title!r}, {self.icon!r}, {self.fields!r})"


# Django's label for "no value" in a select.
_DJANGO_BLANK_LABEL = "---------"


def humanise_empty_choice(field):
    """Replace Django's ``---------`` by words in the select of ``field``.

    A row of dashes says neither "you must choose" nor "this may stay empty".
    A required select opens on *Choose…*, an optional one on *None*. Only the
    default label is replaced : a form that set its own ``empty_label`` or
    blank choice keeps it. Returns the field.
    """
    from django.forms import ChoiceField, ModelChoiceField, ModelMultipleChoiceField

    if isinstance(field, ModelMultipleChoiceField):
        return field
    label = (
        pgettext_lazy("empty select option", "Choose…")
        if field.required
        else pgettext_lazy("empty select option", "None")
    )
    if isinstance(field, ModelChoiceField):
        if field.empty_label == _DJANGO_BLANK_LABEL:
            field.empty_label = label
    elif isinstance(field, ChoiceField):
        choices = list(field.choices)
        if choices and choices[0][0] in ("", None) and str(choices[0][1]) == _DJANGO_BLANK_LABEL:
            field.choices = [(choices[0][0], label), *choices[1:]]
    return field


def humanise_empty_choices(form):
    """Apply :func:`humanise_empty_choice` to every field of ``form``."""
    for field in form.fields.values():
        humanise_empty_choice(field)


def _named(template, label):
    return str(template) % {"label": str(label)}


_named_lazy = lazy(_named, str)


def _required_template(field):
    """The sentence asking for ``field``, worded after what its control is."""
    widget = field.widget
    if isinstance(widget, CheckboxInput):
        return _('Tick "%(label)s".')
    if isinstance(widget, ChoiceWidget):
        return _('Choose a value for "%(label)s".')
    if isinstance(widget, FileInput):
        return _('Add a file for "%(label)s".')
    return _('Fill in "%(label)s".')


def name_required_errors(form):
    """Make every "required" error of ``form`` name its field and the act.

    Django answers *This field is required.* under every empty field : the
    same sentence five times tells nothing a red border did not. Each required
    field answers with its own label and what to do (*Fill in "Name".*,
    *Choose a value for "Type".*). A field that already carries its own
    message keeps it.

    Idempotent : it runs when the form is built, when it is laid out and when
    it is validated, so a field made required (or relabelled) by a subclass
    after ``super().__init__()`` is named as well.
    """
    default = str(forms.Field.default_error_messages["required"])
    for name, field in form.fields.items():
        if not field.required or field.widget.is_hidden:
            continue
        ours = getattr(field, "_required_named", False)
        if not ours and str(field.error_messages.get("required", default)) != default:
            continue
        label = field.label or pretty_name(name)
        field.error_messages["required"] = _named_lazy(_required_template(field), label)
        field._required_named = True


class LabelledRowsFormSet(forms.BaseInlineFormSet):
    """An inline formset laid out as a table, one record per row.

    The column header names a column on screen but is tied to no control : a
    screen reader would announce a row of nameless fields. Every control takes
    its field's label as ``aria-label``. Pass it as ``formset=`` to
    ``inlineformset_factory`` for any formset rendered as a grid.
    """

    def add_fields(self, form, index):
        super().add_fields(form, index)
        for field in form.fields.values():
            if field.label and not field.widget.is_hidden:
                field.widget.attrs.setdefault("aria-label", str(field.label))


class SteppedFormMixin:
    """Declarative grouping / stepping for a Django form.

    Set ``steps`` to a list of :class:`Step`. One step renders single-step
    (with a completion meter); two or more render as a multi-step wizard.
    The declared steps must cover every visible field exactly once; this is
    validated at instantiation so a missing or duplicated field fails loud
    rather than silently dropping from the form.
    """

    steps = []

    #: A step should stay short enough to fit one viewport without scrolling.
    #: Each layout row (a full-width field or one column row) counts as one;
    #: exceeding this raises, forcing the step to be split.
    max_rows_per_step = 7

    def __init__(self, *args, section=None, **kwargs):
        super().__init__(*args, **kwargs)
        humanise_empty_choices(self)
        #: The :class:`Step` the form is restricted to, or ``None`` (whole form).
        self.active_section = None
        if self.steps:
            self._validate_steps()
            if section:
                self._restrict_to(section)
        name_required_errors(self)

    # -- sections ----------------------------------------------------------

    @classmethod
    def section_keys(cls):
        """The keys under which a step of this form opens on its own."""
        return [step.key for step in cls.steps if step.key]

    @classmethod
    def section(cls, key):
        """The :class:`Step` carrying ``key``, or ``None``."""
        for step in cls.steps:
            if step.key and step.key == key:
                return step
        return None

    def _restrict_to(self, key):
        """Keep the fields of one section : the form edits that card alone.

        The other fields leave ``self.fields``, so they are neither validated
        nor written (Django saves what is in ``cleaned_data`` only) : the
        stored values of the rest of the record are untouched. Hidden fields
        stay, they carry no question.
        """
        step = self.section(key)
        if step is None:
            raise UnknownSectionError(key)
        keep = set(step.field_names())
        for name in [n for n, f in self.fields.items() if n not in keep and not f.widget.is_hidden]:
            del self.fields[name]
        self.steps = [step]
        self.active_section = step

    @property
    def is_editing(self):
        """Whether the form changes an existing record (``False`` : it creates).

        Read from the model instance state, not from its key : a UUID key is
        set before the first save.
        """
        instance = getattr(self, "instance", None)
        state = getattr(instance, "_state", None)
        return bool(state is not None and not state.adding)

    # -- internals ---------------------------------------------------------

    def full_clean(self):
        name_required_errors(self)
        super().full_clean()

    def _update_errors(self, errors):
        """Report a model rule about a field this form does not carry.

        ``Model.clean()`` may raise an error keyed on a field the form leaves
        out (a parent set by the view, a derived field). Django then fails with
        "has no field named ..." and the page answers a server error instead of
        a validation message. Such errors are shown at the top of the form.
        """
        error_dict = getattr(errors, "error_dict", None)
        if error_dict:
            foreign = [
                name for name in error_dict
                if name != NON_FIELD_ERRORS and name not in self.fields
            ]
            if foreign:
                remapped = {k: v for k, v in error_dict.items() if k not in foreign}
                general = list(remapped.pop(NON_FIELD_ERRORS, []))
                for name in foreign:
                    general.extend(error_dict[name])
                remapped[NON_FIELD_ERRORS] = general
                errors = ValidationError(remapped)
        super()._update_errors(errors)

    def _visible_field_names(self):
        return [name for name, f in self.fields.items() if not f.widget.is_hidden]

    def _validate_steps(self):
        seen = []
        keys = [step.key for step in self.steps if step.key]
        duplicated = sorted({k for k in keys if keys.count(k) > 1})
        if duplicated:
            raise ImproperlyConfigured(
                f"{type(self).__name__}: section key used by more than one "
                f"step: {', '.join(duplicated)}."
            )
        for step in self.steps:
            for name in step.field_names():
                if name not in self.fields:
                    raise ImproperlyConfigured(
                        f"{type(self).__name__}: step '{step.title}' references "
                        f"unknown field '{name}'."
                    )
                if name in seen:
                    raise ImproperlyConfigured(
                        f"{type(self).__name__}: field '{name}' appears in more "
                        f"than one step."
                    )
                seen.append(name)
            if len(step.fields) > self.max_rows_per_step:
                raise ImproperlyConfigured(
                    f"{type(self).__name__}: step '{step.title}' has "
                    f"{len(step.fields)} layout rows (max {self.max_rows_per_step}); "
                    f"split it so the step fits one viewport without scrolling."
                )
        uncovered = [n for n in self._visible_field_names() if n not in seen]
        if uncovered:
            raise ImproperlyConfigured(
                f"{type(self).__name__}: these visible fields are not assigned to "
                f"any step: {', '.join(uncovered)}."
            )

    # -- public API consumed by the template -------------------------------

    def _live_steps(self):
        """The steps that still hold a field.

        A form may drop a field that does not apply (the parent of the very
        first scope) after ``super().__init__()`` : the layout follows, and a
        step left with nothing is not shown.
        """
        return [step for step in self.steps if any(n in self.fields for n in step.field_names())]

    @property
    def is_stepped(self):
        return bool(self.steps)

    @property
    def is_multistep(self):
        return len(self._live_steps()) > 1

    @property
    def step_count(self):
        return len(self._live_steps())

    @property
    def modal_size(self):
        """Bootstrap-ish modal width hint consumed by the shell / JS.

        Single-step forms stay compact (``md``); multi-step wizards get a
        wider dialog (``lg``). Non-stepped forms return ``""`` (the default
        width).
        """
        if not self.steps:
            return ""
        return "lg" if self.is_multistep else "md"

    @property
    def required_field_count(self):
        """Number of visible required fields, for the completion meter."""
        return sum(
            1
            for name, f in self.fields.items()
            if f.required and not f.widget.is_hidden
        )

    def iter_steps(self):
        """Yield one dict per step with its rows of bound fields and metadata.

        ``rows`` is a list of rows; each row is a list of cells, and each
        cell is ``{"field": BoundField, "col_class": "col-sm"|...}``. A
        full-width field is simply a one-cell row.
        """
        name_required_errors(self)
        steps = self._live_steps()
        total = len(steps)
        for index, step in enumerate(steps):
            rows = []
            bound = []
            for item in step.fields:
                row = []
                for name, width in _row_cells(item):
                    if name not in self.fields:
                        continue
                    bf = self[name]
                    bound.append(bf)
                    row.append({"field": bf, "col_class": _col_class(width)})
                if row:
                    rows.append(row)
            yield {
                "index": index,
                "number": index + 1,
                "title": step.title,
                "icon": step.icon,
                "key": step.key,
                "intro": step.intro,
                "rows": rows,
                "fields": bound,
                "required_count": sum(1 for bf in bound if bf.field.required),
                "is_first": index == 0,
                "is_last": index == total - 1,
            }
