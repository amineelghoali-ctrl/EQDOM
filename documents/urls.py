from django.urls import path

from .views import (
    ClientContractSignatureView,
    ClientDocumentChecklistView,
    ClientDocumentStatusView,
)

urlpatterns = [
    path("client/<str:cin>/documents/", ClientDocumentChecklistView.as_view(), name="client-documents"),
    path("documents/<int:document_id>/status/", ClientDocumentStatusView.as_view(), name="document-status"),
    path("client/<str:cin>/contract/signature/", ClientContractSignatureView.as_view(), name="client-contract-signature"),
]
