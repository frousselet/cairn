# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""Web forms of module 7 (documents).

Three rules hold for every form here:

**No form exposes a field the lifecycle or an act stamps** : ``approved_by``,
``approved_at``, ``superseded_*``, ``next_review_date``, ``last_reviewed_*``,
``launched_at``, ``closed_at`` and every acknowledgement stamp are written by
``transition_to()``, ``record_review()``, ``acknowledge()`` or ``excuse()``.

**A frozen record renders frozen** : a version past ``draft`` (RG-DOC-02) and a
campaign past ``draft`` (its audience is resolved at launch, RG-DOC-15) open
with every field disabled and refuse to validate, so the refusal is a message
on the form rather than a ``ValidationError`` raised from ``save()``.

**The PDF goes through ``PolicyVersion.set_pdf()``**, which applies the
RG-DOC-04 checks (extension, magic bytes, size) and stamps the SHA-256 : the
form never writes ``file_content`` itself.
"""

from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from context.models import Scope
from context.widgets import ScopeTreeWidget
from core.lifecycle import linkable_or_linked, resolve_lifecycle
from core.modal_forms import Step, SteppedFormMixin
from core.scoping import filter_queryset_by_scopes

from .constants import PDF_MAX_BYTES
from .models import AcknowledgementCampaign, Policy, PolicyVersion
from .models.policy_version import next_version_label

FORM_WIDGET_ATTRS = {"class": "form-control"}
SELECT_ATTRS = {"class": "form-select"}
CHECKBOX_ATTRS = {"class": "form-check-input"}
MULTISELECT_ATTRS = {**SELECT_ATTRS, "size": 5}
RICH_TEXT_ATTRS = {**FORM_WIDGET_ATTRS, "rows": 12, "class": "form-control rich-text"}
PDF_INPUT_ATTRS = {**FORM_WIDGET_ATTRS, "accept": "application/pdf,.pdf"}


def _date_widget():
    return forms.DateInput(attrs={**FORM_WIDGET_ATTRS, "type": "date"}, format="%Y-%m-%d")


def _textarea(rows=3):
    """A plain-text area : the shell turns every other ``textarea.form-control``
    into a rich-text editor, which would store HTML in a plain field."""
    return forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": rows, "class": "form-control no-richtext"})


def _is_new(instance):
    """UUID primary keys are set before the first save : ``pk`` is not the test."""
    return instance._state.adding


def _user_scope_ids(user):
    if user is None or user.is_superuser:
        return None
    return user.get_allowed_scope_ids()


def _scoped(qs, user):
    """Restrict a picker to what ``user`` may see (scope tenancy)."""
    scope_ids = _user_scope_ids(user)
    if scope_ids is None:
        return qs
    return filter_queryset_by_scopes(qs, scope_ids)


def _active_users(current_ids=()):
    User = get_user_model()
    from django.db.models import Q

    return User.objects.filter(Q(is_active=True) | Q(pk__in=[i for i in current_ids if i])).order_by(
        "last_name", "first_name", "email",
    )


def _freeze(form, note):
    """Disable every field of a frozen record and say why : once at the top of
    the drawer (``_frozen_note.html``), and on the first field for the page form."""
    for field in form.fields.values():
        field.disabled = True
    first = next(iter(form.fields.values()), None)
    if first is not None:
        first.help_text = note
    form.frozen_note = note


class ScopedFormMixin:
    """Fill the scopes tree with the scopes the user may assign (as in incidents)."""

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        if "scopes" not in self.fields:
            return
        archived = [step.code for step in resolve_lifecycle(Scope).archived_steps]
        qs = Scope.objects.exclude(workflow_state__in=archived)
        scope_ids = _user_scope_ids(user)
        if scope_ids is not None:
            qs = qs.filter(id__in=scope_ids)
        field = self.fields["scopes"]
        field.queryset = qs
        selected_ids = []
        if self.instance is not None and not _is_new(self.instance):
            selected_ids = list(self.instance.scopes.values_list("pk", flat=True))
        elif hasattr(self.data, "getlist"):
            selected_ids = self.data.getlist(self.add_prefix("scopes"))
        elif self.initial.get("scopes"):
            selected_ids = [getattr(s, "pk", s) for s in self.initial["scopes"]]
        field.widget.build_tree_data(qs, selected_ids)


class PdfUploadMixin:
    """The PDF upload of a version, applied through ``PolicyVersion.set_pdf()``."""

    def clean_upload(self):
        upload = self.cleaned_data.get("upload")
        if upload and upload.size and upload.size > PDF_MAX_BYTES:
            raise ValidationError(_("The PDF must not exceed 25 MB."))
        return upload

    def apply_pdf(self, version):
        """Read the upload into ``version`` (RG-DOC-04); errors land on ``upload``."""
        upload = self.cleaned_data.get("upload")
        if upload:
            try:
                version.set_pdf(upload.read(), upload.name)
            except ValidationError as exc:
                self.add_error("upload", exc)
        elif self.cleaned_data.get("clear_pdf"):
            version.clear_pdf()


# --- Policy (the document) --------------------------------------------------


class PolicyForm(SteppedFormMixin, ScopedFormMixin, forms.ModelForm):
    """A document's identity (RG-DOC-08) : editable while it lives, never its content."""

    steps = [
        Step(_("Identity"), "file-earmark-text", [
            "title",
            ["document_type", "classification"],
            "summary",
            "parent",
        ]),
        Step(_("Ownership and review"), "person-check", [
            ["owner", "approver"],
            ["review_frequency_months", "next_review_override"],
        ]),
        Step(_("Coverage"), "diagram-3", [
            "applies_to_roles",
            "linked_requirements",
            "scopes",
            "tags",
        ]),
    ]

    class Meta:
        model = Policy
        fields = [
            "title", "document_type", "classification", "summary", "parent",
            "owner", "approver", "review_frequency_months", "next_review_override",
            "applies_to_roles", "linked_requirements", "scopes", "tags",
        ]
        widgets = {
            "title": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "document_type": forms.Select(attrs=SELECT_ATTRS),
            "classification": forms.Select(attrs=SELECT_ATTRS),
            "summary": _textarea(3),
            "parent": forms.Select(attrs=SELECT_ATTRS),
            "owner": forms.Select(attrs=SELECT_ATTRS),
            "approver": forms.Select(attrs=SELECT_ATTRS),
            "review_frequency_months": forms.NumberInput(attrs={**FORM_WIDGET_ATTRS, "min": 1, "max": 60}),
            "next_review_override": _date_widget(),
            "applies_to_roles": forms.SelectMultiple(attrs=MULTISELECT_ATTRS),
            "linked_requirements": forms.SelectMultiple(attrs=MULTISELECT_ATTRS),
            "scopes": ScopeTreeWidget(),
            "tags": forms.SelectMultiple(attrs={**SELECT_ATTRS, "size": 4}),
        }
        help_texts = {
            "title": _("The document title, e.g. Access control policy."),
            "summary": _("One paragraph on what the document is for, shown in lists."),
            "parent": _("The document this one implements, e.g. the policy above a procedure."),
            "owner": _("Maintains the document and receives the review reminders."),
            "approver": _("Who is expected to approve new versions. The approval itself is recorded by the transition."),
            "review_frequency_months": _("The next review is due this many months after the version in force took effect."),
            "next_review_override": _("Set a date only to override the computed next review."),
            "applies_to_roles": _("The roles the document is addressed to, also the default audience of a campaign."),
            "linked_requirements": _("The requirements this document answers (clause 5.2, A.5.1...)."),
            "scopes": _("The parts of the organisation this document governs."),
            "tags": _("Free-form labels for filtering and grouping."),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        instance = self.instance
        # Parent : a linkable (active) document the user may see, never this
        # document nor one of its descendants (RG-DOC-10).
        parent_field = self.fields["parent"]
        parent_qs = _scoped(Policy.objects.all(), self.user)
        current_parent = Policy.objects.filter(pk=instance.parent_id) if instance.parent_id else None
        parent_qs = linkable_or_linked(parent_qs, current_parent)
        if not _is_new(instance):
            excluded = {instance.pk} | self._descendant_ids(instance)
            parent_qs = parent_qs.exclude(pk__in=excluded)
        parent_field.queryset = parent_qs.order_by("reference")
        for name in ("owner", "approver"):
            self.fields[name].queryset = _active_users([getattr(instance, f"{name}_id", None)])
        for name in ("applies_to_roles", "linked_requirements"):
            field = self.fields[name]
            linked = None if _is_new(instance) else getattr(instance, name).all()
            field.queryset = linkable_or_linked(field.queryset, linked)

    @staticmethod
    def _descendant_ids(policy):
        found, frontier = set(), [policy.pk]
        while frontier:
            children = list(Policy.objects.filter(parent_id__in=frontier).values_list("pk", flat=True))
            frontier = [c for c in children if c not in found]
            found.update(frontier)
        return found


class PolicyCreateForm(PdfUploadMixin, PolicyForm):
    """Create a document and its first, draft version in one go."""

    version_label = forms.CharField(
        label=_("Version label"), max_length=20, initial="1.0",
        widget=forms.TextInput(attrs=FORM_WIDGET_ATTRS),
        help_text=_("The label of the first version, e.g. 1.0."),
    )
    content = forms.CharField(
        label=_("Content"), required=False, widget=forms.Textarea(attrs=RICH_TEXT_ATTRS),
        help_text=_("The text of the document. You can also attach a PDF, or both."),
    )
    upload = forms.FileField(
        label=_("PDF document"), required=False,
        widget=forms.ClearableFileInput(attrs=PDF_INPUT_ATTRS),
        help_text=_("The signed or published copy, as a PDF file (25 MB max)."),
    )

    steps = PolicyForm.steps + [
        Step(_("First version"), "file-earmark-plus", ["version_label", "content", "upload"]),
    ]

    def clean(self):
        cleaned = super().clean()
        version = PolicyVersion(version_label=cleaned.get("version_label") or "1.0", content=cleaned.get("content") or "")
        self.apply_pdf(version)
        self.first_version = version
        return cleaned

    def save_first_version(self, policy, user):
        """Attach the draft first version to the saved document."""
        version = self.first_version
        version.policy = policy
        version.created_by = user
        version.save()
        return version


# --- PolicyVersion ----------------------------------------------------------


class PolicyVersionForm(PdfUploadMixin, SteppedFormMixin, ScopedFormMixin, forms.ModelForm):
    """Edit a draft version. From ``in_review`` onward the content is frozen (RG-DOC-02)."""

    upload = forms.FileField(
        label=_("PDF document"), required=False,
        widget=forms.ClearableFileInput(attrs=PDF_INPUT_ATTRS),
        help_text=_("Attach or replace the PDF (25 MB max). Its SHA-256 is recorded."),
    )
    clear_pdf = forms.BooleanField(
        label=_("Remove the attached PDF"), required=False,
        widget=forms.CheckboxInput(attrs=CHECKBOX_ATTRS),
    )

    steps = [
        Step(_("Content"), "file-earmark-text", ["version_label", "content"]),
        Step(_("Document"), "file-earmark-pdf", ["upload", "clear_pdf"]),
        Step(_("Change and effect"), "journal-check", ["change_summary", "effective_from", "tags"]),
    ]

    class Meta:
        model = PolicyVersion
        fields = ["version_label", "content", "change_summary", "effective_from", "tags"]
        widgets = {
            "version_label": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "content": forms.Textarea(attrs=RICH_TEXT_ATTRS),
            "change_summary": _textarea(4),
            "effective_from": _date_widget(),
            "tags": forms.SelectMultiple(attrs={**SELECT_ATTRS, "size": 4}),
        }
        help_texts = {
            "version_label": _("Unique for the document, e.g. 1.3 or 2.0."),
            "content": _("The text of the document. It is frozen once the version is submitted."),
            "change_summary": _("What changed since the previous version, and why. Required from the second version."),
            "effective_from": _("Leave empty to take the approval date. It can be earlier, never in the future."),
        }

    def __init__(self, *args, **kwargs):
        instance = kwargs.get("instance")
        if instance is None or not instance.has_pdf:
            # Nothing to remove : the checkbox would be noise.
            self.steps = [
                step if step.title != self.steps[1].title else Step(step.title, step.icon, ["upload"])
                for step in self.steps
            ]
        super().__init__(*args, **kwargs)
        if self.instance.is_frozen:
            _freeze(self, _("A submitted version is frozen : its content can no longer be changed."))

    def _validate_steps(self):
        # Runs once the fields exist and before the step coverage check.
        if not self.instance.has_pdf:
            self.fields.pop("clear_pdf", None)
        super()._validate_steps()

    def clean(self):
        cleaned = super().clean()
        if getattr(self, "frozen_note", None):
            raise ValidationError(self.frozen_note)
        return cleaned

    def _post_clean(self):
        if hasattr(self, "cleaned_data") and not getattr(self, "frozen_note", None):
            self.apply_pdf(self.instance)
        super()._post_clean()


class NewVersionForm(forms.Form):
    """RG-DOC-05 : draft the next version from the one in force."""

    bump = forms.ChoiceField(label=_("Version number"), widget=forms.Select(attrs=SELECT_ATTRS))

    def __init__(self, *args, policy=None, **kwargs):
        super().__init__(*args, **kwargs)
        source = policy.version_in_force or policy.latest_version if policy else None
        current = source.version_label if source else None
        self.fields["bump"].choices = [
            ("minor", _("Minor revision : %(label)s") % {"label": next_version_label(current, "minor")}),
            ("major", _("Major revision : %(label)s") % {"label": next_version_label(current, "major")}),
        ]
        self.fields["bump"].initial = "minor"
        self.fields["bump"].help_text = (
            _("The new draft starts from the content and the PDF of version %(label)s.") % {"label": current}
            if current else _("The first version of this document starts empty.")
        )


class RecordReviewForm(forms.Form):
    """RG-DOC-13 : reviewed, no change."""

    comment = forms.CharField(
        label=_("Review note"), required=False, widget=_textarea(4),
        help_text=_("What was checked and why no new version is needed. Recorded in the history."),
    )


# --- AcknowledgementCampaign ------------------------------------------------


class AcknowledgementCampaignForm(SteppedFormMixin, ScopedFormMixin, forms.ModelForm):
    """A campaign is edited in ``draft`` only : its audience is resolved at launch (RG-DOC-15)."""

    steps = [
        Step(_("Campaign"), "patch-check", [
            "name",
            ["policy_version", "due_date"],
            "message",
            "statement",
        ]),
        Step(_("Audience"), "people", ["audience_users", "audience_groups", "audience_roles"]),
        Step(_("Scope and filing"), "diagram-3", ["scopes", "tags"]),
    ]

    class Meta:
        model = AcknowledgementCampaign
        fields = [
            "name", "policy_version", "due_date", "message", "statement",
            "audience_users", "audience_groups", "audience_roles", "scopes", "tags",
        ]
        widgets = {
            "name": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "policy_version": forms.Select(attrs=SELECT_ATTRS),
            "due_date": _date_widget(),
            "message": _textarea(3),
            "statement": _textarea(2),
            "audience_users": forms.SelectMultiple(attrs={**SELECT_ATTRS, "size": 6}),
            "audience_groups": forms.SelectMultiple(attrs=MULTISELECT_ATTRS),
            "audience_roles": forms.SelectMultiple(attrs=MULTISELECT_ATTRS),
            "scopes": ScopeTreeWidget(),
            "tags": forms.SelectMultiple(attrs={**SELECT_ATTRS, "size": 4}),
        }
        help_texts = {
            "name": _("e.g. Acceptable use charter 2.0 : all staff."),
            "policy_version": _("The version to acknowledge. Only a version in force can be launched."),
            "due_date": _("The acknowledgement deadline. Reminders go out before and after it."),
            "message": _("Shown to each person above the document."),
            "statement": _("The sentence each person confirms. {title} and {label} are replaced by the document title and the version label."),
            "audience_users": _("Named people."),
            "audience_groups": _("Every active member at launch."),
            "audience_roles": _("Every person assigned to the role at launch."),
            "scopes": _("Leave empty to take the scopes of the document."),
            "tags": _("Free-form labels for filtering and grouping."),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        instance = self.instance
        version_field = self.fields["policy_version"]
        current = PolicyVersion.objects.filter(pk=instance.policy_version_id) if instance.policy_version_id else None
        version_qs = _scoped(PolicyVersion.objects.select_related("policy"), self.user)
        version_field.queryset = linkable_or_linked(version_qs, current).order_by("policy__reference", "-created_at")
        version_field.label_from_instance = lambda v: f"{v.policy.reference} : {v.policy.title} (v{v.version_label})"
        self.fields["audience_users"].queryset = _active_users(
            [] if _is_new(instance) else list(instance.audience_users.values_list("pk", flat=True))
        )
        roles = self.fields["audience_roles"]
        roles.queryset = linkable_or_linked(roles.queryset, None if _is_new(instance) else instance.audience_roles.all())
        if not _is_new(instance) and instance.workflow_state != resolve_lifecycle(AcknowledgementCampaign).initial_step.code:
            _freeze(self, _("A launched campaign can no longer be edited : its audience was resolved at launch."))

    def clean(self):
        cleaned = super().clean()
        if getattr(self, "frozen_note", None):
            raise ValidationError(self.frozen_note)
        due = cleaned.get("due_date")
        if due and due < timezone.localdate():
            self.add_error("due_date", _("The due date is already past."))
        version = cleaned.get("policy_version")
        if version is not None and not cleaned.get("scopes") and "scopes" in self.fields:
            # The campaign defaults to the document's scopes.
            cleaned["scopes"] = version.policy.scopes.all()
        return cleaned


# --- Acknowledgement rows ---------------------------------------------------


class ExcuseForm(forms.Form):
    """RG-DOC-19 : excuse a pending addressee, with a mandatory reason."""

    reason = forms.CharField(
        label=_("Reason"), widget=_textarea(4),
        help_text=_("e.g. left the organisation, long absence. The row keeps its history."),
    )
