# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""Unit tests for the declarative step model (core.modal_forms)."""

import pytest
from django import forms
from django.core.exceptions import ImproperlyConfigured

from core.modal_forms import Step, SteppedFormMixin


class MultiStepForm(SteppedFormMixin, forms.Form):
    name = forms.CharField()
    email = forms.EmailField(required=False)
    note = forms.CharField(required=False)
    secret = forms.CharField(widget=forms.HiddenInput, required=False)

    steps = [
        Step("Identity", "person", ["name", "email"]),
        Step("Extra", "tag", ["note"]),
    ]


class SingleStepForm(SteppedFormMixin, forms.Form):
    name = forms.CharField()
    note = forms.CharField(required=False)

    steps = [Step("Identity", "person", ["name", "note"])]


class PlainForm(SteppedFormMixin, forms.Form):
    name = forms.CharField()


def test_is_stepped_and_multistep():
    assert MultiStepForm().is_stepped is True
    assert MultiStepForm().is_multistep is True
    assert SingleStepForm().is_stepped is True
    assert SingleStepForm().is_multistep is False
    # No steps declared at all
    assert PlainForm().is_stepped is False
    assert PlainForm().is_multistep is False


def test_iter_steps_grouping_and_order():
    steps = list(MultiStepForm().iter_steps())
    assert [s["title"] for s in steps] == ["Identity", "Extra"]
    assert [bf.name for bf in steps[0]["fields"]] == ["name", "email"]
    assert [bf.name for bf in steps[1]["fields"]] == ["note"]
    assert steps[0]["number"] == 1
    assert steps[0]["is_first"] and not steps[0]["is_last"]
    assert steps[1]["is_last"] and not steps[1]["is_first"]


def test_required_counts():
    steps = list(MultiStepForm().iter_steps())
    assert steps[0]["required_count"] == 1  # name required, email not
    assert steps[1]["required_count"] == 0
    assert MultiStepForm().required_field_count == 1


def test_hidden_field_does_not_need_a_step():
    # `secret` is a HiddenInput and is intentionally left out of every step.
    assert MultiStepForm().is_stepped  # instantiation did not raise


def test_unknown_field_raises():
    class BadForm(SteppedFormMixin, forms.Form):
        name = forms.CharField()
        steps = [Step("Identity", "person", ["nope"])]

    with pytest.raises(ImproperlyConfigured, match="unknown field 'nope'"):
        BadForm()


def test_duplicate_field_raises():
    class BadForm(SteppedFormMixin, forms.Form):
        name = forms.CharField()
        steps = [
            Step("A", "person", ["name"]),
            Step("B", "tag", ["name"]),
        ]

    with pytest.raises(ImproperlyConfigured, match="more than one step"):
        BadForm()


def test_uncovered_visible_field_raises():
    class BadForm(SteppedFormMixin, forms.Form):
        name = forms.CharField()
        orphan = forms.CharField()
        steps = [Step("Identity", "person", ["name"])]

    with pytest.raises(ImproperlyConfigured, match="not assigned to any step"):
        BadForm()


class RowForm(SteppedFormMixin, forms.Form):
    a = forms.CharField()
    b = forms.CharField()
    c = forms.CharField(required=False)

    steps = [Step("S", "x", [[("a", "auto"), "b"], "c"])]


def test_row_layout():
    step = list(RowForm().iter_steps())[0]
    rows = step["rows"]
    assert len(rows) == 2
    # first row: two columns (a auto-width, b equal-width)
    assert [c["field"].name for c in rows[0]] == ["a", "b"]
    assert rows[0][0]["col_class"] == "col-auto"
    assert rows[0][1]["col_class"] == "col-sm"
    # second row: single full-width field
    assert len(rows[1]) == 1
    assert rows[1][0]["field"].name == "c"
    # flat field list still complete and ordered
    assert [bf.name for bf in step["fields"]] == ["a", "b", "c"]


