from django.urls import path

from . import views

urlpatterns = [
    path("ask/", views.AskAssistantApiView.as_view(), name="assistant-api-ask"),
]
