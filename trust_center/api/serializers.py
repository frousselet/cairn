"""Serializers for the Trust Center.

Two strictly separated families:

* **Public** serializers (``Public*``) read from the curation link models and a
  minimal, hardcoded projection of the source object. They expose ONLY a small
  whitelist of fields, are read-only, and sanitize any SVG. They must never be
  reused for internal data and must never gain a ``__all__`` / ``exclude``.
* **Management** serializers are the internal CRUD serializers used behind
  authentication + ``ModulePermission``.
"""

from rest_framework import serializers

from trust_center.models import (
    TrustCenterCertification,
    TrustCenterDocument,
    TrustCenterMeasure,
    TrustCenterSettings,
    TrustCenterSubprocessor,
)
from trust_center.sanitizers import clean_html, logo_html


def _pick_logo(obj):
    """Return a safe logo for a source object (data-URI <img> or inline SVG)."""
    if obj is None:
        return ""
    raw = getattr(obj, "logo_64", "") or getattr(obj, "logo", "")
    return logo_html(raw)


# --- Public serializers (whitelisted, read-only) ----------------------------


class PublicCertificationSerializer(serializers.Serializer):
    label = serializers.CharField(source="public_label", read_only=True)
    description = serializers.SerializerMethodField()
    compliance_level = serializers.IntegerField(
        source="public_compliance_level", read_only=True, allow_null=True
    )
    logo = serializers.SerializerMethodField()

    def get_description(self, obj):
        return clean_html(obj.public_description)

    def get_logo(self, obj):
        return _pick_logo(obj.framework)


class PublicSubprocessorSerializer(serializers.Serializer):
    name = serializers.CharField(source="public_name", read_only=True)
    purpose = serializers.CharField(read_only=True)
    country = serializers.CharField(source="public_country", read_only=True)
    website = serializers.CharField(source="public_website", read_only=True)
    logo = serializers.SerializerMethodField()

    def get_logo(self, obj):
        return _pick_logo(obj.supplier)


class PublicMeasureSerializer(serializers.Serializer):
    title = serializers.CharField(read_only=True)
    description = serializers.SerializerMethodField()
    icon = serializers.CharField(read_only=True)
    category = serializers.CharField(source="get_category_display", read_only=True)

    def get_description(self, obj):
        return clean_html(obj.description)


class PublicDocumentSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    title = serializers.CharField(read_only=True)
    description = serializers.SerializerMethodField()
    access = serializers.CharField(read_only=True)
    requires_nda = serializers.BooleanField(read_only=True)

    def get_description(self, obj):
        return clean_html(obj.description)


# --- Management serializers (internal CRUD) ---------------------------------

_BASE_READ_ONLY = ["id", "reference", "workflow_state", "is_approved", "created_at", "updated_at"]


class TrustCenterSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrustCenterSettings
        fields = [
            "id",
            "is_published",
            "headline",
            "intro",
            "contact_email",
            "show_compliance_percentages",
            "theme_accent",
            "custom_domain",
            "updated_at",
        ]
        read_only_fields = ["id", "updated_at"]


class CertificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrustCenterCertification
        fields = [
            *_BASE_READ_ONLY,
            "framework",
            "public_label",
            "public_description",
            "show_percentage",
            "display_order",
        ]
        read_only_fields = _BASE_READ_ONLY


class SubprocessorSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrustCenterSubprocessor
        fields = [
            *_BASE_READ_ONLY,
            "supplier",
            "public_name",
            "purpose",
            "public_country",
            "public_website",
            "display_order",
        ]
        read_only_fields = _BASE_READ_ONLY


class MeasureSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrustCenterMeasure
        fields = [
            *_BASE_READ_ONLY,
            "title",
            "description",
            "icon",
            "category",
            "display_order",
        ]
        read_only_fields = _BASE_READ_ONLY


class DocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrustCenterDocument
        fields = [
            *_BASE_READ_ONLY,
            "title",
            "description",
            "access",
            "requires_nda",
            "report",
            "file_name",
            "display_order",
        ]
        read_only_fields = _BASE_READ_ONLY

    def validate(self, attrs):
        # The inline-upload source is UI-only; via the API a document must
        # reference a generated report (mirrors the model's clean() invariant).
        report = attrs.get("report", getattr(self.instance, "report", None))
        if report is None:
            raise serializers.ValidationError(
                {"report": "A source report is required when creating a document via the API."}
            )
        return attrs


class TransitionSerializer(serializers.Serializer):
    target_state = serializers.CharField()
    comment = serializers.CharField(required=False, allow_blank=True, default="")
