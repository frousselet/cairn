from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r"reports", views.ReportViewSet)
router.register(r"management-reviews", views.ManagementReviewViewSet)
router.register(r"decisions", views.ManagementReviewDecisionViewSet)
router.register(r"isms-changes", views.IsmsChangeViewSet)

app_name = "reports-api"

urlpatterns = [
    path("", include(router.urls)),
]
