from rest_framework.routers import DefaultRouter

from django.urls import path

from . import views

router = DefaultRouter()
router.register("certifications", views.CertificationViewSet)
router.register("subprocessors", views.SubprocessorViewSet)
router.register("measures", views.MeasureViewSet)
router.register("documents", views.DocumentViewSet)

app_name = "trust_center_api"

urlpatterns = [
    path("settings/", views.TrustCenterSettingsView.as_view(), name="settings"),
    *router.urls,
]
