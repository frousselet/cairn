"""URLs for the generic history panel endpoint."""

from django.urls import path

from core.history_views import HistoryPartialView

app_name = "history"

urlpatterns = [
    path(
        "<str:app_label>/<str:model>/<uuid:pk>/",
        HistoryPartialView.as_view(),
        name="partial",
    ),
]
