# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
from django import forms
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

from compliance.constants import AssessmentStatus
from compliance.models import ComplianceAssessment, Framework
from context.models import Scope
from context.widgets import ScopeTreeWidget
from core.lifecycle import linkable_or_linked, reportable
from core.modal_forms import CreationFormMixin, LabelledRowsFormSet, ScopedFormMixin, Step, SteppedFormMixin
from documents.models import Policy
from reports.constants import (
    DecisionPriority,
)
from reports.models import (
    IsmsChange,
    ManagementReview,
    ManagementReviewComment,
    ManagementReviewDecision,
    ManagementReviewParticipant,
)

User = get_user_model()

_FORM_CONTROL = {"class": "form-control"}
_FORM_SELECT = {"class": "form-select"}
_FORM_CHECK = {"class": "form-check-input"}
_FORM_DATE = {"class": "form-control", "type": "date"}


class SoaReportForm(forms.Form):
    frameworks = forms.ModelMultipleChoiceField(
        queryset=Framework.objects.all(),
        label=_("Frameworks"),
        help_text=_("Select one or more frameworks to include in the Statement of Applicability."),
        widget=forms.SelectMultiple(attrs={
            "class": "form-select",
            "size": 8,
        }),
    )


class AuditReportForm(forms.Form):
    assessment = forms.ModelChoiceField(
        queryset=ComplianceAssessment.objects.filter(
            workflow_state__in=[AssessmentStatus.COMPLETED, AssessmentStatus.CLOSED],
        ).order_by("-assessment_end_date", "-created_at"),
        label=_("Assessment"),
        help_text=_("Select a completed or closed audit to generate the report."),
        widget=forms.Select(attrs={
            "class": "form-select",
        }),
    )


class ManagementReviewForm(forms.Form):
    FORMAT_CHOICES = [
        ("pptx", _("Presentation (PowerPoint)")),
        ("docx", _("Meeting minutes (Word)")),
    ]

    format = forms.ChoiceField(
        choices=FORMAT_CHOICES,
        label=_("Format"),
        initial="pptx",
        widget=forms.RadioSelect(attrs={"class": "form-check-input"}),
    )

    period_start = forms.DateField(
        label=_("Period start"),
        required=False,
        help_text=_("Start of the review period. Leave empty to include all past data."),
        widget=forms.DateInput(attrs={
            "class": "form-control",
            "type": "date",
        }),
    )
    period_end = forms.DateField(
        label=_("Period end"),
        required=False,
        help_text=_("End of the review period. Defaults to today."),
        widget=forms.DateInput(attrs={
            "class": "form-control",
            "type": "date",
        }),
    )

    scopes = forms.ModelMultipleChoiceField(
        # In-force scopes only : read the governance code set off the scope
        # lifecycle rather than hardcoding the step.
        queryset=reportable(Scope.objects.all()).order_by("name"),
        label=_("Scopes"),
        required=False,
        help_text=_("Optionally filter data by scope. Leave empty to include all data."),
        widget=forms.SelectMultiple(attrs={
            "class": "form-select",
            "size": 6,
        }),
    )

    def clean(self):
        cleaned = super().clean()
        start = cleaned.get("period_start")
        end = cleaned.get("period_end")
        if start and end and start > end:
            raise forms.ValidationError(
                _("The period start date must be before the end date.")
            )
        return cleaned


# ═════════════════════════════════════════════════════════════════════
# Persistent management review forms (ISO 27001:2022 clause 9.3)
# ═════════════════════════════════════════════════════════════════════


