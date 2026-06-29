from django.urls import reverse
from rest_framework import serializers

from assets.models import (
    AssetDependency,
    AssetGroup,
    AssetValuation,
    Certificate,
    Contract,
    EssentialAsset,
    Supplier,
    SupplierContact,
    SupplierDependency,
    SupplierRequirement,
    SupportAsset,
)
from assets.models.supplier import SupplierType


class AssetValuationSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssetValuation
        fields = [
            "id", "essential_asset", "evaluation_date",
            "confidentiality_level", "integrity_level", "availability_level",
            "evaluated_by", "justification", "context", "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class AssetDependencySerializer(serializers.ModelSerializer):
    essential_asset_name = serializers.CharField(
        source="essential_asset.name", read_only=True
    )
    support_asset_name = serializers.CharField(
        source="support_asset.name", read_only=True
    )

    class Meta:
        model = AssetDependency
        fields = [
            "id", "reference", "essential_asset", "essential_asset_name",
            "support_asset", "support_asset_name",
            "dependency_type", "criticality", "description",
            "is_single_point_of_failure", "redundancy_level",
            "version",
            "is_approved", "approved_by", "approved_at",
            "created_by", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "reference", "is_single_point_of_failure", "created_by", "created_at", "updated_at", "is_approved", "approved_by", "approved_at", "version"]


class EssentialAssetSerializer(serializers.ModelSerializer):
    class Meta:
        model = EssentialAsset
        fields = [
            "id", "scopes", "reference", "name", "description",
            "type", "category", "owner", "custodian",
            "confidentiality_level", "integrity_level", "availability_level",
            "confidentiality_justification", "integrity_justification",
            "availability_justification",
            "max_tolerable_downtime", "recovery_time_objective",
            "recovery_point_objective",
            "data_classification", "personal_data",
            "personal_data_categories", "regulatory_constraints",
            "related_activities", "status", "review_date", "tags",
            "version",
            "is_approved", "approved_by", "approved_at",
            "created_by", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "reference", "created_by", "created_at", "updated_at", "is_approved", "approved_by", "approved_at", "version"]


class EssentialAssetListSerializer(serializers.ModelSerializer):
    owner_name = serializers.CharField(source="owner.get_full_name", read_only=True)

    class Meta:
        model = EssentialAsset
        fields = [
            "id", "scopes", "reference", "name", "type", "category",
            "owner", "owner_name",
            "confidentiality_level", "integrity_level", "availability_level",
            "data_classification", "personal_data", "status", "created_at",
        ]
        read_only_fields = ["id", "reference", "created_at"]


class SupportAssetSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupportAsset
        fields = [
            "id", "scopes", "reference", "name", "description",
            "type", "category", "owner", "custodian",
            "location", "manufacturer", "model_name", "serial_number",
            "software_version", "ip_address", "hostname", "operating_system",
            "acquisition_date", "end_of_life_date", "warranty_expiry_date",
            "contract_reference",
            "inherited_confidentiality", "inherited_integrity",
            "inherited_availability",
            "exposure_level", "environment",
            "parent_asset", "status", "review_date", "tags",
            "version",
            "is_approved", "approved_by", "approved_at",
            "created_by", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "reference", "created_by", "created_at", "updated_at",
            "inherited_confidentiality", "inherited_integrity",
            "inherited_availability",
            "is_approved", "approved_by", "approved_at",
            "version",
        ]


class SupportAssetListSerializer(serializers.ModelSerializer):
    owner_name = serializers.CharField(source="owner.get_full_name", read_only=True)

    class Meta:
        model = SupportAsset
        fields = [
            "id", "scopes", "reference", "name", "type", "category",
            "owner", "owner_name",
            "inherited_confidentiality", "inherited_integrity",
            "inherited_availability",
            "environment", "exposure_level", "status",
            "end_of_life_date", "created_at",
        ]
        read_only_fields = ["id", "reference", "created_at"]


class AssetGroupSerializer(serializers.ModelSerializer):
    member_count = serializers.IntegerField(
        source="members.count", read_only=True
    )

    class Meta:
        model = AssetGroup
        fields = [
            "id", "scopes", "name", "description", "type",
            "members", "owner", "status", "member_count", "tags",
            "version",
            "is_approved", "approved_by", "approved_at",
            "created_by", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_by", "created_at", "updated_at", "is_approved", "approved_by", "approved_at", "version"]


class AssetGroupListSerializer(serializers.ModelSerializer):
    member_count = serializers.IntegerField(
        source="members.count", read_only=True
    )

    class Meta:
        model = AssetGroup
        fields = [
            "id", "scopes", "name", "type", "owner",
            "status", "member_count", "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class SupplierRequirementSerializer(serializers.ModelSerializer):
    requirement_reference = serializers.CharField(
        source="requirement.reference", read_only=True, default=None
    )

    class Meta:
        model = SupplierRequirement
        fields = [
            "id", "supplier", "requirement", "requirement_reference",
            "title", "description",
            "compliance_status", "evidence", "due_date",
            "verified_at", "verified_by",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class SupplierContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupplierContact
        fields = [
            "id", "supplier", "name", "profession", "service",
            "email", "phone", "role",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class SupplierSerializer(serializers.ModelSerializer):
    type = serializers.PrimaryKeyRelatedField(
        queryset=SupplierType.objects.all(),
        required=False,
        allow_null=True,
    )
    requirement_count = serializers.IntegerField(
        source="requirements.count", read_only=True
    )

    class Meta:
        model = Supplier
        fields = [
            "id", "scopes", "reference", "name", "description",
            "type", "criticality", "owner",
            "contact_name", "contact_email", "contact_phone",
            "website", "address", "country", "latitude", "longitude",
            "contract_reference", "contract_start_date", "contract_end_date",
            "status", "notes", "tags",
            "requirement_count",
            "version",
            "is_approved", "approved_by", "approved_at",
            "created_by", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "reference", "created_by", "created_at", "updated_at",
            "is_approved", "approved_by", "approved_at", "version",
        ]


class SupplierListSerializer(serializers.ModelSerializer):
    owner_name = serializers.CharField(source="owner.get_full_name", read_only=True)
    requirement_count = serializers.IntegerField(
        source="requirements.count", read_only=True
    )

    class Meta:
        model = Supplier
        fields = [
            "id", "scopes", "reference", "name", "type", "criticality",
            "owner", "owner_name", "logo_32",
            "status", "contract_end_date", "requirement_count",
            "created_at",
        ]
        read_only_fields = ["id", "reference", "created_at"]


class SupplierDependencySerializer(serializers.ModelSerializer):
    support_asset_name = serializers.CharField(
        source="support_asset.name", read_only=True
    )
    supplier_name = serializers.CharField(
        source="supplier.name", read_only=True
    )

    class Meta:
        model = SupplierDependency
        fields = [
            "id", "reference", "support_asset", "support_asset_name",
            "supplier", "supplier_name",
            "dependency_type", "criticality", "description",
            "version",
            "is_approved", "approved_by", "approved_at",
            "created_by", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "reference", "created_by", "created_at", "updated_at",
            "is_approved", "approved_by", "approved_at", "version",
        ]


class ContractSerializer(serializers.ModelSerializer):
    """Full contract representation (the inline PDF bytes are never exposed)."""

    document_url = serializers.SerializerMethodField()

    class Meta:
        model = Contract
        fields = [
            "id", "scopes", "reference", "label", "status",
            "start_date", "end_date", "amount", "currency",
            "parent", "supersedes", "suppliers", "clients", "notes", "tags",
            "file_name", "content_type", "document_url",
            "version",
            "is_approved", "approved_by", "approved_at",
            "created_by", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "reference", "file_name", "content_type", "document_url",
            "created_by", "created_at", "updated_at",
            "is_approved", "approved_by", "approved_at", "version",
        ]

    def get_document_url(self, obj):
        if not obj.has_document:
            return None
        return reverse("assets:contract-document", kwargs={"pk": obj.pk})


class ContractListSerializer(serializers.ModelSerializer):
    has_document = serializers.BooleanField(read_only=True)

    class Meta:
        model = Contract
        fields = [
            "id", "scopes", "reference", "label", "status",
            "start_date", "end_date", "amount", "currency",
            "parent", "has_document", "created_at",
        ]
        read_only_fields = ["id", "reference", "created_at"]


class CertificateSerializer(serializers.ModelSerializer):
    """Full certificate representation (the inline PDF bytes are never exposed)."""

    document_url = serializers.SerializerMethodField()
    framework_label = serializers.CharField(read_only=True)

    class Meta:
        model = Certificate
        fields = [
            "id", "scopes", "reference", "label",
            "framework", "framework_label", "status",
            "certificate_number", "issuer", "issue_date", "expiry_date",
            "scope_statement", "sites", "supersedes", "notes", "tags",
            "file_name", "content_type", "document_url",
            "version",
            "is_approved", "approved_by", "approved_at",
            "created_by", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "reference", "framework_label",
            "file_name", "content_type", "document_url",
            "created_by", "created_at", "updated_at",
            "is_approved", "approved_by", "approved_at", "version",
        ]

    def get_document_url(self, obj):
        if not obj.has_document:
            return None
        return reverse("assets:certificate-document", kwargs={"pk": obj.pk})


class CertificateListSerializer(serializers.ModelSerializer):
    has_document = serializers.BooleanField(read_only=True)
    framework_label = serializers.CharField(read_only=True)

    class Meta:
        model = Certificate
        fields = [
            "id", "scopes", "reference", "label",
            "framework", "framework_label", "status",
            "issuer", "issue_date", "expiry_date",
            "has_document", "created_at",
        ]
        read_only_fields = ["id", "reference", "framework_label", "created_at"]
