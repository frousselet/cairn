from django.urls import path

from helpers import views

app_name = "helpers"

urlpatterns = [
    path("dismiss/", views.DismissHelperView.as_view(), name="dismiss"),
    path("save-sort/", views.SaveSortPreferenceView.as_view(), name="save-sort"),
    path("save-columns/", views.SaveColumnPreferenceView.as_view(), name="save-columns"),
]
