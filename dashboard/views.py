from django.utils import timezone
from django.db.models import Count, Sum
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from audit.models import AuditLog
from fasttrack.models import AuditLog as TechnicalAuditLog
from fasttrack.models import CoreBankingDetails, DossierWorkflow


class AgentKPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        today = timezone.localdate()
        events = AuditLog.objects.filter(user=request.user, timestamp__date=today)
        scans = events.filter(action=AuditLog.Action.SCAN_CIN).count()
        agreements = events.filter(action=AuditLog.Action.SIMULATION_CREATED).count()
        scan_times = TechnicalAuditLog.objects.filter(
            agent=request.user, timestamp__date=today, action="CIN_SCAN", status=TechnicalAuditLog.Status.SUCCESS
        )
        average_ms = sum(scan_times.values_list("response_time_ms", flat=True)) / scan_times.count() if scan_times.exists() else None
        return Response({
            "date": today.isoformat(),
            "dossiers_scannes": scans,
            "accords_principe_generes": agreements,
            "temps_moyen_traitement_secondes": round(average_ms / 1000, 2) if average_ms is not None else 0,
        })


class AgencyAnalyticsView(APIView):
    """Indicateurs agrégés pour Chart.js, réservés au pilotage interne."""

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        if not request.user.is_staff:
            return Response({"detail": "Accès statistiques réservé."}, status=403)
        status_counts = {
            item["current_status"]: item["total"]
            for item in DossierWorkflow.objects.values("current_status").annotate(total=Count("id"))
        }
        by_agent = list(
            DossierWorkflow.objects.values("assigned_agent__username")
            .annotate(total=Count("id"))
            .order_by("assigned_agent__username")
        )
        credit = CoreBankingDetails.objects.aggregate(
            requested=Sum("montant_credit"), financed=Sum("montant_finance")
        )
        return Response({
            "statuses": status_counts,
            "by_agent": [{"label": row["assigned_agent__username"] or "Non assigné", "total": row["total"]} for row in by_agent],
            "credit_totals": {"requested": credit["requested"] or 0, "financed": credit["financed"] or 0},
        })
