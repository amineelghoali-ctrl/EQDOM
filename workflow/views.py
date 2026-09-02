from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from fasttrack.models import DossierWorkflow

from .models import OverrideRequest


class OverrideRequestCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, cin, *args, **kwargs):
        reason = str(request.data.get("reason", "")).strip()
        if not reason:
            return Response({"reason": ["Le motif de dérogation est obligatoire."]}, status=status.HTTP_400_BAD_REQUEST)
        workflow = get_object_or_404(DossierWorkflow, client__cin_number__iexact=cin)
        override = OverrideRequest.objects.create(workflow=workflow, requested_by=request.user, reason=reason)
        return Response({"id": override.pk, "is_approved": False, "message": "Demande transmise au chef d'agence."}, status=status.HTTP_201_CREATED)
