from django.contrib.auth import authenticate, login, logout
from django.utils import timezone
from django.utils.translation import gettext as _
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.api.filters import AccessLogFilter, PermissionFilter, UserFilter
from accounts.api.permissions import ModulePermission
from accounts.api.serializers import (
    AccessLogSerializer,
    CompanySettingsSerializer,
    GroupSerializer,
    LoginSerializer,
    MeSerializer,
    PermissionSerializer,
    SavedFilterSerializer,
    UserCreateSerializer,
    UserDetailSerializer,
    UserListSerializer,
)
from accounts.constants import AccessEventType, FailureReason
from accounts.models import AccessLog, CompanySettings, Group, Permission, SavedFilter, User


# ── Auth API Views ──────────────────────────────────────────

class LoginAPIView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]
        password = serializer.validated_data["password"]

        user = authenticate(request, username=email, password=password)
        if user is not None:
            refresh = RefreshToken.for_user(user)
            # Log via signal fires from authenticate, but we need to
            # manually fire login signal for session-less JWT
            AccessLog.objects.create(
                user=user,
                email_attempted=email,
                event_type=AccessEventType.LOGIN_SUCCESS,
                ip_address=_get_client_ip(request),
                user_agent=request.META.get("HTTP_USER_AGENT", ""),
            )
            user.reset_failed_attempts()

            permissions = sorted(
                Permission.objects.filter(groups__users=user).values_list("codename", flat=True).distinct()
            )
            return Response({
                "status": "success",
                "data": {
                    "access_token": str(refresh.access_token),
                    "refresh_token": str(refresh),
                    "user": {
                        "id": str(user.id),
                        "email": user.email,
                        "display_name": user.display_name,
                        "language": user.language,
                        "theme_preference": user.theme_preference,
                        "permissions": permissions,
                    },
                },
            })
        else:
            # Determine error type
            try:
                u = User.objects.get(email__iexact=email)
                if u.is_locked:
                    return Response({
                        "status": "error",
                        "error": {
                            "code": "ACCOUNT_LOCKED",
                            "message": "Le compte est temporairement verrouillé.",
                            "details": {
                                "locked_until": u.locked_until.isoformat() if u.locked_until else None,
                            },
                        },
                    }, status=status.HTTP_403_FORBIDDEN)
            except User.DoesNotExist:
                pass

            return Response({
                "status": "error",
                "error": {
                    "code": "AUTHENTICATION_FAILED",
                    "message": "Email ou mot de passe invalide.",
                },
            }, status=status.HTTP_401_UNAUTHORIZED)


class LogoutAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get("refresh_token")
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
        except Exception:
            pass

        AccessLog.objects.create(
            user=request.user,
            email_attempted=request.user.email,
            event_type=AccessEventType.LOGOUT,
            ip_address=_get_client_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
        )
        return Response({"status": "success"})


class MeAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = MeSerializer(request.user)
        return Response({"status": "success", "data": serializer.data})

    def patch(self, request):
        serializer = MeSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"status": "success", "data": serializer.data})


class DashboardLayoutAPIView(APIView):
    """Read and update the authenticated user's configurable dashboard layout.

    GET returns the resolved layout (every registered widget exactly once, in
    the user's order, with sizes clamped to each widget's allowed set) plus the
    catalogue of available widgets. PUT replaces the layout; the payload is
    sanitised against the widget registry so it can never be corrupted.
    """

    permission_classes = [IsAuthenticated]

    def _catalogue(self):
        from core.dashboard import DASHBOARD_WIDGETS

        return [
            {
                "id": w.id,
                "title": str(w.title),
                "icon": w.icon,
                "category": str(w.category),
                "sizes": list(w.sizes),
                "default_size": w.default_size,
                "default_zone": w.default_zone,
                "multiple": w.multiple,
                "description": str(w.description),
            }
            for w in DASHBOARD_WIDGETS
        ]

    def get(self, request):
        from core.dashboard import resolve_layout

        return Response({
            "status": "success",
            "data": {
                "layout": resolve_layout(request.user.dashboard_layout),
                "widgets": self._catalogue(),
            },
        })

    def put(self, request):
        from core.dashboard import sanitize_layout

        layout = sanitize_layout(request.data.get("layout"))
        request.user.dashboard_layout = layout
        request.user.save(update_fields=["dashboard_layout"])
        return Response({"status": "success", "data": {"layout": layout}})


