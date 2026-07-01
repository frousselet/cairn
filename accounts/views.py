from itertools import chain
from operator import attrgetter

from django.apps import apps
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import translation
from django.utils.translation import gettext as _, gettext_lazy as _lazy
from django.views import View
from django.views.generic import DetailView, ListView

from accounts.constants import PERMISSION_REGISTRY, MODULE_LABELS, AccessEventType, PermissionAction, UserType
from core.history import EntryKind, classify_record
from core.mixins import (
    AdvancedFilterMixin,
    ColumnPreferenceMixin,
    ListSummaryMixin,
    PredefinedFilterMixin,
    SavedFilterMixin,
    SortableListMixin,
    TableBodyPaginatedMixin,
)
from accounts.forms import (
    CompanySettingsForm,
    GroupForm,
    LoginForm,
    PasswordChangeForm,
    ProfileForm,
    UserCreateForm,
    UserUpdateForm,
)
from accounts.models import AccessLog, CompanySettings, Group, Permission, User
from context.models import Scope


class PermissionRequiredMixin:
    """Mixin checking custom dotted permissions (module.feature.action)."""

    permission_required = None

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(f"/accounts/login/?next={request.path}")
        if self.permission_required:
            codenames = self.permission_required
            if isinstance(codenames, str):
                codenames = [codenames]
            for codename in codenames:
                if not request.user.has_perm(codename):
                    messages.error(request, _("You do not have the required permissions."))
                    return redirect("/")
        return super().dispatch(request, *args, **kwargs)


# ── Authentication ──────────────────────────────────────────

class LoginView(View):
    def get(self, request):
        if request.user.is_authenticated:
            return redirect("/")
        form = LoginForm()
        return render(request, "accounts/login.html", {"form": form})

    def post(self, request):
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"]
            password = form.cleaned_data["password"]
            user = authenticate(request, username=email, password=password)
            if user is not None:
                login(request, user)
                from core.redirects import safe_redirect_target
                next_url = safe_redirect_target(request, request.GET.get("next"))
                return redirect(next_url)
            else:
                # Check if account is locked for better messaging
                try:
                    u = User.objects.get(email__iexact=email)
                    if u.is_locked:
                        messages.error(request, _("This account is temporarily locked due to multiple failed attempts."))
                    elif not u.is_active:
                        messages.error(request, _("Invalid credentials."))
                    else:
                        messages.error(request, _("Invalid credentials."))
                except User.DoesNotExist:
                    messages.error(request, _("Invalid credentials."))
        return render(request, "accounts/login.html", {"form": form})


class LogoutView(LoginRequiredMixin, View):
    def post(self, request):
        logout(request)
        return redirect("accounts:login")

    def get(self, request):
        logout(request)
        return redirect("accounts:login")


# ── Profile ─────────────────────────────────────────────────

class ProfileView(LoginRequiredMixin, View):
    def _get_context(self, request, form):
        groups = request.user.custom_groups.all()
        permissions = sorted(
            Permission.objects.filter(groups__users=request.user).values_list("codename", flat=True).distinct()
        )
        can_oauth = request.user.is_superuser or request.user.has_perm("system.oauth.read")
        oauth_apps = request.user.oauth_applications.order_by("-created_at") if can_oauth else []
        return {
            "form": form,
            "groups": groups,
            "permissions": permissions,
            "passkeys": request.user.passkeys.order_by("-created_at"),
            "oauth_apps": oauth_apps,
            "can_create_oauth": request.user.is_superuser or request.user.has_perm("system.oauth.create"),
        }

    def get(self, request):
        form = ProfileForm(instance=request.user)
        return render(request, "accounts/profile.html", self._get_context(request, form))

    def post(self, request):
        form = ProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            lang = form.cleaned_data.get("language", "")
            if lang:
                translation.activate(lang)
            messages.success(request, _("Profile updated."))
            response = redirect("accounts:profile")
            if lang:
                response.set_cookie(settings.LANGUAGE_COOKIE_NAME, lang)
            else:
                response.delete_cookie(settings.LANGUAGE_COOKIE_NAME)
            return response
        return render(request, "accounts/profile.html", self._get_context(request, form))


class ResetHelpersView(LoginRequiredMixin, View):
    """Reset all dismissed helpers for the current user."""

    def post(self, request):
        request.user.dismissed_helpers = []
        request.user.save(update_fields=["dismissed_helpers"])
        messages.success(request, _("Help banners have been restored."))
        return redirect("accounts:profile")