def test_row_validation_flattens_names():
    class BadRowForm(SteppedFormMixin, forms.Form):
        a = forms.CharField()
        steps = [Step("S", "x", [[("a", "auto"), "nope"]])]

    with pytest.raises(ImproperlyConfigured, match="unknown field 'nope'"):
        BadRowForm()


def test_modal_size():
    assert MultiStepForm().modal_size == "lg"
    assert SingleStepForm().modal_size == "md"
    assert PlainForm().modal_size == ""


def test_too_many_rows_raises():
    class FatForm(SteppedFormMixin, forms.Form):
        max_rows_per_step = 3
        a = forms.CharField()
        b = forms.CharField()
        c = forms.CharField()
        d = forms.CharField()
        steps = [Step("S", "x", ["a", "b", "c", "d"])]

    with pytest.raises(ImproperlyConfigured, match="4 layout rows"):
        FatForm()


@pytest.mark.django_db
def test_a_model_rule_on_a_field_the_form_lacks_is_reported_not_raised():
    """`Model.clean()` naming a field outside the form used to raise
    "has no field named ..." (a server error) instead of a validation error."""
    from compliance.constants import FindingSource, FindingType
    from compliance.forms import FindingRegisterForm

    form = FindingRegisterForm(data={
        "source": FindingSource.COMPLAINT,
        "finding_type": FindingType.MINOR_NON_CONFORMITY,
        "description": "x",
    })
    # Force the model rule : an audit source with no audit, as a stale or
    # forged instance would carry.
    form.fields["source"].choices = list(FindingSource.choices)
    form.data = {**form.data, "source": FindingSource.AUDIT}

    assert form.is_valid() is False
    assert form.non_field_errors()


class TestEmptySelectOption:
    """Django labels "no value" with a row of dashes. The forms say it in words."""

    def _form(self):
        from controls.forms import ControlForm

        return ControlForm()

    @pytest.mark.django_db
    def test_no_stepped_form_select_shows_a_row_of_dashes(self):
        assert "---------" not in self._form().as_p()

    def test_an_optional_select_opens_on_none_and_a_required_one_on_choose(self):
        from django import forms

        from core.modal_forms import SteppedFormMixin

        class Probe(SteppedFormMixin, forms.Form):
            optional = forms.ChoiceField(choices=[("", "---------"), ("a", "A")], required=False)
            required = forms.ChoiceField(choices=[("", "---------"), ("a", "A")])
            custom = forms.ChoiceField(choices=[("", "Any colour"), ("a", "A")], required=False)

        form = Probe()
        assert str(form.fields["optional"].choices[0][1]) == "None"
        assert str(form.fields["required"].choices[0][1]) == "Choose…"
        # A label the form chose itself is kept.
        assert form.fields["custom"].choices[0][1] == "Any colour"


# ── Sections : a step opens on its own ──────────────────────────────────────


class SectionedForm(SteppedFormMixin, forms.Form):
    name = forms.CharField()
    kind = forms.ChoiceField(choices=[("", "---------"), ("a", "A")])
    note = forms.CharField(required=False)
    agree = forms.BooleanField()
    token = forms.CharField(widget=forms.HiddenInput, required=False)

    steps = [
        Step("Identity", "person", ["name", "kind"], key="identity", intro="Who it is."),
        Step("Extra", "tag", ["note", "agree"], key="extra"),
    ]


def test_a_step_with_a_key_is_a_section():
    assert SectionedForm.section_keys() == ["identity", "extra"]
    assert SectionedForm.section("extra").title == "Extra"
    assert SectionedForm.section("nope") is None
    # A step without a key is not a section.
    assert MultiStepForm.section_keys() == []


def test_a_form_opened_on_a_section_carries_its_fields_only():
    form = SectionedForm(section="extra")

    assert form.active_section.key == "extra"
    # The other section's fields are gone; the hidden field, which asks nothing, stays.
    assert set(form.fields) == {"note", "agree", "token"}
    assert form.is_multistep is False
    assert [step["title"] for step in form.iter_steps()] == ["Extra"]


