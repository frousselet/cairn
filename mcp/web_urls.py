# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""Web pages of the agent skills, mounted at ``/mcp/skills/``."""

from django.urls import path

from mcp import web_views as views

app_name = "mcp_skills"

urlpatterns = [
    path("", views.McpSkillListView.as_view(), name="skill-list"),
    path("table-body/", views.McpSkillTableBodyView.as_view(), name="skill-table-body"),
    path("create/", views.McpSkillCreateView.as_view(), name="skill-create"),
    path("<uuid:pk>/", views.McpSkillDetailView.as_view(), name="skill-detail"),
    path("<uuid:pk>/edit/", views.McpSkillUpdateView.as_view(), name="skill-update"),
    path("<uuid:pk>/delete/", views.McpSkillDeleteView.as_view(), name="skill-delete"),
]