class ManagementReviewModelForm(SteppedFormMixin, ScopedFormMixin, forms.ModelForm):
    """Edit a management review (ISO 27001:2022 clause 9.3), one section at a time.

    Each step is a section, and a card of the page of the review : the Edit
    button of a card opens its section alone. The participants are rows of
    the review, listed on their own form (``ParticipantFormSet``).
    """

    steps = [
        Step(_("Planning"), "calendar-event", [
            "title",
            ["frequency", "location"],
            ["period_start", "period_end"],
            ["planned_date", "next_review_date"],
        ], key="planning"),
        Step(_("Organisation"), "people", [
            ["facilitator", "approver"],
            "scopes",
            "tags",
        ], key="organisation"),
        Step(_("Description"), "text-left", ["description"], key="description"),
        Step(_("Agenda"), "list-ol", ["agenda"], key="agenda"),
        Step(_("Executive summary"), "file-text", ["summary"], key="summary"),
    ]

    class Meta:
        model = ManagementReview
        fields = [
            "title", "description", "frequency",
            "period_start", "period_end", "planned_date", "location",
            "facilitator", "approver", "next_review_date",
            "agenda", "summary",
            "scopes", "tags",
        ]
        widgets = {
            "title": forms.TextInput(attrs=_FORM_CONTROL),
            "description": forms.Textarea(attrs={**_FORM_CONTROL, "rows": 3}),
            "frequency": forms.Select(attrs=_FORM_SELECT),
            "period_start": forms.DateInput(attrs=_FORM_DATE),
            "period_end": forms.DateInput(attrs=_FORM_DATE),
            "planned_date": forms.DateInput(attrs=_FORM_DATE),
            "location": forms.TextInput(attrs=_FORM_CONTROL),
            "facilitator": forms.Select(attrs=_FORM_SELECT),
            "approver": forms.Select(attrs=_FORM_SELECT),
            "next_review_date": forms.DateInput(attrs=_FORM_DATE),
            "agenda": forms.Textarea(attrs={**_FORM_CONTROL, "rows": 4}),
            "summary": forms.Textarea(attrs={**_FORM_CONTROL, "rows": 4}),
            "scopes": ScopeTreeWidget(),
            "tags": forms.SelectMultiple(attrs={**_FORM_SELECT, "size": 4}),
        }
        help_texts = {
            "title": _("For example : Annual management review 2026."),
            "frequency": _("Exceptional for a review held outside the planned intervals, after a major incident for example."),
            "period_start": _("The indicators, incidents and findings of the period feed the review."),
            "location": _("A meeting room, or the link of a video conference."),
            "facilitator": _("The person who prepares the review and takes its minutes."),
            "approver": _("Usually a member of top management. Whoever closes the review is recorded as its approver otherwise."),
            "next_review_date": _("ISO 27001 clause 9.3 asks for reviews at planned intervals."),
            "scopes": _("The data of these scopes is aggregated in the review and its exports."),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        active_users = User.objects.filter(is_active=True).order_by(
            "last_name", "first_name", "email",
        )
        for name in ("facilitator", "approver"):
            # A section, or the creation form, may not carry the picker.
            if name in self.fields:
                self.fields[name].queryset = active_users
        scopes = self.fields.get("scopes")
        if scopes is not None and not self.instance._state.adding:
            # A scope archived since the review was filed under it is kept,
            # never dropped by the next save.
            linked = Scope.objects.filter(pk__in=self.instance.scopes.values("pk"))
            scopes.queryset = (scopes.queryset | linked).distinct()
            build_tree = getattr(scopes.widget, "build_tree_data", None)
            if build_tree is not None:
                build_tree(scopes.queryset, self._selected_scope_ids())

    def clean(self):
        cleaned = super().clean()
        start = cleaned.get("period_start", self.instance.period_start)
        end = cleaned.get("period_end", self.instance.period_end)
        if start and end and start > end:
            raise forms.ValidationError(
                _("The period start date must be before the end date.")
            )
        return cleaned


class ManagementReviewCreateForm(CreationFormMixin, ManagementReviewModelForm):
    """Plan a management review on one screen : its title, its frequency, the
    period it covers, the date it is held on and the scopes whose data it
    aggregates.

    The frequency is chosen, never answered for the reader. Whoever plans the
    review facilitates it, as the owner of a record answers for it : the page
    of the review names someone else, its approver, its agenda and its
    participants, and lists what the review still needs.
    """

    owner_field = None
    decisions = ("frequency",)

    steps = [
        Step(_("Planning"), "calendar-event", [
            "scopes",
            "title",
            "frequency",
            ["period_start", "period_end"],
            "planned_date",
        ]),
    ]

    class Meta(ManagementReviewModelForm.Meta):
        fields = ["scopes", "title", "frequency", "period_start", "period_end", "planned_date"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.user is not None and self.instance.facilitator_id is None:
            self.instance.facilitator = self.user


class ManagementReviewParticipantForm(forms.ModelForm):
    class Meta:
        model = ManagementReviewParticipant
        fields = ["user", "external_name", "external_role", "role", "attended"]
        widgets = {
            "user": forms.Select(attrs=_FORM_SELECT),
            "external_name": forms.TextInput(attrs=_FORM_CONTROL),
            "external_role": forms.TextInput(attrs=_FORM_CONTROL),
            "role": forms.Select(attrs=_FORM_SELECT),
            "attended": forms.CheckboxInput(attrs=_FORM_CHECK),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["user"].required = False
        self.fields["user"].queryset = User.objects.filter(
            is_active=True,
        ).order_by("last_name", "first_name", "email")

    def clean(self):
        cleaned = super().clean()
        user = cleaned.get("user")
        external_name = (cleaned.get("external_name") or "").strip()
        if not user and not external_name:
            raise forms.ValidationError(
                _("Provide either an internal user or an external participant name."),
            )
        return cleaned


ParticipantFormSet = forms.inlineformset_factory(
    ManagementReview,
    ManagementReviewParticipant,
    form=ManagementReviewParticipantForm,
    extra=1,
    can_delete=True,
    formset=LabelledRowsFormSet,
)


class ManagementReviewTransitionForm(forms.Form):
    target_status = forms.CharField(widget=forms.HiddenInput())
    comment = forms.CharField(
        label=_("Comment"),
        required=False,
        widget=forms.Textarea(attrs={**_FORM_CONTROL, "rows": 3}),
    )


class ManagementReviewDecisionForm(SteppedFormMixin, ScopedFormMixin, forms.ModelForm):
    """Edit a decision of a management review (clause 9.3.3), one section at a time.

    Each step is a section, and a card of the page of the decision : the Edit
    button of a card opens its section alone. The review it belongs to comes
    from the address and is never a question.
    """

    steps = [
        Step(_("Decision"), "check2-square", [
            ["category", "input_clause"],
            "title",
            "description",
            "priority",
        ], key="decision"),
        Step(_("Follow-up"), "person-check", [
            ["owner", "due_date"],
            "status",
        ], key="follow_up"),
        Step(_("Rationale"), "chat-quote", ["rationale"], key="rationale"),
        Step(_("Implementation"), "patch-check", [
            "implemented_at",
            "implementation_evidence",
        ], key="implementation"),
    ]

    class Meta:
        model = ManagementReviewDecision
        fields = [
            "category", "input_clause", "title", "description", "rationale",
            "owner", "due_date", "priority", "status",
            "implemented_at", "implementation_evidence",
        ]
        widgets = {
            "category": forms.Select(attrs=_FORM_SELECT),
            "input_clause": forms.Select(attrs=_FORM_SELECT),
            "title": forms.TextInput(attrs=_FORM_CONTROL),
            "description": forms.Textarea(attrs={**_FORM_CONTROL, "rows": 3}),
            "rationale": forms.Textarea(attrs={**_FORM_CONTROL, "rows": 2}),
            "owner": forms.Select(attrs=_FORM_SELECT),
            "due_date": forms.DateInput(attrs=_FORM_DATE),
            "priority": forms.Select(attrs=_FORM_SELECT),
            "status": forms.Select(attrs=_FORM_SELECT),
            "implemented_at": forms.DateInput(attrs=_FORM_DATE),
            "implementation_evidence": forms.Textarea(
                attrs={**_FORM_CONTROL, "rows": 2},
            ),
        }
        help_texts = {
            "input_clause": _("The input of clause 9.3.2 that led to the decision, for example the audit results."),
            "title": _("For example : Extend the monitoring to the industrial network."),
            "owner": _("The review cannot be closed while a decision has no owner."),
            "due_date": _("The review cannot be closed while a decision has no due date."),
            "rationale": _("Why the management decided it : an auditor reads it to follow the decision back to its inputs."),
            "implementation_evidence": _("A document, a ticket or a record that shows the decision is in place."),
        }

    def __init__(self, *args, review=None, **kwargs):
        super().__init__(*args, **kwargs)
        if review is not None:
            self.instance.review = review
        if "owner" in self.fields:
            self.fields["owner"].queryset = User.objects.filter(
                is_active=True,
            ).order_by("last_name", "first_name", "email")


class ManagementReviewDecisionCreateForm(CreationFormMixin, ManagementReviewDecisionForm):
    """Record a decision of a management review on one screen : what was
    decided, of which kind, who carries it out, by when and how urgently.

    The category and the priority are chosen, never answered for the reader;
    the owner is whoever records it unless they name someone else. The input
    clause, the rationale and the implementation are written on the page of
    the decision.
    """

    owner_field = "owner"
    decisions = ("category", "priority")

    steps = [
        Step(_("Decision"), "check2-square", [
            "title",
            "category",
            "description",
            ["owner", "due_date"],
            "priority",
        ]),
    ]

    class Meta(ManagementReviewDecisionForm.Meta):
        fields = ["title", "category", "description", "owner", "due_date", "priority"]


class IsmsChangeForm(forms.ModelForm):
    class Meta:
        model = IsmsChange
        fields = [
            "change_type", "title", "description", "impact_analysis",
            "affected_scopes", "affected_frameworks", "affected_documents",
            "affected_policies",
            "owner", "status", "target_date", "implemented_at",
        ]
        widgets = {
            "change_type": forms.Select(attrs=_FORM_SELECT),
            "title": forms.TextInput(attrs=_FORM_CONTROL),
            "description": forms.Textarea(attrs={**_FORM_CONTROL, "rows": 3}),
            "impact_analysis": forms.Textarea(attrs={**_FORM_CONTROL, "rows": 3}),
            "affected_scopes": forms.SelectMultiple(attrs={**_FORM_SELECT, "size": 4}),
            "affected_frameworks": forms.SelectMultiple(attrs={**_FORM_SELECT, "size": 4}),
            "affected_documents": forms.SelectMultiple(attrs={**_FORM_SELECT, "size": 4}),
            "affected_policies": forms.Textarea(attrs={**_FORM_CONTROL, "rows": 2}),
            "owner": forms.Select(attrs=_FORM_SELECT),
            "status": forms.Select(attrs=_FORM_SELECT),
            "target_date": forms.DateInput(attrs=_FORM_DATE),
            "implemented_at": forms.DateInput(attrs=_FORM_DATE),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["owner"].queryset = User.objects.filter(
            is_active=True,
        ).order_by("last_name", "first_name", "email")
        editing = bool(self.instance and self.instance.pk)
        self.fields["affected_scopes"].queryset = linkable_or_linked(
            Scope.objects.all(), self.instance.affected_scopes.all() if editing else None,
        ).order_by("name")
        self.fields["affected_frameworks"].queryset = Framework.objects.order_by(
            "short_name", "name",
        )
        # RG-DOC-20 : new links target active documents; a link to a document
        # retired since is kept rather than silently dropped on save.
        self.fields["affected_documents"].queryset = linkable_or_linked(
            Policy.objects.all(), self.instance.affected_documents.all() if editing else None,
        ).order_by("reference")
        self.fields["affected_policies"].help_text = _(
            "Free text, kept for changes recorded before the documents register. "
            "Link governed documents above."
        )


class ManagementReviewCommentForm(forms.ModelForm):
    class Meta:
        model = ManagementReviewComment
        fields = ["content"]
        widgets = {
            "content": forms.Textarea(attrs={
                **_FORM_CONTROL, "rows": 2,
                "placeholder": _("Write a comment"),
                "aria-label": _("Write a comment"),
            }),
        }


class ParticipantSignatureForm(forms.Form):
    """Upload a PNG signature image for a participant.

    The image is stored as a base64 data URI in the participant's
    `signature_data` field and embedded in the DOCX export. This is a
    graphical (non-qualified) signature, not an eIDAS qualified one.
    """

    signature_image = forms.ImageField(
        label=_("Signature image"),
        help_text=_("Upload a PNG or JPEG image of your signature (max 500 KB)."),
        widget=forms.ClearableFileInput(attrs={
            "class": "form-control",
            "accept": "image/png,image/jpeg",
        }),
    )

    def clean_signature_image(self):
        image = self.cleaned_data["signature_image"]
        max_size = 500 * 1024
        if image.size > max_size:
            raise forms.ValidationError(
                _("Signature image must be smaller than 500 KB."),
            )
        return image


class DecisionPromoteForm(forms.Form):
    """Promote a decision into a ComplianceActionPlan."""

    name = forms.CharField(
        label=_("Action plan name"),
        max_length=255,
        widget=forms.TextInput(attrs=_FORM_CONTROL),
    )
    priority = forms.ChoiceField(
        label=_("Priority"),
        choices=DecisionPriority.choices,
        widget=forms.Select(attrs=_FORM_SELECT),
    )
    target_date = forms.DateField(
        label=_("Target date"),
        widget=forms.DateInput(attrs=_FORM_DATE),
    )
    gap_description = forms.CharField(
        label=_("Gap description"),
        widget=forms.Textarea(attrs={**_FORM_CONTROL, "rows": 3}),
    )
    remediation_plan = forms.CharField(
        label=_("Remediation plan"),
        widget=forms.Textarea(attrs={**_FORM_CONTROL, "rows": 3}),
    )
    owner = forms.ModelChoiceField(
        label=_("Supervisor"),
        queryset=User.objects.filter(is_active=True).order_by(
            "last_name", "first_name", "email",
        ),
        widget=forms.Select(attrs=_FORM_SELECT),
    )