def test_a_section_validates_and_keeps_its_own_fields_only():
    """The required fields of the other sections are neither asked nor missed."""
    form = SectionedForm({"note": "kept", "agree": "on"}, section="extra")

    assert form.is_valid(), form.errors
    assert set(form.cleaned_data) == {"note", "agree", "token"}


def test_an_unknown_section_is_refused():
    from core.modal_forms import UnknownSectionError

    with pytest.raises(UnknownSectionError):
        SectionedForm(section="nope")


def test_two_steps_cannot_share_a_section_key():
    class Twice(SteppedFormMixin, forms.Form):
        a = forms.CharField()
        b = forms.CharField()
        steps = [Step("A", "x", ["a"], key="same"), Step("B", "x", ["b"], key="same")]

    with pytest.raises(ImproperlyConfigured, match="section key"):
        Twice()


def test_a_step_carries_its_introduction():
    first = next(iter(SectionedForm().iter_steps()))

    assert first["key"] == "identity"
    assert first["intro"] == "Who it is."


def test_a_field_dropped_by_the_form_leaves_the_layout():
    """A form may drop a question that does not apply : nothing breaks, and a
    step left with nothing is not a step."""

    class Dropping(SectionedForm):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            del self.fields["note"]
            del self.fields["agree"]

    form = Dropping()

    assert form.step_count == 1
    assert form.is_multistep is False
    assert [step["title"] for step in form.iter_steps()] == ["Identity"]


# ── A required field says its name and what to do ────────────────────────────


def test_a_required_error_names_the_field_and_the_act():
    form = SectionedForm({})

    assert not form.is_valid()
    assert form.errors["name"] == ['Fill in "Name".']
    assert form.errors["kind"] == ['Choose a value for "Kind".']
    assert form.errors["agree"] == ['Tick "Agree".']


def test_a_field_with_its_own_required_message_keeps_it():
    class Own(SteppedFormMixin, forms.Form):
        name = forms.CharField(error_messages={"required": "Give it a name."})
        steps = [Step("Identity", "person", ["name"])]

    form = Own({})

    assert not form.is_valid()
    assert form.errors["name"] == ["Give it a name."]


def test_a_field_made_required_after_init_is_named_as_well():
    """A subclass often sets ``required`` after ``super().__init__()``."""

    class Late(SteppedFormMixin, forms.Form):
        name = forms.CharField(required=False, label="Title")
        steps = [Step("Identity", "person", ["name"])]

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.fields["name"].required = True
            self.fields["name"].label = "Short title"

    form = Late({})

    assert not form.is_valid()
    assert form.errors["name"] == ['Fill in "Short title".']
    # And the sentence the page shows before any submit is the same one.
    row = next(iter(Late().iter_steps()))["fields"][0]
    assert str(row.field.error_messages["required"]) == 'Fill in "Short title".'


def test_an_optional_field_keeps_no_named_message():
    form = SectionedForm()

    assert "required" in form.fields["note"].error_messages
    assert not getattr(form.fields["note"], "_required_named", False)


@pytest.mark.django_db
def test_is_editing_reads_the_instance_state_not_its_key():
    """A UUID key is set before the first save : it does not tell an edit."""
    from context.forms import ScopeCreateForm, ScopeUpdateForm
    from context.models import Scope

    assert ScopeCreateForm().is_editing is False
    assert Scope().pk is not None
    # A form over an instance read from the database edits it.
    existing = Scope(name="x", description="y")
    existing._state.adding = False
    assert ScopeUpdateForm(instance=existing).is_editing is True
    # A plain form creates.
    assert SectionedForm().is_editing is False


# ── The shell : every button carries its word ────────────────────────────────


