from django.urls import path

from . import views

app_name = "assistant"

urlpatterns = [
    path("ask/", views.AskAssistantView.as_view(), name="ask"),
    path("feedback/", views.AssistantFeedbackView.as_view(), name="feedback"),
    path("feedback/list/", views.AssistantFeedbackListView.as_view(), name="feedback-list"),
    path("feedback/export/", views.AssistantFeedbackExportView.as_view(), name="feedback-export"),
]
