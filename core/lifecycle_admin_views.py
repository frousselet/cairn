"""Cairn admin screens to view and customize the JSON lifecycle definitions.

Lives under Administration -> Lifecycles. Editing a definition here re-shapes the
stepper, the allowed transitions and the governance flags for every entity bound
to that lifecycle, with no code change : the JSON is the single source of truth.
"""

import json

from django import forms
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import ListView, UpdateView, View

from core.lifecycle import (
    LIFECYCLE_REGISTRY,
    LifecycleError,
    lifecycle_from_json,
    lifecycle_to_json,
)
from core.models import LifecycleDefinition


class LifecycleDefinitionForm(forms.ModelForm):
    definition_text = forms.CharField(
        label=_("Definition (JSON)"),
        widget=forms.Textarea(attrs={"rows": 22, "class": "form-control font-monospace no-richtext", "spellcheck": "false"}),
        help_text=_(
            "A JSON object with \"steps\" and \"transitions\". Exactly one step of "
            "kind \"draft\" (the entry) and at least one of kind \"archived\" (the "
            "exit). A transition source may be \"*\" for \"from any state\"."
        ),
    )

    class Meta:
        model = LifecycleDefinition
        fields = ["label"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["label"].widget.attrs.setdefault("class", "form-control")
        if self.instance and self.instance.pk and not self.is_bound:
            self.fields["definition_text"].initial = json.dumps(
                self.instance.definition, indent=2, ensure_ascii=False
            )

    def clean_definition_text(self):
        raw = self.cleaned_data["definition_text"]
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise forms.ValidationError(_("Invalid JSON: %(err)s") % {"err": exc}) from None
        try:
            lifecycle_from_json(self.instance.name, data)
        except LifecycleError as exc:
            raise forms.ValidationError(str(exc)) from None
        except (KeyError, TypeError, AttributeError) as exc:
            raise forms.ValidationError(_("Malformed definition: %(err)s") % {"err": exc}) from None
        self._definition = data
        return raw

    def save(self, commit=True):
        obj = super().save(commit=False)
        obj.definition = self._definition
        obj.is_customized = True
        if commit:
            obj.save()
        return obj


class LifecycleDefinitionListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = LifecycleDefinition
    permission_required = "system.config.read"
    template_name = "core/lifecycle_list.html"
    context_object_name = "definitions"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        for d in ctx["definitions"]:
            d.step_count = len(d.definition.get("steps", []))
            d.transition_count = len(d.definition.get("transitions", []))
        return ctx


class LifecycleDefinitionUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = LifecycleDefinition
    form_class = LifecycleDefinitionForm
    permission_required = "system.config.read"
    template_name = "core/lifecycle_form.html"
    slug_field = "name"
    slug_url_kwarg = "name"

    def get_success_url(self):
        return reverse("core:lifecycle-edit", kwargs={"name": self.object.name})

    def form_valid(self, form):
        messages.success(self.request, _("Lifecycle \"%(name)s\" updated.") % {"name": self.object.name})
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        # Feed the graphical editor the current definition + the vocabularies it
        # offers in its dropdowns (step kinds, tones).
        source = self.object.definition
        if self.request.method == "POST":
            raw = self.request.POST.get("definition_text")
            if raw:
                try:
                    source = json.loads(raw)
                except json.JSONDecodeError:
                    source = self.object.definition
        ctx["definition_json"] = json.dumps(source)
        ctx["step_kinds"] = ["draft", "intermediate", "archived"]
        ctx["tones"] = [
            "neutral", "secondary", "info", "primary", "success", "warning", "danger", "dark", "muted",
        ]
        return ctx


class LifecycleDefinitionResetView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Reset a system lifecycle back to its code-declared default."""

    permission_required = "system.config.read"

    def post(self, request, name):
        obj = get_object_or_404(LifecycleDefinition, name=name)
        lifecycle = LIFECYCLE_REGISTRY.get(name)
        if lifecycle is not None:
            obj.definition = lifecycle_to_json(lifecycle)
            obj.is_customized = False
            obj.save()
            messages.success(request, _("Lifecycle \"%(name)s\" reset to its default.") % {"name": name})
        else:
            messages.error(request, _("No code default is registered for this lifecycle."))
        return redirect("core:lifecycle-edit", name=name)