class TokenRefreshAPIView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        refresh_token = request.data.get("refresh_token")
        if not refresh_token:
            return Response(
                {"status": "error", "error": {"code": "MISSING_TOKEN", "message": "refresh_token requis."}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            old_refresh = RefreshToken(refresh_token)
            # Blacklist old token (rotation)
            old_refresh.blacklist()
            user_id = old_refresh["user_id"]
            user = User.objects.get(pk=user_id)
            new_refresh = RefreshToken.for_user(user)
            return Response({
                "status": "success",
                "data": {
                    "access_token": str(new_refresh.access_token),
                    "refresh_token": str(new_refresh),
                },
            })
        except Exception:
            return Response(
                {"status": "error", "error": {"code": "INVALID_TOKEN", "message": "Token invalide ou expiré."}},
                status=status.HTTP_401_UNAUTHORIZED,
            )


# ── Resource ViewSets ───────────────────────────────────────

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    permission_classes = [IsAuthenticated, ModulePermission]
    permission_module = "system"
    permission_feature = "users"
    filterset_class = UserFilter
    search_fields = ["email", "first_name", "last_name"]
    ordering_fields = ["email", "last_name", "created_at", "last_login"]

    def get_serializer_class(self):
        if self.action == "list":
            return UserListSerializer
        if self.action == "create":
            return UserCreateSerializer
        return UserDetailSerializer

    @action(detail=True, methods=["get"])
    def groups(self, request, pk=None):
        user = self.get_object()
        groups = user.custom_groups.all()
        serializer = GroupSerializer(groups, many=True)
        return Response({"status": "success", "data": serializer.data})

    @action(detail=True, methods=["get"])
    def permissions(self, request, pk=None):
        user = self.get_object()
        perms = sorted(
            Permission.objects.filter(groups__users=user).values_list("codename", flat=True).distinct()
        )
        return Response({"status": "success", "data": perms})


class GroupViewSet(viewsets.ModelViewSet):
    queryset = Group.objects.all()
    serializer_class = GroupSerializer
    permission_classes = [IsAuthenticated, ModulePermission]
    permission_module = "system"
    permission_feature = "groups"
    search_fields = ["name"]

    def destroy(self, request, *args, **kwargs):
        group = self.get_object()
        if group.users.exists():
            return Response(
                {"status": "error", "error": {"message": _("This group still has users. Remove all users before deleting.")}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=["get", "post"])
    def permissions(self, request, pk=None):
        group = self.get_object()
        if request.method == "GET":
            perms = group.permissions.all()
            serializer = PermissionSerializer(perms, many=True)
            return Response({"status": "success", "data": serializer.data})
        # POST: add permissions by codename list
        codenames = request.data.get("permissions", [])
        perms = Permission.objects.filter(codename__in=codenames)
        group.permissions.add(*perms)
        return Response({"status": "success"})

    @action(detail=True, methods=["get", "post"])
    def users(self, request, pk=None):
        group = self.get_object()
        if request.method == "GET":
            users = group.users.all()
            serializer = UserListSerializer(users, many=True)
            return Response({"status": "success", "data": serializer.data})
        # POST: add users by ID list
        user_ids = request.data.get("users", [])
        users = User.objects.filter(pk__in=user_ids)
        group.users.add(*users)
        return Response({"status": "success"})


class PermissionViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    queryset = Permission.objects.all()
    serializer_class = PermissionSerializer
    permission_classes = [IsAuthenticated, ModulePermission]
    permission_module = "system"
    permission_feature = "groups"
    filterset_class = PermissionFilter
    search_fields = ["codename", "name"]

    @action(detail=False, methods=["get"])
    def by_module(self, request):
        """Permissions grouped by module then feature."""
        from accounts.constants import MODULE_LABELS, PERMISSION_REGISTRY

        result = {}
        for perm in Permission.objects.all():
            mod = perm.module
            if mod not in result:
                result[mod] = {"label": MODULE_LABELS.get(mod, mod), "features": {}}
            feat = perm.feature
            if feat not in result[mod]["features"]:
                feat_info = PERMISSION_REGISTRY.get(mod, {}).get(feat, {})
                result[mod]["features"][feat] = {
                    "label": feat_info.get("label", feat),
                    "permissions": [],
                }
            result[mod]["features"][feat]["permissions"].append(
                PermissionSerializer(perm).data
            )
        return Response({"status": "success", "data": result})


class AccessLogViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    queryset = AccessLog.objects.select_related("user")
    serializer_class = AccessLogSerializer
    permission_classes = [IsAuthenticated, ModulePermission]
    permission_module = "system"
    permission_feature = "audit_trail"
    filterset_class = AccessLogFilter
    ordering_fields = ["timestamp"]


# ── Company Settings ────────────────────────────────────────

class CompanySettingsAPIView(APIView):
    permission_classes = [IsAuthenticated, ModulePermission]
    permission_module = "system"
    permission_feature = "config"

    def get(self, request):
        instance = CompanySettings.get()
        serializer = CompanySettingsSerializer(instance)
        return Response({"status": "success", "data": serializer.data})

    def patch(self, request):
        instance = CompanySettings.get()
        serializer = CompanySettingsSerializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"status": "success", "data": serializer.data})


# ── Helpers ─────────────────────────────────────────────────

def _get_client_ip(request):
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


class NotificationViewSet(
    mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet
):
    """The authenticated user's own notifications (own-data, no module permission)."""

    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        from accounts.api.serializers import NotificationSerializer

        return NotificationSerializer

    def get_queryset(self):
        qs = self.request.user.notifications.all()
        if self.request.query_params.get("unread") in ("1", "true", "True"):
            qs = qs.filter(is_read=False)
        return qs

    @action(detail=False, methods=["get"])
    def unread_count(self, request):
        return Response({"unread": request.user.notifications.filter(is_read=False).count()})

    @action(detail=True, methods=["post"])
    def mark_read(self, request, pk=None):
        notification = self.get_object()
        notification.mark_read()
        return Response({"id": str(notification.pk), "is_read": True})

    @action(detail=False, methods=["post"])
    def mark_all_read(self, request):
        updated = request.user.notifications.filter(is_read=False).update(
            is_read=True, read_at=timezone.now()
        )
        return Response({"marked_read": updated})


class SavedFilterViewSet(viewsets.ModelViewSet):
    """Per-user named list filters; reads include filters shared with everyone,
    but only the owner may modify or delete one. Filter by ?view_key=."""

    serializer_class = SavedFilterSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        from django.db.models import Q

        user = self.request.user
        qs = SavedFilter.objects.filter(Q(owner=user) | Q(is_shared=True)).select_related("owner")
        view_key = self.request.query_params.get("view_key")
        if view_key:
            qs = qs.filter(view_key=view_key)
        return qs

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    def _assert_owner(self, instance):
        from rest_framework.exceptions import PermissionDenied

        if instance.owner_id != self.request.user.id:
            raise PermissionDenied("Only the owner can modify this saved filter.")

    def perform_update(self, serializer):
        self._assert_owner(serializer.instance)
        serializer.save()

    def perform_destroy(self, instance):
        self._assert_owner(instance)
        instance.delete()
