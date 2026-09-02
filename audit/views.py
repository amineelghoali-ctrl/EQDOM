from io import BytesIO

from django.http import HttpResponse
from django.utils import timezone
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from .models import AuditLog


class AuditExportPDFView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, cin, *args, **kwargs):
        logs = AuditLog.objects.filter(client_cin__iexact=cin).select_related("user")
        stream = BytesIO()
        pdf = canvas.Canvas(stream, pagesize=A4)
        width, height = A4
        pdf.setTitle(f"Attestation CNDP - {cin}")
        pdf.setFont("Helvetica-Bold", 16)
        pdf.drawString(48, height - 60, "EQDOM — Système des Agences — Attestation d'accès CNDP")
        pdf.setFont("Helvetica", 10)
        pdf.drawString(48, height - 84, f"Dossier CIN : {cin.upper()}")
        pdf.drawString(48, height - 100, f"Éditée le : {timezone.localtime():%d/%m/%Y %H:%M}")
        y = height - 136
        pdf.setFont("Helvetica-Bold", 9)
        pdf.drawString(48, y, "Horodatage")
        pdf.drawString(170, y, "Utilisateur")
        pdf.drawString(330, y, "Action")
        y -= 18
        pdf.setFont("Helvetica", 9)
        for log in logs:
            if y < 55:
                pdf.showPage(); y = height - 55; pdf.setFont("Helvetica", 9)
            pdf.drawString(48, y, timezone.localtime(log.timestamp).strftime("%d/%m/%Y %H:%M:%S"))
            pdf.drawString(170, y, log.user.get_username()[:25])
            pdf.drawString(330, y, log.get_action_display())
            y -= 16
        if not logs.exists():
            pdf.drawString(48, y, "Aucun accès CNDP enregistré pour ce dossier.")
        pdf.setFont("Helvetica-Oblique", 8)
        pdf.drawString(48, 34, "Document généré à des fins de traçabilité et de contrôle CNDP.")
        pdf.save()
        response = HttpResponse(stream.getvalue(), content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="attestation-cndp-{cin.upper()}.pdf"'
        return response