class PasswordChangeView(LoginRequiredMixin, View):
    def get(self, request):
        form = PasswordChangeForm(request.user)
        return render(request, "accounts/password_change.html", {"form": form})

    def post(self, request):
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            form.save()
            update_session_auth_hash(request, request.user)
            messages.success(request, _("Password changed successfully."))
            return redirect("accounts:profile")
        return render(request, "accounts/password_change.html", {"form": form})


# ── Company Settings ────────────────────────────────────────

class CompanySettingsView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = "system.config.read"

    def get(self, request):
        instance = CompanySettings.get()
        form = CompanySettingsForm(instance=instance)
        can_edit = request.user.is_superuser or request.user.has_perm("system.config.update")
        return render(request, "accounts/company_settings.html", {"form": form, "company": instance, "can_edit": can_edit})

    def post(self, request):
        can_edit = request.user.is_superuser or request.user.has_perm("system.config.update")
        if not can_edit:
            messages.error(request, _("You do not have the required permissions."))
            return redirect("accounts:company-settings")
        instance = CompanySettings.get()
        form = CompanySettingsForm(request.POST, request.FILES, instance=instance)
        if form.is_valid():
            form.save()
            messages.success(request, _("Company settings updated."))
            return redirect("accounts:company-settings")
        return render(request, "accounts/company_settings.html", {"form": form, "company": instance, "can_edit": can_edit})


# ── Users ───────────────────────────────────────────────────

USER_FILTER_GROUPS = [
    {"param": "type", "field": "user_type", "label": _lazy("Type"), "options": UserType.choices},
]
USER_TEXT_FILTERS = [
    {"param": "name", "field": "last_name", "label": _lazy("Name")},
    {"param": "email", "field": "email", "label": _lazy("Email")},
]
USER_COLUMNS = [
    {"key": "name", "label": _lazy("Name"), "always": True},
    {"key": "job_title", "label": _lazy("Job title")},
    {"key": "status", "label": _lazy("Status")},
    {"key": "last_login", "label": _lazy("Last login")},
    {"key": "actions", "label": _lazy("Actions"), "always": True},
]

USER_SORTABLE_FIELDS = {
    "name": "last_name",
    "email": "email",
    "status": "is_active",
    "last_login": "last_login",
}


def _user_list_kpis(base):
    """Coloured KPI tiles for the user list rail, computed from the base queryset
    (before facets)."""
    if base is None:
        return []
    return [
        {"label": _("Total"), "value": base.count(), "icon": "people", "tone": "accent"},
        {"label": _("Active"), "value": base.filter(is_active=True).count(), "icon": "person-check", "tone": "success"},
        {"label": _("Inactive"), "value": base.filter(is_active=False).count(), "icon": "person-dash", "tone": "accent"},
        {"label": _("Administrators"), "value": base.filter(is_superuser=True).count(), "icon": "shield-lock", "tone": "warning"},
    ]


