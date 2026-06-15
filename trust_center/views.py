"""Public, unauthenticated Trust Center web views.

These views intentionally omit ``LoginRequiredMixin`` (there is no global
login-required middleware in this project): the Trust Center is public. The
global ``TrustCenterSettings.is_published`` kill switch 404s everything when off.
"""

import ipaddress
from urllib.parse import quote

from django.conf import settings
from django.core import signing
from django.core.cache import cache
from django.db.models import F
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views import View
from django.views.generic import FormView, TemplateView

from accounts.models import CompanySettings
from accounts.notifications import notify_document_requested
from trust_center.constants import DocumentAccess, DocumentRequestState
from trust_center.forms import PublicDocumentRequestForm
from trust_center.models import (
    DocumentRequest,
    TrustCenterCertification,
    TrustCenterDocument,
    TrustCenterMeasure,
    TrustCenterSettings,
    TrustCenterSubprocessor,
)
from trust_center.sanitizers import clean_css


def _client_ip(request):
    """Return a valid client IP string, or None.

    X-Forwarded-For is client-controlled, so the value is validated before it
    reaches the GenericIPAddressField (an ``inet`` column on PostgreSQL rejects
    a malformed value with a hard error).
    """
    xff = request.META.get("HTTP_X_FORWARDED_FOR", "")
    candidate = (xff.split(",")[0].strip() if xff else "") or request.META.get("REMOTE_ADDR")
    if not candidate:
        return None
    try:
        return str(ipaddress.ip_address(candidate))
    except ValueError:
        return None


def _attachment_disposition(filename):
    """Build a safe Content-Disposition value (no header injection / breakout)."""
    safe = "".join(ch for ch in (filename or "") if ch not in '"\\\r\n').strip() or "document"
    return f"attachment; filename=\"{safe}\"; filename*=UTF-8''{quote(safe)}"


def _rate_ok(key, limit, window):
    """Lightweight cache-based rate limiter (best effort, per-process cache)."""
    count = cache.get(key, 0)
    if count >= limit:
        return False
    cache.set(key, count + 1, window)
    return True


class TrustCenterLandingView(TemplateView):
    template_name = "trust_center/public_landing.html"

    def get_context_data(self, **kwargs):
        settings_obj = TrustCenterSettings.get()
        if not settings_obj.is_published:
            raise Http404()
        ctx = super().get_context_data(**kwargs)
        ctx["tc"] = settings_obj
        ctx["company"] = CompanySettings.get()
        ctx["certifications"] = (
            TrustCenterCertification.objects.published().select_related("framework")
        )
        ctx["subprocessors"] = (
            TrustCenterSubprocessor.objects.published().select_related("supplier")
        )
        ctx["measures"] = TrustCenterMeasure.objects.published()
        ctx["documents"] = TrustCenterDocument.objects.published()
        return ctx


class TrustCenterPublicDocumentDownloadView(View):
    """Stream a PUBLIC trust center document, no authentication required."""

    def get(self, request, pk):
        if not TrustCenterSettings.get().is_published:
            raise Http404()
        doc = get_object_or_404(
            TrustCenterDocument.objects.published(),
            pk=pk,
            access=DocumentAccess.PUBLIC,
        )
        data = doc.get_file_bytes()
        if not data:
            raise Http404()
        resp = HttpResponse(
            data, content_type=doc.content_type or "application/octet-stream"
        )
        resp["Content-Disposition"] = _attachment_disposition(doc.effective_file_name)
        return resp


class TrustCenterCustomCSSView(View):
    """Serve the operator-supplied custom CSS as a standalone stylesheet.

    Served with ``text/css`` (not inlined in a <style> element) so there is no
    HTML context to break out of; ``clean_css`` is applied as defence in depth.
    """

    def get(self, request):
        css = clean_css(TrustCenterSettings.get().custom_css or "")
        return HttpResponse(css, content_type="text/css; charset=utf-8")


class DocumentRequestCreateView(FormView):
    """Public request form for a GATED document (no authentication)."""

    template_name = "trust_center/document_request_form.html"
    form_class = PublicDocumentRequestForm

    def dispatch(self, request, *args, **kwargs):
        if not TrustCenterSettings.get().is_published:
            raise Http404()
        self.document = get_object_or_404(
            TrustCenterDocument.objects.published(),
            pk=kwargs["pk"],
            access=DocumentAccess.GATED,
        )
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["document"] = self.document
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["document"] = self.document
        ctx["tc"] = TrustCenterSettings.get()
        ctx["company"] = CompanySettings.get()
        return ctx

    def _confirmation(self):
        return render(
            self.request,
            "trust_center/document_request_submitted.html",
            {
                "document": self.document,
                "tc": TrustCenterSettings.get(),
                "company": CompanySettings.get(),
            },
        )

    def form_valid(self, form):
        ip = _client_ip(self.request)
        if not _rate_ok(f"tc_request:{ip}", limit=5, window=3600):
            form.add_error(None, _("Too many requests. Please try again later."))
            return self.form_invalid(form)

        already_pending = DocumentRequest.objects.filter(
            document=self.document,
            email=form.cleaned_data["email"],
            workflow_state=DocumentRequestState.PENDING,
        ).exists()

        if not already_pending:
            req = DocumentRequest(
                document=self.document,
                email=form.cleaned_data["email"],
                requester_name=form.cleaned_data["requester_name"],
                company=form.cleaned_data.get("company", ""),
                reason=form.cleaned_data.get("reason", ""),
                nda_accepted=form.cleaned_data.get("nda_accepted", False),
                ip_address=ip,
                user_agent=self.request.META.get("HTTP_USER_AGENT", "")[:1000],
            )
            if req.nda_accepted:
                req.nda_accepted_at = timezone.now()
            req.save()
            notify_document_requested(req)

        # Same confirmation whether or not we deduplicated, to avoid leaking
        # which emails already have a pending request.
        return self._confirmation()


class TrustCenterGatedDownloadView(View):
    """Serve a gated document from a valid, unexpired, approved signed token."""

    def get(self, request, token):
        if not TrustCenterSettings.get().is_published:
            raise Http404()
        ttl = settings.TRUST_CENTER_DOWNLOAD_TTL
        try:
            req = DocumentRequest.resolve_token(token, max_age=ttl)
        except signing.SignatureExpired:
            return render(
                request,
                "trust_center/gated_link_expired.html",
                {"tc": TrustCenterSettings.get(), "company": CompanySettings.get()},
                status=410,
            )
        except signing.BadSignature:
            raise Http404()

        if req is None or not req.is_granted:
            raise Http404()

        # The document must still be published (an admin unpublishing or
        # archiving it revokes outstanding approved links too).
        if not TrustCenterDocument.objects.published().filter(pk=req.document_id).exists():
            raise Http404()

        data = req.document.get_file_bytes()
        if not data:
            raise Http404()

        DocumentRequest.objects.filter(pk=req.pk).update(
            download_count=F("download_count") + 1
        )
        resp = HttpResponse(
            data, content_type=req.document.content_type or "application/octet-stream"
        )
        resp["Content-Disposition"] = _attachment_disposition(req.document.effective_file_name)
        return resp
