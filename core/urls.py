"""URL configuration for Cairn project."""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from mcp.views import OAuthAuthorizeView, oauth_authorization_server_metadata

from .views import (
    CalendarEventsView, CalendarSubscribeView, CalendarUpcomingView,
    CalendarView, ChangelogDismissView, DashboardAskCairnBriefingView,
    DashboardIndicatorsPartialView,
    DashboardIndicatorWidgetPartialView,
    DashboardLayoutSaveView, GeneralDashboardView, GlobalSearchView,
    ICalFeedView, KanbanBoardDataView, KanbanBoardView,
    SectionCollapseToggleView, StyleGuideView,
)

urlpatterns = [
    # OAuth 2.0 Authorization Server Metadata (RFC 8414) - must be at root
    path(".well-known/oauth-authorization-server", oauth_authorization_server_metadata, name="oauth-as-metadata"),

    # OAuth 2.0 Authorization Endpoint - must be at root
    path("authorize", OAuthAuthorizeView.as_view(), name="oauth-authorize"),

    path("i18n/", include("django.conf.urls.i18n")),
    path("onboarding/", include("core.onboarding.urls")),
    path("", GeneralDashboardView.as_view(), name="home"),
    path("dashboard/indicators-partial/", DashboardIndicatorsPartialView.as_view(), name="dashboard-indicators-partial"),
    path("dashboard/indicator-widget/", DashboardIndicatorWidgetPartialView.as_view(), name="dashboard-indicator-widget"),
    path("dashboard/ask-cairn-briefing/", DashboardAskCairnBriefingView.as_view(), name="dashboard-ask-cairn-briefing"),
    path("dashboard/changelog-dismiss/", ChangelogDismissView.as_view(), name="changelog-dismiss"),
    path("dashboard/section-toggle/", SectionCollapseToggleView.as_view(), name="dashboard-section-toggle"),
    path("dashboard/layout/", DashboardLayoutSaveView.as_view(), name="dashboard-layout-save"),
    path("calendar/", CalendarView.as_view(), name="calendar"),
    path("kanban/", KanbanBoardView.as_view(), name="kanban"),
    path("api/kanban-board/", KanbanBoardDataView.as_view(), name="kanban-board"),
    path("calendar/subscribe/", CalendarSubscribeView.as_view(), name="calendar-subscribe"),
    path("calendar.ics", ICalFeedView.as_view(), name="calendar-ical"),
    path("api/calendar-events/", CalendarEventsView.as_view(), name="calendar-events"),
    path("api/calendar-upcoming/", CalendarUpcomingView.as_view(), name="calendar-upcoming"),
    path("api/search/", GlobalSearchView.as_view(), name="global-search"),
    path("api/assistant/", include("assistant.urls")),
    path("styleguide/", StyleGuideView.as_view(), name="styleguide"),
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("helpers/", include("helpers.urls")),
    path("context/", include("context.urls")),
    path("assets/", include("assets.urls")),
    path("compliance/", include("compliance.urls")),
    path("risks/", include("risks.urls")),
    path("reports/", include("reports.urls")),
    path("trust/", include("trust_center.urls")),
    path("trust-center/manage/", include("trust_center.admin_urls")),
    path("api/v1/", include("accounts.api.urls")),
    path("api/v1/context/", include("context.api.urls")),
    path("api/v1/assets/", include("assets.api.urls")),
    path("api/v1/compliance/", include("compliance.api.urls")),
    path("api/v1/risks/", include("risks.api.urls")),
    path("api/v1/reports/", include("reports.api.urls")),
    path("api/v1/trust-center/", include("trust_center.api.urls")),
    path("api/v1/assistant/", include("assistant.api.urls")),
    path("api/v1/", include("mcp.urls")),
    path("workflow/", include("core.workflow_urls")),
    path("history/", include("core.history_urls")),
    path("imports/", include("core.imports.urls")),
]

if settings.DEBUG:
    # In DEBUG, serve static files through Django so uvicorn / daphne /
    # gunicorn (which, unlike runserver, do not auto-serve them) can hand
    # out static/js/* etc. The runserver convenience injection only runs
    # under `manage.py runserver`; the entries below take care of every
    # other dev server. STATICFILES_DIRS and collected files at STATIC_ROOT
    # both end up reachable via STATIC_URL.
    from django.contrib.staticfiles.urls import staticfiles_urlpatterns

    urlpatterns += staticfiles_urlpatterns()
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