class UserListView(LoginRequiredMixin, PermissionRequiredMixin, ListSummaryMixin, PredefinedFilterMixin, AdvancedFilterMixin, SavedFilterMixin, ColumnPreferenceMixin, SortableListMixin, ListView):
    model = User
    template_name = "accounts/user_list.html"
    context_object_name = "users"
    paginate_by = 50
    permission_required = "system.users.read"
    filter_groups = USER_FILTER_GROUPS
    text_filters = USER_TEXT_FILTERS
    columns = USER_COLUMNS
    sortable_fields = USER_SORTABLE_FIELDS
    default_sort = "name"
    search_fields = ["email", "first_name", "last_name"]

    def get_queryset(self):
        qs = User.objects.annotate(group_count=Count("custom_groups"))
        qs = self._apply_sorting(qs)
        qs = self.filter_queryset_predefined(qs)
        return self.filter_queryset_advanced(qs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["list_kpis"] = _user_list_kpis(getattr(self, "_summary_base_qs", None))
        return ctx


class UserTableBodyView(LoginRequiredMixin, PermissionRequiredMixin, TableBodyPaginatedMixin, PredefinedFilterMixin, AdvancedFilterMixin, SortableListMixin, ListView):
    model = User
    permission_required = "system.users.read"
    template_name = "accounts/user_table_body.html"
    context_object_name = "users"
    paginate_by = 50
    sortable_fields = USER_SORTABLE_FIELDS
    default_sort = "name"
    search_fields = ["email", "first_name", "last_name"]
    filter_groups = USER_FILTER_GROUPS
    text_filters = USER_TEXT_FILTERS

    def get_queryset(self):
        qs = User.objects.annotate(group_count=Count("custom_groups"))
        qs = self._apply_sorting(qs)
        qs = self.filter_queryset_predefined(qs)
        return self.filter_queryset_advanced(qs)


class UserDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = User
    template_name = "accounts/user_detail.html"
    context_object_name = "account_user"
    permission_required = "system.users.read"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        u = self.object
        ctx["groups"] = u.custom_groups.all()
        ctx["permissions"] = sorted(
            Permission.objects.filter(groups__users=u).values_list("codename", flat=True).distinct()
        )
        ctx["recent_access_logs"] = AccessLog.objects.filter(user=u)[:20]
        return ctx


class UserCreateView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = "system.users.create"

    def get(self, request):
        form = UserCreateForm()
        return render(request, "accounts/user_form.html", {"form": form, "title": _("Create a user")})

    def post(self, request):
        form = UserCreateForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save(commit=False)
            user.created_by = request.user
            user.save()
            messages.success(request, _("User %(name)s created.") % {"name": user.display_name})
            return redirect("accounts:user-detail", pk=user.pk)
        return render(request, "accounts/user_form.html", {"form": form, "title": _("Create a user")})


class UserUpdateView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = "system.users.update"

    def get(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        form = UserUpdateForm(instance=user)
        return render(request, "accounts/user_form.html", {"form": form, "title": _("Edit %(name)s") % {"name": user.display_name}, "object": user})

    def post(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        form = UserUpdateForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, _("User updated."))
            return redirect("accounts:user-detail", pk=user.pk)
        return render(request, "accounts/user_form.html", {"form": form, "title": _("Edit %(name)s") % {"name": user.display_name}, "object": user})


# ── Groups ──────────────────────────────────────────────────

GROUP_COLUMNS = [
    {"key": "name", "label": _lazy("Name"), "always": True},
    {"key": "users", "label": _lazy("Users")},
    {"key": "permissions", "label": _lazy("Permissions")},
    {"key": "actions", "label": _lazy("Actions"), "always": True},
]


class GroupListView(LoginRequiredMixin, PermissionRequiredMixin, ListSummaryMixin, PredefinedFilterMixin, AdvancedFilterMixin, SavedFilterMixin, ColumnPreferenceMixin, SortableListMixin, ListView):
    model = Group
    template_name = "accounts/group_list.html"
    context_object_name = "groups"
    paginate_by = 50
    permission_required = "system.groups.read"
    filter_groups = []
    columns = GROUP_COLUMNS
    sortable_fields = {"name": "name"}
    default_sort = "name"
    search_fields = ["name", "description"]

    def get_queryset(self):
        qs = Group.objects.annotate(
            user_count=Count("users"),
            permission_count=Count("permissions"),
        )
        qs = self._apply_sorting(qs)
        qs = self.filter_queryset_predefined(qs)
        return self.filter_queryset_advanced(qs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        base = getattr(self, "_summary_base_qs", None)
        if base is not None:
            ctx["list_kpis"] = [
                {"label": _("Total"), "value": base.count(), "icon": "diagram-3", "tone": "accent"},
                {"label": _("System groups"), "value": base.filter(is_system=True).count(), "icon": "shield-lock", "tone": "warning"},
                {"label": _("Custom groups"), "value": base.filter(is_system=False).count(), "icon": "pencil-square", "tone": "success"},
            ]
        return ctx


class GroupTableBodyView(LoginRequiredMixin, PermissionRequiredMixin, TableBodyPaginatedMixin, PredefinedFilterMixin, AdvancedFilterMixin, SortableListMixin, ListView):
    model = Group
    permission_required = "system.groups.read"
    template_name = "accounts/group_table_body.html"
    context_object_name = "groups"
    paginate_by = 50
    sortable_fields = {"name": "name"}
    default_sort = "name"
    search_fields = ["name", "description"]
    filter_groups = []

    def get_queryset(self):
        qs = Group.objects.annotate(
            user_count=Count("users"),
            permission_count=Count("permissions"),
        )
        qs = self._apply_sorting(qs)
        qs = self.filter_queryset_predefined(qs)
        return self.filter_queryset_advanced(qs)


class GroupDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = Group
    template_name = "accounts/group_detail.html"
    context_object_name = "group"
    permission_required = "system.groups.read"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        group = self.object
        ctx["group_users"] = group.users.all()
        ctx["group_permissions"] = group.permissions.all().order_by("module", "feature", "action")

        # Build permission matrix as a flat list of rows for easy template rendering
        group_codenames = set(group.permissions.values_list("codename", flat=True))
        all_actions = ["create", "read", "update", "delete", "access", "approve", "impersonate"]
        matrix = []
        for module, features in PERMISSION_REGISTRY.items():
            module_label = MODULE_LABELS.get(module, module)
            for feature, info in features.items():
                cells = []
                for action in all_actions:
                    codename = f"{module}.{feature}.{action}"
                    has_action = action in info["actions"]
                    cells.append({
                        "codename": codename,
                        "has_action": has_action,
                        "checked": codename in group_codenames,
                    })
                matrix.append({
                    "module": module,
                    "module_label": module_label,
                    "feature": feature,
                    "feature_label": info["label"],
                    "cells": cells,
                })
        ctx["permission_matrix"] = matrix
        ctx["all_actions"] = all_actions
        ctx["all_users"] = User.objects.filter(is_active=True).exclude(pk__in=group.users.all())
        ctx["all_scopes"] = Scope.objects.exclude(workflow_state="archived")
        ctx["group_scope_ids"] = set(group.allowed_scopes.values_list("id", flat=True))
        return ctx


class GroupCreateView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = "system.groups.create"

    def get(self, request):
        form = GroupForm()
        return render(request, "accounts/group_form.html", {"form": form, "title": _("Create a group")})

    def post(self, request):
        form = GroupForm(request.POST)
        if form.is_valid():
            group = form.save(commit=False)
            group.created_by = request.user
            group.save()
            messages.success(request, _("Group '%(name)s' created.") % {"name": group.name})
            return redirect("accounts:group-detail", pk=group.pk)
        return render(request, "accounts/group_form.html", {"form": form, "title": _("Create a group")})


class GroupUpdateView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = "system.groups.update"

    def get(self, request, pk):
        group = get_object_or_404(Group, pk=pk)
        form = GroupForm(instance=group)
        return render(request, "accounts/group_form.html", {"form": form, "title": _("Edit '%(name)s'") % {"name": group.name}, "object": group})

    def post(self, request, pk):
        group = get_object_or_404(Group, pk=pk)
        form = GroupForm(request.POST, instance=group)
        if form.is_valid():
            form.save()
            messages.success(request, _("Group updated."))
            return redirect("accounts:group-detail", pk=group.pk)
        return render(request, "accounts/group_form.html", {"form": form, "title": _("Edit '%(name)s'") % {"name": group.name}, "object": group})


class GroupPermissionsUpdateView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Handle permission matrix checkbox form submission."""

    permission_required = "system.groups.update"

    def post(self, request, pk):
        group = get_object_or_404(Group, pk=pk)

        # Collect selected permission codenames from POST
        selected = request.POST.getlist("permissions")
        perms = Permission.objects.filter(codename__in=selected)
        group.permissions.set(perms)
        messages.success(request, _("Permissions updated."))
        return redirect("accounts:group-detail", pk=group.pk)


class GroupUsersUpdateView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Add/remove users from a group (single or bulk)."""

    permission_required = "system.groups.update"

    def post(self, request, pk):
        group = get_object_or_404(Group, pk=pk)
        action = request.POST.get("action")

        if action == "add":
            # Support both single user_id and multiple user_ids
            user_ids = request.POST.getlist("user_ids")
            user_id = request.POST.get("user_id")
            if user_id and not user_ids:
                user_ids = [user_id]
            if user_ids:
                users = User.objects.filter(pk__in=user_ids)
                group.users.add(*users)
                count = users.count()
                if count == 1:
                    messages.success(request, _("%(name)s added to the group.") % {"name": users.first().display_name})
                else:
                    messages.success(request, _("%(count)d users added to the group.") % {"count": count})

        elif action == "remove":
            user_id = request.POST.get("user_id")
            if user_id:
                user = get_object_or_404(User, pk=user_id)
                group.users.remove(user)
                messages.success(request, _("%(name)s removed from the group.") % {"name": user.display_name})

        elif action == "bulk_remove":
            user_ids = request.POST.getlist("user_ids")
            if user_ids:
                users = User.objects.filter(pk__in=user_ids)
                count = users.count()
                group.users.remove(*users)
                messages.success(request, _("%(count)d users removed from the group.") % {"count": count})

        return redirect("accounts:group-detail", pk=group.pk)


class GroupScopesUpdateView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Update allowed scopes for a group."""

    permission_required = "system.groups.update"

    def post(self, request, pk):
        group = get_object_or_404(Group, pk=pk)
        selected = request.POST.getlist("scopes")
        scopes = Scope.objects.filter(id__in=selected)
        group.allowed_scopes.set(scopes)
        messages.success(request, _("Allowed scopes updated."))
        return redirect("accounts:group-detail", pk=group.pk)


class GroupDeleteView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = "system.groups.delete"

    def get(self, request, pk):
        group = get_object_or_404(Group, pk=pk)
        user_count = group.users.count()
        return render(request, "accounts/group_confirm_delete.html", {
            "object": group,
            "user_count": user_count,
        })

    def post(self, request, pk):
        group = get_object_or_404(Group, pk=pk)
        if group.users.exists():
            messages.error(request, _("This group still has users. Remove all users before deleting."))
            return redirect("accounts:group-detail", pk=group.pk)
        name = group.name
        group.delete()
        messages.success(request, _("Group '%(name)s' deleted.") % {"name": name})
        return redirect("accounts:group-list")


# ── Impersonation ───────────────────────────────────────────


class ImpersonateStartView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = "system.users.impersonate"

    def post(self, request, pk):
        from accounts.middleware import IMPERSONATION_SESSION_KEY
        from accounts.constants import AccessEventType

        # Prevent nested impersonation
        if request.session.get(IMPERSONATION_SESSION_KEY):
            messages.error(request, _("Impersonation already active."))
            return redirect("accounts:user-detail", pk=pk)

        target = get_object_or_404(User, pk=pk)

        if target == request.user:
            messages.error(request, _("You cannot impersonate yourself."))
            return redirect("accounts:user-detail", pk=pk)

        if not target.is_active or getattr(target, "is_locked", False):
            messages.error(request, _("Cannot impersonate an inactive or locked user."))
            return redirect("accounts:user-detail", pk=pk)

        # Log the impersonation start
        original_user = request.user
        AccessLog.objects.create(
            user=original_user,
            event_type=AccessEventType.IMPERSONATION_START,
            ip_address=request.META.get("REMOTE_ADDR", ""),
            user_agent=request.META.get("HTTP_USER_AGENT", "")[:500],
            metadata={"impersonated_user_id": str(target.pk), "impersonated_email": target.email},
        )

        # Switch to target user (login() flushes the session)
        original_id = str(original_user.pk)
        login(request, target, backend="accounts.backends.EmailAuthBackend")
        # Re-set the key after login flushed the session
        request.session[IMPERSONATION_SESSION_KEY] = original_id

        messages.info(request, _("Now impersonating %(name)s.") % {"name": target.display_name})
        return redirect("/")


class ImpersonateStopView(LoginRequiredMixin, View):

    def post(self, request):
        from accounts.middleware import IMPERSONATION_SESSION_KEY
        from accounts.constants import AccessEventType

        original_id = request.session.get(IMPERSONATION_SESSION_KEY)
        if not original_id:
            return redirect("/")

        try:
            original_user = User.objects.get(pk=original_id)
        except User.DoesNotExist:
            request.session.pop(IMPERSONATION_SESSION_KEY, None)
            return redirect("/")

        # Log the impersonation stop
        AccessLog.objects.create(
            user=original_user,
            event_type=AccessEventType.IMPERSONATION_STOP,
            ip_address=request.META.get("REMOTE_ADDR", ""),
            user_agent=request.META.get("HTTP_USER_AGENT", "")[:500],
            metadata={"impersonated_user_id": str(request.user.pk), "impersonated_email": request.user.email},
        )

        login(request, original_user, backend="accounts.backends.EmailAuthBackend")
        # Session flushed by login, no key to remove
        messages.success(request, _("Impersonation ended."))
        return redirect("/")


# ── Permissions ─────────────────────────────────────────────


def _permission_module_options():
    return [(module, MODULE_LABELS.get(module, module)) for module in PERMISSION_REGISTRY]


def _permission_feature_options():
    seen = {}
    for features in PERMISSION_REGISTRY.values():
        for feature, info in features.items():
            seen.setdefault(feature, info.get("label", feature))
    return list(seen.items())


def _annotate_permission_labels(permissions):
    """Attach human module/feature labels onto each permission in the page."""
    feature_labels = {}
    for features in PERMISSION_REGISTRY.values():
        for feature, info in features.items():
            feature_labels.setdefault(feature, info.get("label", feature))
    for perm in permissions:
        perm.module_label = MODULE_LABELS.get(perm.module, perm.module)
        perm.feature_label = feature_labels.get(perm.feature, perm.feature)


PERMISSION_FILTER_GROUPS = [
    {"param": "module", "field": "module", "label": _lazy("Module"), "options": _permission_module_options()},
    {"param": "feature", "field": "feature", "label": _lazy("Feature"), "options": _permission_feature_options()},
    {"param": "action", "field": "action", "label": _lazy("Action"), "options": PermissionAction.choices},
]
PERMISSION_COLUMNS = [
    {"key": "codename", "label": _lazy("Codename"), "always": True},
    {"key": "module", "label": _lazy("Module")},
    {"key": "feature", "label": _lazy("Feature")},
    {"key": "action", "label": _lazy("Action")},
]
PERMISSION_SORTABLE_FIELDS = {
    "codename": "codename",
    "module": "module",
    "feature": "feature",
    "action": "action",
}


class PermissionListView(LoginRequiredMixin, PermissionRequiredMixin, ListSummaryMixin, PredefinedFilterMixin, AdvancedFilterMixin, SavedFilterMixin, ColumnPreferenceMixin, SortableListMixin, ListView):
    model = Permission
    template_name = "accounts/permission_list.html"
    context_object_name = "permissions"
    paginate_by = 100
    permission_required = "system.groups.read"
    filter_groups = PERMISSION_FILTER_GROUPS
    columns = PERMISSION_COLUMNS
    sortable_fields = PERMISSION_SORTABLE_FIELDS
    default_sort = "codename"
    search_fields = ["codename", "name"]

    def get_queryset(self):
        qs = self._apply_sorting(Permission.objects.all())
        qs = self.filter_queryset_predefined(qs)
        return self.filter_queryset_advanced(qs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        _annotate_permission_labels(ctx["permissions"])
        base = getattr(self, "_summary_base_qs", None)
        if base is not None:
            ctx["list_kpis"] = [
                {"label": _("Total"), "value": base.count(), "icon": "key", "tone": "accent"},
                {"label": _("System"), "value": base.filter(is_system=True).count(), "icon": "shield-lock", "tone": "warning"},
                {"label": _("Modules"), "value": base.values("module").distinct().count(), "icon": "grid", "tone": "success"},
            ]
        return ctx


class PermissionTableBodyView(LoginRequiredMixin, PermissionRequiredMixin, TableBodyPaginatedMixin, PredefinedFilterMixin, AdvancedFilterMixin, SortableListMixin, ListView):
    model = Permission
    permission_required = "system.groups.read"
    template_name = "accounts/permission_table_body.html"
    context_object_name = "permissions"
    paginate_by = 100
    sortable_fields = PERMISSION_SORTABLE_FIELDS
    default_sort = "codename"
    search_fields = ["codename", "name"]
    filter_groups = PERMISSION_FILTER_GROUPS

    def get_queryset(self):
        qs = self._apply_sorting(Permission.objects.all())
        qs = self.filter_queryset_predefined(qs)
        return self.filter_queryset_advanced(qs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        _annotate_permission_labels(ctx["permissions"])
        return ctx


# ── Access Logs ─────────────────────────────────────────────

ACCESS_LOG_FILTER_GROUPS = [
    {"param": "event_type", "field": "event_type", "label": _lazy("Event"), "options": AccessEventType.choices},
]
ACCESS_LOG_COLUMNS = [
    {"key": "date", "label": _lazy("Date"), "always": True},
    {"key": "email", "label": _lazy("Email")},
    {"key": "event", "label": _lazy("Event")},
    {"key": "ip", "label": _lazy("IP")},
]
ACCESS_LOG_SORTABLE_FIELDS = {
    "date": "timestamp",
    "email": "email_attempted",
    "event": "event_type",
}


_ACCESS_LOG_SUCCESS_EVENTS = (
    AccessEventType.LOGIN_SUCCESS,
    AccessEventType.PASSKEY_LOGIN_SUCCESS,
)
_ACCESS_LOG_FAILURE_EVENTS = (
    AccessEventType.LOGIN_FAILED,
    AccessEventType.PASSKEY_LOGIN_FAILED,
)


def _access_log_kpis(base):
    """Coloured KPI tiles for the access-log rail, computed from the base
    queryset (before facets)."""
    if base is None:
        return []
    from django.utils import timezone as tz

    since = tz.now() - tz.timedelta(hours=24)
    return [
        {"label": _("Total"), "value": base.count(), "icon": "clock-history", "tone": "accent"},
        {"label": _("Successful logins"), "value": base.filter(event_type__in=_ACCESS_LOG_SUCCESS_EVENTS).count(), "icon": "check-circle", "tone": "success"},
        {"label": _("Failed logins"), "value": base.filter(event_type__in=_ACCESS_LOG_FAILURE_EVENTS).count(), "icon": "x-circle", "tone": "danger"},
        {"label": _("Last 24h"), "value": base.filter(timestamp__gte=since).count(), "icon": "hourglass", "tone": "warning"},
    ]


class AccessLogListView(LoginRequiredMixin, PermissionRequiredMixin, ListSummaryMixin, PredefinedFilterMixin, AdvancedFilterMixin, SavedFilterMixin, ColumnPreferenceMixin, SortableListMixin, ListView):
    model = AccessLog
    template_name = "accounts/access_log_list.html"
    context_object_name = "logs"
    paginate_by = 50
    permission_required = "system.audit_trail.read"
    filter_groups = ACCESS_LOG_FILTER_GROUPS
    columns = ACCESS_LOG_COLUMNS
    sortable_fields = ACCESS_LOG_SORTABLE_FIELDS
    default_sort = "date"
    default_sort_order = "desc"
    search_fields = ["email_attempted"]

    def get_queryset(self):
        qs = AccessLog.objects.select_related("user")
        qs = self.filter_queryset_predefined(qs)
        return self.filter_queryset_advanced(qs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["list_kpis"] = _access_log_kpis(getattr(self, "_summary_base_qs", None))
        return ctx


class AccessLogTableBodyView(LoginRequiredMixin, PermissionRequiredMixin, TableBodyPaginatedMixin, PredefinedFilterMixin, AdvancedFilterMixin, SortableListMixin, ListView):
    model = AccessLog
    permission_required = "system.audit_trail.read"
    template_name = "accounts/access_log_table_body.html"
    context_object_name = "logs"
    paginate_by = 50
    sortable_fields = ACCESS_LOG_SORTABLE_FIELDS
    default_sort = "date"
    default_sort_order = "desc"
    search_fields = ["email_attempted"]
    filter_groups = ACCESS_LOG_FILTER_GROUPS

    def get_queryset(self):
        qs = AccessLog.objects.select_related("user")
        qs = self.filter_queryset_predefined(qs)
        return self.filter_queryset_advanced(qs)


# ── Calendar subscriptions ──────────────────────────────────


CALENDAR_SUBSCRIPTION_COLUMNS = [
    {"key": "user", "label": _lazy("User"), "always": True},
    {"key": "name", "label": _lazy("Name"), "always": True},
    {"key": "created", "label": _lazy("Created")},
    {"key": "client", "label": _lazy("Client")},
    {"key": "actions", "label": _lazy("Actions"), "always": True},
]
CALENDAR_SUBSCRIPTION_SORTABLE_FIELDS = {
    "user": "user__last_name",
    "name": "name",
    "created": "created_at",
    "last_used": "last_used_at",
}


class CalendarSubscriptionListView(LoginRequiredMixin, PermissionRequiredMixin, ListSummaryMixin, PredefinedFilterMixin, AdvancedFilterMixin, SavedFilterMixin, ColumnPreferenceMixin, SortableListMixin, ListView):
    template_name = "accounts/calendar_subscription_list.html"
    context_object_name = "tokens"
    paginate_by = 50
    permission_required = "system.users.read"
    filter_groups = []
    columns = CALENDAR_SUBSCRIPTION_COLUMNS
    sortable_fields = CALENDAR_SUBSCRIPTION_SORTABLE_FIELDS
    default_sort = "created"
    default_sort_order = "desc"
    search_fields = ["name", "user__first_name", "user__last_name", "user__email"]

    @property
    def model(self):
        from accounts.models import CalendarToken
        return CalendarToken

    def get_queryset(self):
        from accounts.models import CalendarToken
        qs = self._apply_sorting(CalendarToken.objects.select_related("user"))
        qs = self.filter_queryset_predefined(qs)
        return self.filter_queryset_advanced(qs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        base = getattr(self, "_summary_base_qs", None)
        if base is not None:
            ctx["list_kpis"] = [
                {"label": _("Total"), "value": base.count(), "icon": "calendar-event", "tone": "accent"},
            ]
        return ctx


class CalendarSubscriptionTableBodyView(LoginRequiredMixin, PermissionRequiredMixin, TableBodyPaginatedMixin, PredefinedFilterMixin, AdvancedFilterMixin, SortableListMixin, ListView):
    template_name = "accounts/calendar_subscription_table_body.html"
    context_object_name = "tokens"
    paginate_by = 50
    permission_required = "system.users.read"
    filter_groups = []
    sortable_fields = CALENDAR_SUBSCRIPTION_SORTABLE_FIELDS
    default_sort = "created"
    default_sort_order = "desc"
    search_fields = ["name", "user__first_name", "user__last_name", "user__email"]

    @property
    def model(self):
        from accounts.models import CalendarToken
        return CalendarToken

    def get_queryset(self):
        from accounts.models import CalendarToken
        qs = self._apply_sorting(CalendarToken.objects.select_related("user"))
        qs = self.filter_queryset_predefined(qs)
        return self.filter_queryset_advanced(qs)


class CalendarSubscriptionRevokeView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = "system.users.update"

    def post(self, request, pk):
        from accounts.models import CalendarToken
        token = get_object_or_404(CalendarToken, pk=pk)
        name = token.name
        user_name = token.user.display_name
        token.delete()
        messages.success(request, _("Calendar subscription \"%(name)s\" revoked for %(user)s.") % {"name": name, "user": user_name})
        return redirect("accounts:calendar-subscription-list")


# ── Action Log (history) ────────────────────────────────────

HISTORY_TYPE_LABELS = {"+": _lazy("Creation"), "~": _lazy("Modification"), "-": _lazy("Deletion")}

MODEL_LABELS = {}


def _get_model_labels():
    """Build a mapping of historical model → human label, cached."""
    if MODEL_LABELS:
        return MODEL_LABELS
    for model in apps.get_models():
        if model.__name__.startswith("Historical"):
            original = getattr(model, "instance_type", None)
            if original:
                label = original._meta.verbose_name.capitalize()
                app = original._meta.app_label
                MODEL_LABELS[model] = (app, label)
    return MODEL_LABELS


class ActionLogListView(LoginRequiredMixin, PermissionRequiredMixin, ListSummaryMixin, ListView):
    template_name = "accounts/action_log_list.html"
    context_object_name = "entries"
    paginate_by = 50
    permission_required = "system.audit_trail.read"

    def _get_historical_models(self):
        # Only true per-record history models (they carry history_user). Exclude
        # the auto-generated M2M through-history models (e.g. from
        # HistoricalRecords(m2m_fields=[...])), which track relation rows, have no
        # history_user, and whose change is already represented by the parent's
        # history entry.
        return [
            m
            for m in apps.get_models()
            if m.__name__.startswith("Historical")
            and any(f.name == "history_user" for f in m._meta.fields)
        ]

    def get_queryset(self):
        labels = _get_model_labels()

        querysets = []
        for hist_model in self._get_historical_models():
            app, model_label = labels.get(hist_model, (None, None))
            if not app:
                continue
            querysets.append(hist_model.objects.select_related("history_user").all())

        if not querysets:
            return []

        merged = sorted(
            chain(*querysets),
            key=attrgetter("history_date"),
            reverse=True,
        )
        return merged

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        labels = _get_model_labels()

        annotated = []
        for entry in ctx["entries"]:
            app, model_label = labels.get(type(entry), ("", ""))
            entry.app_label = MODULE_LABELS.get(app, app)
            entry.model_label = model_label
            try:
                entry.object_repr = str(entry)
            except Exception:
                entry.object_repr = "-"

            # Classify via the shared core.history classifier.
            kind = classify_record(entry)
            if kind == EntryKind.TRANSITION:
                entry.action_label = _("Transition")
                entry.action_badge = "info"
            elif kind == EntryKind.CREATE:
                entry.action_label = HISTORY_TYPE_LABELS["+"]
                entry.action_badge = "success"
            elif kind == EntryKind.DELETE:
                entry.action_label = HISTORY_TYPE_LABELS["-"]
                entry.action_badge = "danger"
            else:
                entry.action_label = HISTORY_TYPE_LABELS["~"]
                entry.action_badge = "warning"

            annotated.append(entry)

        ctx["entries"] = annotated
        # Aggregated history has no single model, so the offcanvas advanced
        # builder and the predefined facets cannot apply. Expose only a coloured
        # KPI tile for the rail, computed from the full merged list length.
        paginator = ctx.get("paginator")
        total = paginator.count if paginator is not None else len(annotated)
        ctx["list_kpis"] = [
            {"label": _("Total entries"), "value": total, "icon": "journal-text", "tone": "accent"},
        ]
        return ctx
