from django.urls import path

from . import views

app_name = "imports"

urlpatterns = [
    path("<str:entity>/preview/", views.EntityImportPreviewView.as_view(), name="import-preview"),
    path("<str:entity>/sample/", views.EntityImportSampleView.as_view(), name="import-sample"),
    path("<str:entity>/", views.EntityImportView.as_view(), name="import"),
]
