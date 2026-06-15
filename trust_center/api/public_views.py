"""Public, unauthenticated Trust Center API.

All views here are AllowAny + anonymous-throttled and read exclusively from the
``published()`` querysets (the dual gate) and the public serializers (the field
whitelist). The global ``TrustCenterSettings.is_published`` kill switch is
enforced by :func:`_require_published`, which 404s the whole surface when off.
"""

from django.http import Http404
from rest_framework.generics import ListAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from accounts.models import CompanySettings
from trust_center.models import (
    TrustCenterCertification,
    TrustCenterDocument,
    TrustCenterMeasure,
    TrustCenterSettings,
    TrustCenterSubprocessor,
)
from trust_center.sanitizers import clean_html, clean_svg

from .serializers import (
    PublicCertificationSerializer,
    PublicDocumentSerializer,
    PublicMeasureSerializer,
    PublicSubprocessorSerializer,
)


def require_published():
    """Return the settings singleton, or raise 404 when the Trust Center is off."""
    settings_obj = TrustCenterSettings.get()
    if not settings_obj.is_published:
        raise Http404()
    return settings_obj


class _PublicBase:
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [AnonRateThrottle]
    pagination_class = None


class TrustCenterPublicView(_PublicBase, APIView):
    """Aggregate payload for the public Trust Center page."""

    def get(self, request):
        settings_obj = require_published()
        company = CompanySettings.get()
        return Response(
            {
                "settings": {
                    "headline": settings_obj.headline,
                    "intro": clean_html(settings_obj.intro),
                    "contact_email": settings_obj.contact_email,
                    "theme_accent": settings_obj.theme_accent,
                    "show_compliance_percentages": settings_obj.show_compliance_percentages,
                },
                "company": {
                    "name": company.name,
                    "logo": clean_svg(company.logo_128 or company.logo),
                },
                "certifications": PublicCertificationSerializer(
                    TrustCenterCertification.objects.published().select_related("framework"),
                    many=True,
                ).data,
                "subprocessors": PublicSubprocessorSerializer(
                    TrustCenterSubprocessor.objects.published().select_related("supplier"),
                    many=True,
                ).data,
                "measures": PublicMeasureSerializer(
                    TrustCenterMeasure.objects.published(), many=True
                ).data,
                "documents": PublicDocumentSerializer(
                    TrustCenterDocument.objects.published(), many=True
                ).data,
            }
        )


class PublicCertificationListView(_PublicBase, ListAPIView):
    serializer_class = PublicCertificationSerializer

    def get_queryset(self):
        require_published()
        return TrustCenterCertification.objects.published().select_related("framework")


class PublicSubprocessorListView(_PublicBase, ListAPIView):
    serializer_class = PublicSubprocessorSerializer

    def get_queryset(self):
        require_published()
        return TrustCenterSubprocessor.objects.published().select_related("supplier")


class PublicMeasureListView(_PublicBase, ListAPIView):
    serializer_class = PublicMeasureSerializer

    def get_queryset(self):
        require_published()
        return TrustCenterMeasure.objects.published()


class PublicDocumentListView(_PublicBase, ListAPIView):
    serializer_class = PublicDocumentSerializer

    def get_queryset(self):
        require_published()
        return TrustCenterDocument.objects.published()
