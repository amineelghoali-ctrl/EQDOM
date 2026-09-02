from django.urls import path

from .views import AuditExportPDFView

urlpatterns = [path("audit/export-pdf/<str:cin>/", AuditExportPDFView.as_view(), name="audit-export-pdf")]
