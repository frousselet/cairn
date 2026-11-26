# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
from django.urls import include, path
from rest_framework.routers import SimpleRouter

from mcp.api.views_mcp import McpEndpointView, mcp_metadata_view
from mcp.api.views_skills import McpSkillViewSet
from mcp.api.views_uploads import McpUploadView
from mcp.api.views_oauth import (
    OAuthApplicationDetailView,
    OAuthApplicationListCreateView,
    OAuthRegisterView,
    OAuthTokenView,
)

app_name = "mcp"

router = SimpleRouter()
router.register(r"mcp/skills", McpSkillViewSet, basename="mcp-skill")

urlpatterns = [
    # OAuth 2.0 endpoints
    path("oauth/token/", OAuthTokenView.as_view(), name="oauth-token"),
    path("oauth/register/", OAuthRegisterView.as_view(), name="oauth-register"),
    path("oauth/applications/", OAuthApplicationListCreateView.as_view(), name="oauth-applications"),
    path("oauth/applications/<uuid:pk>/", OAuthApplicationDetailView.as_view(), name="oauth-application-detail"),

    # MCP Streamable HTTP endpoint
    path("mcp", McpEndpointView.as_view(), name="mcp-endpoint"),
    # Where a client sends a file a tool call asked for (io.modelcontextprotocol/files)
    path("mcp/uploads/<uuid:pk>", McpUploadView.as_view(), name="mcp-upload"),

    # OAuth Protected Resource Metadata
    path("mcp/.well-known/oauth-protected-resource", mcp_metadata_view, name="mcp-metadata"),

    # Organization skills (REST)
    path("", include(router.urls)),
]
