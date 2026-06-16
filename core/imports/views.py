"""Generic upload -> preview -> confirm wizard for every registered importer."""

import logging

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.http import Http404, HttpResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views import View
from django.views.generic import FormView, TemplateView

from . import registry
from .forms import EntityImportForm

logger = logging.getLogger(__name__)

SESSION_KEY = "entity_import"


class _ImporterViewMixin:
    """Resolve the importer from the ``entity`` URL kwarg and gate permissions."""

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        importer_cls = registry.get(kwargs.get("entity"))
        self.importer = importer_cls() if importer_cls else None

    def dispatch(self, request, *args, **kwargs):
        if self.importer is None:
            raise Http404("Unknown import entity")
        return super().dispatch(request, *args, **kwargs)

    @property
    def _perm_prefix(self):
        return f"{self.importer.app_label}.{self.importer.permission_feature}"


class EntityImportView(_ImporterViewMixin, LoginRequiredMixin, PermissionRequiredMixin, FormView):
    form_class = EntityImportForm
    template_name = "imports/import.html"
    modal_template_name = "imports/import_modal.html"

    def get_permission_required(self):
        return (f"{self._perm_prefix}.create",)

    def get_template_names(self):
        # Serve the modal partial when opened in the shared HTMX drawer (GET
        # only; the form posts as a normal multipart request, so validation
        # errors fall back to the full-page template).
        headers = self.request.headers
        if (
            self.request.method == "GET"
            and headers.get("HX-Request") == "true"
            and headers.get("HX-Boosted") != "true"
            and headers.get("HX-Target") == "drawer-form-content"
        ):
            return [self.modal_template_name]
        return [self.template_name]

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["importer"] = self.importer
        ctx["entity"] = self.importer.entity_key
        ctx["verbose_name"] = self.importer.verbose_name
        ctx["verbose_name_plural"] = self.importer.verbose_name_plural
        ctx["column_docs"] = self.importer.column_docs()
        ctx["sample_url"] = reverse("imports:import-sample", args=[self.importer.entity_key])
        ctx["list_url"] = reverse(self.importer.list_url_name)
        return ctx

    def form_valid(self, form):
        uploaded = form.cleaned_data["file"]
        try:
            rows = self.importer.parse_csv(uploaded)
        except Exception as exc:
            logger.exception("Error while parsing the import file")
            form.add_error("file", _("File reading error: %(error)s") % {"error": exc})
            return self.form_invalid(form)

        result = self.importer.validate(rows, self.request.user)
        if result.fatal:
            for error in result.fatal:
                form.add_error(None, error)
            return self.form_invalid(form)

        self.request.session[SESSION_KEY] = {
            "entity": self.importer.entity_key,
            "valid": [
                {
                    "row_number": r["row_number"],
                    "raw": r["raw"],
                    "conflict": r.get("conflict"),
                }
                for r in result.valid
            ],
            "errors": result.errors,
            "warnings": result.warnings,
        }
        return redirect(reverse("imports:import-preview", args=[self.importer.entity_key]))


class EntityImportPreviewView(_ImporterViewMixin, LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    template_name = "imports/import_preview.html"

    def get_permission_required(self):
        return (f"{self._perm_prefix}.create",)

    def _session_data(self):
        data = self.request.session.get(SESSION_KEY)
        if not data or data.get("entity") != self.importer.entity_key:
            return None
        return data

    def dispatch(self, request, *args, **kwargs):
        if self.importer is None:
            raise Http404("Unknown import entity")
        if request.user.is_authenticated and self._session_data() is None:
            messages.warning(
                request,
                _("No import data in session. Please upload a file first."),
            )
            return redirect(reverse("imports:import", args=[kwargs["entity"]]))
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        data = self._session_data()
        columns = [c.name for c in self.importer.columns]

        def _cells(raw):
            return [raw.get(col, "") for col in columns]

        ctx["importer"] = self.importer
        ctx["entity"] = self.importer.entity_key
        ctx["verbose_name"] = self.importer.verbose_name
        ctx["verbose_name_plural"] = self.importer.verbose_name_plural
        ctx["columns"] = columns
        valid_rows = [
            {
                "row_number": r["row_number"],
                "cells": _cells(r["raw"]),
                "conflict": r.get("conflict"),
            }
            for r in data["valid"]
        ]
        ctx["valid_rows"] = valid_rows
        ctx["error_rows"] = [
            {"row_number": r["row_number"], "cells": _cells(r["raw"]), "messages": r["messages"]}
            for r in data["errors"]
        ]
        ctx["warnings"] = data["warnings"]
        ctx["valid_count"] = len(valid_rows)
        ctx["error_count"] = len(data["errors"])
        ctx["conflict_count"] = sum(1 for r in valid_rows if r["conflict"])
        ctx["new_count"] = sum(1 for r in valid_rows if not r["conflict"])
        return ctx

    def post(self, request, *args, **kwargs):
        data = self._session_data()
        if data is None:
            messages.warning(request, _("No import data in session."))
            return redirect(reverse("imports:import", args=[kwargs["entity"]]))

        rows = [v["raw"] for v in data["valid"]]
        result = self.importer.validate(rows, request.user)
        if result.fatal or result.errors:
            messages.error(
                request,
                _("The data could no longer be validated. Please upload the file again."),
            )
            return redirect(reverse("imports:import", args=[self.importer.entity_key]))

        # Per-row replacement decisions from the preview checkboxes.
        replace_rows = {str(r) for r in request.POST.getlist("replace")}
        for vr in result.valid:
            vr["replace"] = str(vr["row_number"]) in replace_rows

        try:
            outcome = self.importer.execute(result.valid, request.user)
        except Exception as exc:
            logger.exception("Error during %s import", self.importer.entity_key)
            messages.error(request, _("Import error: %(error)s") % {"error": exc})
            return redirect(reverse("imports:import", args=[self.importer.entity_key]))

        del request.session[SESSION_KEY]
        messages.success(
            request,
            _("Import complete: %(created)s created, %(updated)s updated, "
              "%(skipped)s skipped (%(name)s).")
            % {
                "created": len(outcome.created),
                "updated": len(outcome.updated),
                "skipped": len(outcome.skipped),
                "name": self.importer.verbose_name_plural,
            },
        )
        return redirect(reverse(self.importer.list_url_name))


class EntityImportSampleView(_ImporterViewMixin, LoginRequiredMixin, PermissionRequiredMixin, View):
    """Serve a sample CSV file for the entity."""

    def get_permission_required(self):
        return (f"{self._perm_prefix}.read",)

    def get(self, request, *args, **kwargs):
        buf = self.importer.generate_sample_csv()
        response = HttpResponse(buf.getvalue(), content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = (
            f'attachment; filename="sample_{self.importer.entity_key}.csv"'
        )
        return response