def _render_shell(form, **context):
    from django.template.loader import render_to_string
    from django.test import RequestFactory

    request = RequestFactory().get("/somewhere/")
    return render_to_string(
        "includes/modal_form.html", {"form": form, "modal_title": "Title", "request": request, **context},
    )


class _Button:
    """A button of the rendered shell : its attributes, and the text it shows."""

    def __init__(self, node):
        self.node = node

    def get(self, name, default=None):
        # A boolean attribute (hidden, data-mform-next) parses to None : it is
        # there all the same, so it is told from a missing one.
        if name not in self.node.attrs:
            return default
        value = self.node.attrs[name]
        return "" if value is None else value

    @property
    def text(self):
        return " ".join(" ".join(t for n in self.node.walk() for t in n.text).split())


def _buttons(html):
    from core.tests.markup_audit import parse

    return [_Button(node) for node in parse(html).walk() if node.tag == "button"]


def _text(button):
    return button.text


def test_a_multistep_form_ends_on_a_footer_with_words():
    html = _render_shell(SectionedForm())
    labels = [_text(b) for b in _buttons(html) if "mform-pill-btn" not in (b.get("class") or "")]

    assert "Cancel" in labels
    assert "Previous" in labels
    assert "Next" in labels
    assert "Save" in labels
    # The floating arrows are gone, here and in the page shell.
    assert "mform-nav" not in html
    from pathlib import Path

    base = Path(__file__).resolve().parents[2] / "templates" / "base.html"
    assert "mform-nav" not in base.read_text(encoding="utf-8")


def test_the_action_waits_for_the_last_step_of_a_creation_only():
    creating = _render_shell(SectionedForm())
    submit = next(b for b in _buttons(creating) if b.get("data-mform-submit") is not None)
    assert submit.get("hidden") is not None
    assert 'data-mform-mode="create"' in creating


@pytest.mark.django_db
def test_a_record_being_edited_can_be_saved_from_any_step():
    from context.forms import ScopeUpdateForm
    from context.models import Scope

    existing = Scope(name="x", description="y")
    existing._state.adding = False
    html = _render_shell(ScopeUpdateForm(instance=existing))

    assert 'data-mform-mode="edit"' in html
    submit = next(b for b in _buttons(html) if b.get("data-mform-submit") is not None)
    assert submit.get("hidden") is None
    # Next is then the quiet button : one primary action at a time.
    following = next(b for b in _buttons(html) if b.get("data-mform-next") is not None)
    assert "btn-secondary" in following.get("class")


def test_each_step_of_the_stepper_is_a_named_button():
    html = _render_shell(SectionedForm())
    pills = [b for b in _buttons(html) if "mform-pill-btn" in (b.get("class") or "")]

    assert [_text(p) for p in pills] == ["1 Identity", "2 Extra"]
    assert pills[0].get("aria-current") == "step"
    assert all(p.get("type") == "button" for p in pills)


def test_past_four_steps_the_stepper_names_the_current_one_only():
    class Six(SteppedFormMixin, forms.Form):
        a = forms.CharField(required=False)
        b = forms.CharField(required=False)
        c = forms.CharField(required=False)
        d = forms.CharField(required=False)
        e = forms.CharField(required=False)
        steps = [Step(n.upper(), "x", [n]) for n in "abcde"]

    assert "mform-stepper--compact" in _render_shell(Six())
    assert "mform-stepper--compact" not in _render_shell(SectionedForm())


def test_the_submit_button_says_what_it_does():
    assert "Save" in [_text(b) for b in _buttons(_render_shell(SingleStepForm()))]
    created = [_text(b) for b in _buttons(_render_shell(SingleStepForm(), submit_label="Create"))]
    assert "Create" in created and "Save" not in created


def test_a_form_with_nothing_required_shows_no_meter():
    class Optional(SteppedFormMixin, forms.Form):
        note = forms.CharField(required=False)
        steps = [Step("Note", "x", ["note"])]

    assert "data-mform-meter" not in _render_shell(Optional())
    assert "data-mform-meter" in _render_shell(SingleStepForm())


