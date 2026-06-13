from django.urls import path

from . import views

app_name = "assistant"

urlpatterns = [
    path("ask/", views.AskAssistantView.as_view(), name="ask"),
    path("feedback/", views.AssistantFeedbackView.as_view(), name="feedback"),
]
