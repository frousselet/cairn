"""URL patterns for the first-run onboarding flow."""

from django.urls import path

from . import views

app_name = "onboarding"

urlpatterns = [
    path("", views.OnboardingView.as_view(), name="landing"),
    path("progress.json", views.OnboardingProgressView.as_view(), name="progress"),
    path("scratch/", views.OnboardingScratchView.as_view(), name="scratch"),
    path("seed/", views.OnboardingSeedView.as_view(), name="seed"),
    path("complete/", views.OnboardingCompleteView.as_view(), name="complete"),
]
