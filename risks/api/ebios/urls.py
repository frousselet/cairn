from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views


router = DefaultRouter()
router.register(r"study-frameworks", views.StudyFrameworkViewSet)
router.register(r"workshops", views.EbiosWorkshopProgressViewSet)
router.register(r"baselines", views.SecurityBaselineViewSet)
router.register(r"feared-events", views.FearedEventViewSet)
router.register(r"baseline-gaps", views.BaselineGapViewSet)


urlpatterns = [
    path("", include(router.urls)),
]