def test_a_section_says_so_when_it_comes_back():
    html = _render_shell(SectionedForm(section="extra"))

    assert 'name="_section"' in html and 'value="extra"' in html
    assert 'name="_section"' not in _render_shell(SectionedForm())


def test_a_required_field_carries_the_sentence_that_asks_for_it():
    html = _render_shell(SectionedForm())

    assert 'data-mform-required="Fill in &quot;Name&quot;."' in html
    assert 'data-mform-required="Choose a value for &quot;Kind&quot;."' in html


def test_the_introduction_of_a_step_is_shown_above_its_fields():
    html = _render_shell(SectionedForm())

    assert '<p class="mform-intro">Who it is.</p>' in html


# ── A creation form settles what has one answer only ────────────────────────


@pytest.mark.django_db
class TestCreationFormMixin:
    """``CreationFormMixin``, read through a real creation form (the support asset)."""

    @staticmethod
    def _answers(user, **more):
        return {"name": "Payroll server", "category": "server", "owner": str(user.pk), "description": "", **more}

    @staticmethod
    def _form(*args, **kwargs):
        from assets.forms import SupportAssetCreateForm

        return SupportAssetCreateForm(*args, **kwargs)

    def test_with_several_scopes_the_scope_is_asked(self):
        from accounts.tests.factories import UserFactory
        from context.tests.factories import ScopeFactory

        ScopeFactory()
        ScopeFactory()

        assert "scopes" in self._form(user=UserFactory(is_superuser=True)).fields

    def test_with_one_scope_it_is_not_asked_and_the_record_is_filed_under_it(self):
        from accounts.tests.factories import UserFactory
        from context.tests.factories import ScopeFactory

        only = ScopeFactory()
        user = UserFactory(is_superuser=True)

        form = self._form(self._answers(user), user=user)

        assert "scopes" not in form.fields
        assert form.is_valid(), form.errors
        assert list(form.save().scopes.all()) == [only]

    def test_the_only_scope_is_the_only_one_the_reader_may_reach(self):
        """Two scopes exist, the reader is given one : nothing to choose, and never the other."""
        from accounts.models import Group
        from accounts.tests.factories import UserFactory
        from context.tests.factories import ScopeFactory

        theirs, other = ScopeFactory(), ScopeFactory()
        user = UserFactory()
        group = Group.objects.create(name="One scope only")
        group.allowed_scopes.add(theirs)
        group.users.add(user)

        form = self._form(self._answers(user), user=user)

        assert "scopes" not in form.fields
        assert form.is_valid(), form.errors
        assert list(form.save().scopes.all()) == [theirs]
        assert other.pk != theirs.pk

    def test_a_deferred_save_files_the_record_with_its_relations(self):
        from accounts.tests.factories import UserFactory
        from context.tests.factories import ScopeFactory

        only = ScopeFactory()
        user = UserFactory(is_superuser=True)
        form = self._form(self._answers(user), user=user)
        assert form.is_valid(), form.errors

        record = form.save(commit=False)
        record.save()
        assert list(record.scopes.all()) == []
        form.save_m2m()

        assert list(record.scopes.all()) == [only]

    def test_whoever_creates_the_record_answers_for_it_unless_they_say_otherwise(self):
        from accounts.tests.factories import UserFactory
        from context.tests.factories import ScopeFactory

        ScopeFactory()
        user, someone_else = UserFactory(is_superuser=True), UserFactory()

        assert self._form(user=user).fields["owner"].initial == user.pk
        form = self._form(self._answers(user, owner=str(someone_else.pk)), user=user)
        assert form.is_valid(), form.errors
        assert form.save().owner == someone_else

    def test_without_a_reader_nothing_is_assumed(self):
        from context.tests.factories import ScopeFactory

        ScopeFactory()
        ScopeFactory()

        assert self._form().fields["owner"].initial is None
