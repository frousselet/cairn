# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""REST API of the organization skills : ``/api/v1/mcp/skills/``.

The same records the web register and the MCP tools write, under the same
``system.mcp_skill.*`` permissions and the same default lifecycle. A skill is
instance-wide (``scope_filtered = False`` : a procedure of the organization
belongs to no scope), and is only served over MCP once validated.
"""

from rest_framework import serializers, viewsets
from rest_framework.permissions import IsAuthenticated

from accounts.api.mixins import HistoryAPIMixin, LifecycleAPIMixin, ScopeFilterAPIMixin
from accounts.api.permissions import ModulePermission
from core.completeness_api import CompletenessSerializerMixin
from mcp.models import McpSkill


class McpSkillSerializer(CompletenessSerializerMixin, serializers.ModelSerializer):
    status = serializers.CharField(source="workflow_state", read_only=True)
    uri = serializers.CharField(read_only=True)
    replaces_shipped_skill = serializers.BooleanField(read_only=True)
    skill_md = serializers.SerializerMethodField()

    class Meta:
        model = McpSkill
        fields = [
            "id", "reference", "name", "description", "body", "uri", "replaces_shipped_skill",
            "skill_md", "status", "version", "created_by", "created_at", "updated_at", "completeness",
        ]
        read_only_fields = ["id", "reference", "version", "created_by", "created_at", "updated_at"]

    def get_skill_md(self, obj):
        return obj.skill_md()


class McpSkillListSerializer(serializers.ModelSerializer):
    status = serializers.CharField(source="workflow_state", read_only=True)
    replaces_shipped_skill = serializers.BooleanField(read_only=True)

    class Meta:
        model = McpSkill
        fields = ["id", "reference", "name", "description", "replaces_shipped_skill", "status", "updated_at"]


class McpSkillViewSet(ScopeFilterAPIMixin, LifecycleAPIMixin, HistoryAPIMixin, viewsets.ModelViewSet):
    queryset = McpSkill.objects.all()
    permission_classes = [IsAuthenticated, ModulePermission]
    permission_module = "system"
    permission_feature = "mcp_skill"
    custom_action_map = {"transition": "update"}
    scope_filtered = False
    search_fields = ["reference", "name", "description"]
    ordering_fields = ["reference", "name", "workflow_state", "updated_at"]
    filterset_fields = ["workflow_state"]

    def perform_create(self, serializer):
        # The author is the person acting, never a field of the payload.
        serializer.save(created_by=self.request.user)

    def get_serializer_class(self):
        if self.action == "list":
            return McpSkillListSerializer
        return McpSkillSerializer
