from django.contrib.auth import password_validation
from rest_framework import serializers

from accounts.models import AccessLog, CompanySettings, Group, Notification, Permission, SavedFilter, User
from context.models import Scope


class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = ("id", "codename", "name", "module", "feature", "action", "is_system")
        read_only_fields = fields


class UserListSerializer(serializers.ModelSerializer):
    display_name = serializers.CharField(read_only=True)
    groups = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id", "user_type", "email", "first_name", "last_name", "display_name",
            "job_title", "department", "is_active", "last_login", "groups",
        )
        read_only_fields = ("id", "display_name", "last_login")

    def get_groups(self, obj):
        return list(obj.custom_groups.values_list("name", flat=True))


class UserDetailSerializer(serializers.ModelSerializer):
    display_name = serializers.CharField(read_only=True)
    groups = serializers.SerializerMethodField()
    permissions = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id", "user_type", "email", "first_name", "last_name", "display_name",
            "job_title", "department", "phone", "language", "timezone", "theme_preference",
            "is_active", "is_staff", "last_login", "created_at", "updated_at",
            "groups", "permissions",
        )
        read_only_fields = ("id", "display_name", "last_login", "created_at", "updated_at", "permissions")

    def get_groups(self, obj):
        return [{"id": str(g.id), "name": g.name} for g in obj.custom_groups.all()]

    def get_permissions(self, obj):
        return sorted(
            Permission.objects.filter(groups__users=obj).values_list("codename", flat=True).distinct()
        )


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = (
            "id", "user_type", "email", "first_name", "last_name", "password",
            "job_title", "department", "phone", "language", "timezone", "theme_preference",
            "is_active",
        )
        read_only_fields = ("id",)

    def validate_password(self, value):
        password_validation.validate_password(value)
        return value

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            user.created_by = request.user
        user.save()
        return user


class UserInviteSerializer(serializers.Serializer):
    """Provision a user without a password (invitation flow).

    The account is created with an unusable password; the response carries an
    activation link the invitee follows to set their first credential. Groups
    are matched by name. No password is ever accepted here.
    """

    email = serializers.EmailField()
    last_name = serializers.CharField(max_length=150)
    first_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    user_type = serializers.CharField(required=False)
    job_title = serializers.CharField(required=False, allow_blank=True)
    department = serializers.CharField(required=False, allow_blank=True)
    phone = serializers.CharField(required=False, allow_blank=True)
    language = serializers.CharField(required=False, allow_blank=True)
    groups = serializers.ListField(
        child=serializers.CharField(), required=False,
        help_text="Role / group names to assign (must already exist).",
    )


class GroupSerializer(serializers.ModelSerializer):
    permissions = serializers.SlugRelatedField(
        slug_field="codename",
        queryset=Permission.objects.all(),
        many=True,
        required=False,
    )
    allowed_scopes = serializers.PrimaryKeyRelatedField(
        many=True,
        required=False,
        queryset=Scope.objects.all(),
    )
    user_count = serializers.SerializerMethodField()

    class Meta:
        model = Group
        fields = (
            "id", "name", "description", "is_system", "permissions",
            "allowed_scopes", "user_count", "created_at", "updated_at",
        )
        read_only_fields = ("id", "is_system", "created_at", "updated_at")

    def get_user_count(self, obj):
        return obj.users.count()


class AccessLogSerializer(serializers.ModelSerializer):
    user_email = serializers.CharField(source="user.email", read_only=True, default=None)

    class Meta:
        model = AccessLog
        fields = (
            "id", "timestamp", "user", "user_email", "email_attempted",
            "event_type", "ip_address", "user_agent", "failure_reason", "metadata",
        )
        read_only_fields = fields


class CompanySettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompanySettings
        fields = ("id", "name", "app_name", "assistant_name", "address", "logo", "accent_color", "use_logo_as_app_brand", "updated_at")
        read_only_fields = ("id", "updated_at")


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class MeSerializer(serializers.ModelSerializer):
    display_name = serializers.CharField(read_only=True)
    permissions = serializers.SerializerMethodField()
    is_superuser = serializers.BooleanField(read_only=True)
    can_override_import_dates = serializers.SerializerMethodField()
    can_create_users = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id", "email", "first_name", "last_name", "display_name",
            "job_title", "department", "phone", "language", "timezone", "theme_preference",
            "permissions", "is_superuser",
            "can_override_import_dates", "can_create_users",
        )
        read_only_fields = (
            "id", "email", "display_name", "permissions", "is_superuser",
            "can_override_import_dates", "can_create_users",
        )

    def get_permissions(self, obj):
        return sorted(
            Permission.objects.filter(groups__users=obj).values_list("codename", flat=True).distinct()
        )

    def get_can_override_import_dates(self, obj):
        # Whether this account may preserve created_at / updated_at on import
        # (silently ignored otherwise). Superusers always may.
        return bool(obj.is_superuser or obj.has_perm("system.data_import.override_dates"))

    def get_can_create_users(self, obj):
        return bool(obj.is_superuser or obj.has_perm("system.users.create"))


class NotificationSerializer(serializers.ModelSerializer):
    actor_name = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = (
            "id", "notification_type", "title", "message", "actor_name",
            "target_url", "is_read", "read_at", "created_at",
        )
        read_only_fields = fields

    def get_actor_name(self, obj):
        return obj.actor.display_name if obj.actor else ""


class SavedFilterSerializer(serializers.ModelSerializer):
    owner_name = serializers.CharField(source="owner.display_name", read_only=True)

    class Meta:
        model = SavedFilter
        fields = (
            "id", "view_key", "name", "query", "is_shared",
            "owner", "owner_name", "created_at", "updated_at",
        )
        read_only_fields = ("id", "owner", "owner_name", "created_at", "updated_at")
