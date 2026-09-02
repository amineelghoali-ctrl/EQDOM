from django.urls import path

from .views import AgencyAnalyticsView, AgentKPIView

urlpatterns = [
    path("agent/kpis/", AgentKPIView.as_view(), name="agent-kpis"),
    path("analytics/agency/", AgencyAnalyticsView.as_view(), name="agency-analytics"),
]
