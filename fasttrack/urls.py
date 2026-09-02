"""Routes API Fast-Track."""

from django.urls import path

from .views import (
    CreditSimulationView,
    CurrencyRateView,
    ClientAgencyLocationView,
    ClientSearchView,
    CinImageSearchView,
    ClientDossierPDFView,
    FastTrackDiagnosticView,
    JobStatusView,
    ScanCINView,
    WhatsAppMessageView,
    WorkflowCommentCreateView,
    WorkflowAgentsView,
    WorkflowAssignmentView,
    WorkflowDetailView,
    WorkflowLikeView,
    WorkflowReplyView,
    WorkflowStatusView,
    ResponsableDossierListView,
    ResponsableDecisionView,
    ResponsableDossierCSVExportView,
    ClientTimelineView,
)

urlpatterns = [
    path("agent/search-client/", ClientSearchView.as_view(), name="search-client"),
    path("agent/scan-search/", CinImageSearchView.as_view(), name="cin-image-search"),
    path("agent/client/<str:cin>/dossier-pdf/", ClientDossierPDFView.as_view(), name="client-dossier-pdf"),
    path("credit/simulate/", CreditSimulationView.as_view(), name="credit-simulate"),
    path("currency/rate/", CurrencyRateView.as_view(), name="currency-rate"),
    path("client/<str:cin>/agency-location/", ClientAgencyLocationView.as_view(), name="client-agency-location"),
    path("responsable/dossiers/", ResponsableDossierListView.as_view(), name="responsable-dossiers"),
    path("responsable/dossiers/<int:dossier_id>/decision/", ResponsableDecisionView.as_view(), name="responsable-decision"),
    path("responsable/dossiers/export-csv/", ResponsableDossierCSVExportView.as_view(), name="responsable-dossiers-csv"),
    path("client/<str:cin>/timeline/", ClientTimelineView.as_view(), name="client-timeline"),
    path("workflow/agents/", WorkflowAgentsView.as_view(), name="workflow-agents"),
    path("workflow/<str:cin>/", WorkflowDetailView.as_view(), name="workflow-detail"),
    path("workflow/<str:cin>/status/", WorkflowStatusView.as_view(), name="workflow-status"),
    path("workflow/<str:cin>/assign/", WorkflowAssignmentView.as_view(), name="workflow-assignment"),
    path("workflow/<str:cin>/comments/", WorkflowCommentCreateView.as_view(), name="workflow-comments"),
    path("workflow/comments/<int:comment_id>/reply/", WorkflowReplyView.as_view(), name="workflow-reply"),
    path("workflow/comments/<int:comment_id>/like/", WorkflowLikeView.as_view(), name="workflow-like"),
    path("agent/scan-cin/", ScanCINView.as_view(), name="scan-cin"),
    path("jobs/<str:job_id>/status/", JobStatusView.as_view(), name="job-status"),
    path(
        "agent/client/<str:cin>/fast-track-diagnostic/",
        FastTrackDiagnosticView.as_view(),
        name="fast-track-diagnostic",
    ),
    path(
        "agent/client/<str:cin>/payment-reminder/",
        WhatsAppMessageView.as_view(),
        name="payment-reminder",
    ),
    path(
        "agent/client/<str:cin>/whatsapp-message/",
        WhatsAppMessageView.as_view(),
        name="whatsapp-message",
    ),
]
