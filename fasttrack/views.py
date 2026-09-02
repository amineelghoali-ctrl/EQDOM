"""Vues REST de l'espace agent Fast-Track."""

from typing import Any
from time import perf_counter
from io import BytesIO
import csv
from urllib.parse import urlencode
from decimal import Decimal

from celery.result import AsyncResult
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.storage import default_storage
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import AuditLog, ClientProfile, CoreBankingDetails, DossierWorkflow, WorkflowComment
from .serializers import (
    ClientProfileSerializer,
    CoreBankingDetailsSerializer,
    CreditSimulationSerializer,
    DossierWorkflowSerializer,
    ScanCINSerializer,
    WorkflowCommentCreateSerializer,
    WorkflowCommentSerializer,
    WorkflowAssignmentSerializer,
    ResponsableDecisionSerializer,
    ResponsableDossierSerializer,
    WorkflowStatusSerializer,
)
from .permissions import IsResponsable, is_responsable
from .services.credit_simulator import EQDOMCreditSimulator
from .services.currency_service import get_mad_rate
from .services.geocoding_service import (
    get_client_coordinates,
    get_reference_client_city,
    get_nearest_agency,
)
from .services.cin_ocr import (
    CinNotDetectedError,
    OcrConfigurationError,
    extract_moroccan_cin_identity,
)
from .services.whatsapp_reminder import build_whatsapp_client_message
from .tasks import process_cin_scan_task


def _traffic_light(client: ClientProfile) -> dict[str, str]:
    """Détermine l'état visuel de risque du dossier."""
    details = client.core_banking_details
    if not client.liveness_verified or client.face_match_score < 0.85:
        return {"color": "red", "label": "Vérification biométrique requise"}
    if details.nbr_impayes >= 3 or details.age_impayes_jours > 90:
        return {"color": "red", "label": "Risque élevé : impayés importants"}
    if details.nbr_impayes > 0:
        return {"color": "orange", "label": "Attention : régularisation nécessaire"}
    return {"color": "green", "label": "Dossier à jour"}


def _new_client_url(identity: dict[str, Any]) -> str:
    """Construit l'URL de saisie, préremplie seulement par l'OCR."""
    cin = identity.get("cin") or identity.get("cin_number")
    return "/dossiers/nouveau/?" + urlencode(
        {
            "cin": cin,
            "nom": identity["nom"],
            "prenom": identity["prenom"],
        }
    )


def _ensure_initial_core_banking(client: ClientProfile) -> CoreBankingDetails:
    """Garantit qu'un dossier enregistré est consultable sur la vue 360°.

    Les valeurs à zéro indiquent une étude en cours ; elles ne simulent ni
    crédit accordé, ni impayé. Elles seront remplacées par les vraies données
    saisies/validées par l'agent.
    """
    details, _ = CoreBankingDetails.objects.get_or_create(
        client=client,
        defaults={
            "produit": "Dossier en constitution",
            "mode_prelevement": "À renseigner",
            "etat": "EN_CONSTITUTION",
            "numero_dossier": f"DOS-{client.cin_number}",
            "montant_credit": Decimal("0.00"),
            "montant_finance": Decimal("0.00"),
            "mensualite": Decimal("0.00"),
            "nb_mensualites_total": 0,
            "nb_mensualites_restantes": 0,
            "mt_restant_du": Decimal("0.00"),
            "total_a_regler": Decimal("0.00"),
            "situation": "EN_CONSTITUTION",
        },
    )
    return details


class ScanCINView(APIView):
    """Dépose un scan puis déclenche son traitement Celery."""

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser]

    def post(self, request, *args: Any, **kwargs: Any) -> Response:
        serializer = ScanCINSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        image = serializer.validated_data["image"]
        cin_number = serializer.validated_data.get("cin_number", "").upper()
        if cin_number and ClientProfile.objects.filter(cin_number=cin_number).exists():
            return Response(
                {
                    "status": "COMPLETED",
                    "exists": True,
                    "cin_searched": cin_number,
                    "message": "Dossier client existant trouvé après contrôle de la CIN.",
                },
                status=status.HTTP_200_OK,
            )
        image_path = default_storage.save(f"cin_scans/{image.name}", image)
        if settings.DEBUG:
            # En développement l'agent ne doit pas dépendre de Redis/Celery :
            # l'analyse est immédiate et la réponse reste toujours du JSON.
            task_result = process_cin_scan_task.apply(
                args=(image_path, request.user.pk, cin_number or None),
                throw=False,
            )
            if not task_result.successful():
                # Ne jamais renvoyer une page HTML Django à fetch(). L'agent
                # reçoit un message JSON exploitable et peut réessayer.
                return Response(
                    {
                        "detail": (
                            "Le scan n'a pas pu être traité. Vérifiez que l'image "
                            "est lisible puis réessayez."
                        )
                    },
                    status=status.HTTP_422_UNPROCESSABLE_ENTITY,
                )
            result = task_result.get()
            result["creation_url"] = _new_client_url(result["identity"])
            return Response(
                {
                    "status": "SUCCESS",
                    "exists": result.get("exists", False),
                    "cin_searched": result.get("cin", cin_number),
                    "mode": "LOCAL_FALLBACK",
                    "result": result,
                },
                status=status.HTTP_201_CREATED,
            )
        try:
            task = process_cin_scan_task.delay(image_path, request.user.pk, cin_number or None)
            return Response({"job_id": task.id, "status": "PENDING", "exists": False, "cin_searched": cin_number, "mode": "ASYNC"}, status=status.HTTP_202_ACCEPTED)
        except Exception:
            return Response(
                {"detail": "Le service de scan asynchrone est indisponible."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )


class JobStatusView(APIView):
    """Expose l'état et le résultat d'une tâche Celery."""

    permission_classes = [IsAuthenticated]

    def get(self, request, job_id: str, *args: Any, **kwargs: Any) -> Response:
        task = AsyncResult(job_id)
        payload: dict[str, Any] = {"job_id": job_id, "status": task.status}
        if task.successful():
            result = task.result
            if isinstance(result, dict) and result.get("identity"):
                result = {**result, "creation_url": _new_client_url(result["identity"])}
            payload["result"] = result
        elif task.failed():
            payload["error"] = "Le traitement du scan a échoué."
        return Response(payload)


class CreditSimulationView(APIView):
    """Calcule une simulation de crédit et trace la demande de l'agent."""

    permission_classes = [IsAuthenticated]

    def post(self, request, *args: Any, **kwargs: Any) -> Response:
        started_at = perf_counter()
        serializer = CreditSimulationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = EQDOMCreditSimulator(**serializer.validated_data).simulate()
        AuditLog.objects.create(
            agent=request.user,
            client_cin="SIMULATION",
            action="CREDIT_SIMULATION",
            status=AuditLog.Status.SUCCESS,
            response_time_ms=int((perf_counter() - started_at) * 1000),
        )
        return Response(result, status=status.HTTP_200_OK)


class CurrencyRateView(APIView):
    """Expose le repli serveur lorsque Frankfurter est indisponible côté web."""

    permission_classes = [IsAuthenticated]

    def get(self, request, *args: Any, **kwargs: Any) -> Response:
        currency = request.query_params.get("from", "MAD")
        try:
            return Response(get_mad_rate(currency))
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


def _get_workflow(cin: str, agent) -> DossierWorkflow:
    """Récupère ou initialise le workflow d'un client pour l'agent courant."""
    client = get_object_or_404(ClientProfile, cin_number=cin)
    workflow, _ = DossierWorkflow.objects.get_or_create(
        client=client,
        defaults={"assigned_agent": agent, "created_by": agent},
    )
    return workflow


def _diagnostic_payload(client: ClientProfile) -> dict[str, Any]:
    """Construit la vue 360° commune au diagnostic et à la recherche CIN."""
    details = client.core_banking_details
    return {
        "identite": ClientProfileSerializer(client).data,
        "core_banking": CoreBankingDetailsSerializer(details).data,
        "situation_impayes": {
            "nbr_impayes": details.nbr_impayes,
            "age_impayes_jours": details.age_impayes_jours,
            "total_impaye": details.total_impaye,
            "penalite_retard": details.penalite_retard,
            "total_a_regler": details.total_a_regler,
        },
        "feu_tricolore": _traffic_light(client),
    }


class ClientSearchView(APIView):
    """Recherche un client par CIN et distingue un nouveau dossier."""

    permission_classes = [IsAuthenticated]

    def get(self, request, *args: Any, **kwargs: Any) -> Response:
        cin = request.query_params.get("cin", "").strip().upper()
        if not cin:
            return Response({"detail": "Le paramètre cin est obligatoire."}, status=status.HTTP_400_BAD_REQUEST)
        client = ClientProfile.objects.select_related("core_banking_details").filter(cin_number=cin).first()
        if client is None:
            return Response({"exists": False, "cin_searched": cin, "message": "Client inexistant (Nouveau client)"})
        _ensure_initial_core_banking(client)
        profile = _diagnostic_payload(client)
        workflow = _get_workflow(cin, request.user)
        return Response({"exists": True, "client": profile, "workflow": DossierWorkflowSerializer(workflow, context={"request": request}).data})


class ClientAgencyLocationView(APIView):
    """Retourne une position client et l'agence EQDOM la plus proche."""

    permission_classes = [IsAuthenticated]

    def get(self, request, cin: str, *args: Any, **kwargs: Any) -> Response:
        client = get_object_or_404(ClientProfile, cin_number=cin)
        city = (
            request.query_params.get("ville", "").strip()
            or client.ville.strip()
            or get_reference_client_city(client.cin_number)
        )
        coordinates = get_client_coordinates(city)
        agency = get_nearest_agency(
            float(coordinates["latitude"]), float(coordinates["longitude"])
        )
        return Response(
            {
                "client": {
                    "cin": client.cin_number,
                    "ville": city,
                    "latitude": coordinates["latitude"],
                    "longitude": coordinates["longitude"],
                    "coordinates_source": coordinates["source"],
                },
                "agency": agency,
            }
        )


class CinImageSearchView(APIView):
    """Recherche un dossier à partir de l'OCR d'une image de CIN."""

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser]

    def post(self, request, *args: Any, **kwargs: Any) -> Response:
        serializer = ScanCINSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            identity = extract_moroccan_cin_identity(serializer.validated_data["image"].read())
            cin = identity["cin"]
        except OcrConfigurationError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except CinNotDetectedError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
        client = ClientProfile.objects.select_related("core_banking_details").filter(cin_number=cin).first()
        if client is None:
            # Le scan prépare uniquement la saisie : le dossier est créé
            # après la confirmation explicite de l'agent sur le formulaire.
            AuditLog.objects.create(agent=request.user, client_cin=cin, action="CIN_IMAGE_IDENTITY_EXTRACTED", status=AuditLog.Status.SUCCESS, response_time_ms=0)
            return Response(
                {
                    "exists": False,
                    "created": False,
                    "cin_searched": cin,
                    "identity": identity,
                    "creation_url": _new_client_url(identity),
                    "message": "Identité extraite. Complétez les informations client pour créer le dossier.",
                },
                status=status.HTTP_200_OK,
            )
        AuditLog.objects.create(agent=request.user, client_cin=cin, action="CIN_IMAGE_SEARCH", status=AuditLog.Status.SUCCESS, response_time_ms=0)
        _ensure_initial_core_banking(client)
        profile = _diagnostic_payload(client)
        workflow = _get_workflow(cin, request.user)
        return Response({"exists": True, "client": profile, "workflow": DossierWorkflowSerializer(workflow, context={"request": request}).data})


class ClientDossierPDFView(APIView):
    """Génère le résumé PDF téléchargeable d'un dossier client."""

    permission_classes = [IsAuthenticated]

    def get(self, request, cin: str, *args: Any, **kwargs: Any) -> HttpResponse:
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.pdfgen import canvas
        except ImportError:
            return HttpResponse("Le module PDF est indisponible.", status=503)
        client = get_object_or_404(ClientProfile.objects.select_related("core_banking_details"), cin_number=cin)
        details = client.core_banking_details
        buffer = BytesIO()
        pdf = canvas.Canvas(buffer, pagesize=A4)
        pdf.setTitle(f"EQDOM - Dossier {cin}")
        width, height = A4
        pdf.setFillColorRGB(0.04, 0.12, 0.29)
        pdf.rect(0, height - 90, width, 90, fill=1, stroke=0)
        pdf.setFillColorRGB(1, 1, 1)
        pdf.setFont("Helvetica-Bold", 20)
        pdf.drawString(48, height - 52, "EQDOM - Dossier Client")
        pdf.setFillColorRGB(0.1, 0.14, 0.22)
        pdf.setFont("Helvetica", 11)
        lines = [
            f"CIN : {client.cin_number}",
            f"Client : {client.prenom} {client.nom}",
            f"Telephone : {client.telephone}",
            f"Produit : {details.produit} ({details.etat})",
            f"Numero dossier : {details.numero_dossier or '-'}",
            f"Montant finance : {details.montant_finance} DH",
            f"Mensualite : {details.mensualite} DH",
            f"Echeances restantes : {details.nb_mensualites_restantes}",
            f"Impayes : {details.nbr_impayes}",
            f"Total a regler : {details.total_a_regler} DH",
            f"Situation : {details.situation}",
        ]
        y = height - 130
        for line in lines:
            pdf.drawString(55, y, line)
            y -= 25
        pdf.setFillColorRGB(0.39, 0.45, 0.55)
        pdf.setFont("Helvetica-Oblique", 9)
        pdf.drawString(55, 45, "Système d'Information EQDOM SA - Référence Client")
        pdf.save()
        AuditLog.objects.create(agent=request.user, client_cin=cin, action="CLIENT_DOSSIER_PDF_DOWNLOADED", status=AuditLog.Status.SUCCESS, response_time_ms=0)
        response = HttpResponse(buffer.getvalue(), content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="dossier_eqdom_{cin}.pdf"'
        return response


class WorkflowDetailView(APIView):
    """Retourne l'état collaboratif et les échanges d'un dossier."""

    permission_classes = [IsAuthenticated]

    def get(self, request, cin: str, *args: Any, **kwargs: Any) -> Response:
        workflow = _get_workflow(cin, request.user)
        return Response(DossierWorkflowSerializer(workflow, context={"request": request}).data)


class WorkflowStatusView(APIView):
    """Met à jour l'étape du workflow d'un dossier."""

    permission_classes = [IsAuthenticated]

    def patch(self, request, cin: str, *args: Any, **kwargs: Any) -> Response:
        serializer = WorkflowStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        workflow = _get_workflow(cin, request.user)
        next_status = serializer.validated_data["current_status"]
        protected_statuses = {
            DossierWorkflow.Status.FINANCEMENT,
            DossierWorkflow.Status.REFUSE,
        }
        if next_status in protected_statuses:
            if not is_responsable(request.user):
                return Response(
                    {"detail": "La décision finale est réservée au responsable."},
                    status=status.HTTP_403_FORBIDDEN,
                )
            return Response(
                {"detail": "Utilisez la décision responsable pour valider ou refuser ce dossier."},
                status=status.HTTP_409_CONFLICT,
            )
        workflow.current_status = next_status
        workflow.assigned_agent = request.user
        workflow.save(update_fields=["current_status", "assigned_agent", "updated_at"])
        AuditLog.objects.create(agent=request.user, client_cin=cin, action="WORKFLOW_STATUS_UPDATED", status=AuditLog.Status.SUCCESS, response_time_ms=0)
        return Response(DossierWorkflowSerializer(workflow, context={"request": request}).data)


class WorkflowAgentsView(APIView):
    """Liste les agents actifs pouvant recevoir un dossier."""

    permission_classes = [IsAuthenticated]

    def get(self, request, *args: Any, **kwargs: Any) -> Response:
        users = get_user_model().objects.filter(
            is_active=True,
            profile__role="AGENT",
        ).order_by("username")
        return Response({"agents": list(users.values("id", "username"))})


class WorkflowAssignmentView(APIView):
    """Transfère l'assignation d'un dossier à un autre agent actif."""

    permission_classes = [IsAuthenticated]

    def patch(self, request, cin: str, *args: Any, **kwargs: Any) -> Response:
        serializer = WorkflowAssignmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        agent = get_object_or_404(
            get_user_model(),
            pk=serializer.validated_data["agent_id"],
            is_active=True,
            profile__role="AGENT",
        )
        workflow = _get_workflow(cin, request.user)
        workflow.assigned_agent = agent
        workflow.save(update_fields=["assigned_agent", "updated_at"])
        AuditLog.objects.create(agent=request.user, client_cin=cin, action="WORKFLOW_ASSIGNED_TO_AGENT", status=AuditLog.Status.SUCCESS, response_time_ms=0)
        return Response(DossierWorkflowSerializer(workflow, context={"request": request}).data)


class WorkflowCommentCreateView(APIView):
    """Publie une note de premier niveau dans le fil du dossier."""

    permission_classes = [IsAuthenticated]

    def post(self, request, cin: str, *args: Any, **kwargs: Any) -> Response:
        serializer = WorkflowCommentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        workflow = _get_workflow(cin, request.user)
        comment = WorkflowComment.objects.create(workflow=workflow, author=request.user, content=serializer.validated_data["content"])
        AuditLog.objects.create(agent=request.user, client_cin=cin, action="WORKFLOW_COMMENT_CREATED", status=AuditLog.Status.SUCCESS, response_time_ms=0)
        return Response(WorkflowCommentSerializer(comment, context={"request": request}).data, status=status.HTTP_201_CREATED)


class WorkflowReplyView(APIView):
    """Ajoute une réponse à une note existante."""

    permission_classes = [IsAuthenticated]

    def post(self, request, comment_id: int, *args: Any, **kwargs: Any) -> Response:
        serializer = WorkflowCommentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        parent = get_object_or_404(WorkflowComment, pk=comment_id)
        comment = WorkflowComment.objects.create(workflow=parent.workflow, author=request.user, parent_comment=parent, content=serializer.validated_data["content"])
        AuditLog.objects.create(agent=request.user, client_cin=parent.workflow.client.cin_number, action="WORKFLOW_REPLY_CREATED", status=AuditLog.Status.SUCCESS, response_time_ms=0)
        return Response(WorkflowCommentSerializer(comment, context={"request": request}).data, status=status.HTTP_201_CREATED)


class WorkflowLikeView(APIView):
    """Ajoute ou retire le like de l'agent courant sur une note."""

    permission_classes = [IsAuthenticated]

    def post(self, request, comment_id: int, *args: Any, **kwargs: Any) -> Response:
        comment = get_object_or_404(WorkflowComment, pk=comment_id)
        if comment.likes.filter(pk=request.user.pk).exists():
            comment.likes.remove(request.user)
            liked = False
        else:
            comment.likes.add(request.user)
            liked = True
        return Response({"comment_id": comment.pk, "liked": liked, "likes_count": comment.likes.count()})


class ResponsableDossierListView(APIView):
    """Expose la file de validation de tous les agents au responsable."""

    permission_classes = [IsResponsable]

    def get(self, request, *args: Any, **kwargs: Any) -> Response:
        workflows = DossierWorkflow.objects.select_related(
            "client", "assigned_agent", "created_by"
        ).prefetch_related("comments")
        agent_filter = request.query_params.get("agent", "").strip()
        if agent_filter:
            normalized = agent_filter.lower()
            usernames = {normalized}
            if not normalized.startswith("agent_"):
                usernames.add(f"agent_{normalized}")
            workflows = workflows.filter(created_by__username__in=usernames)
        agents = get_user_model().objects.filter(
            is_active=True,
            profile__role="AGENT",
        ).order_by("username")
        dossier_data = ResponsableDossierSerializer(
            workflows, many=True, context={"request": request}
        ).data
        total = len(dossier_data)
        financing = sum(item["current_status"] == DossierWorkflow.Status.FINANCEMENT for item in dossier_data)
        refused = sum(item["current_status"] == DossierWorkflow.Status.REFUSE for item in dossier_data)
        pending = sum(item["current_status"] == DossierWorkflow.Status.PENDING_VALIDATION for item in dossier_data)
        return Response(
            {
                "dossiers": dossier_data,
                "agents": list(agents.values("id", "username")),
                "kpis": {
                    "total_dossiers": total,
                    "en_attente_validation": pending,
                    "financements": financing,
                    "refus": refused,
                    "taux_acceptation": round((financing / (financing + refused) * 100), 1) if financing + refused else 0,
                },
            }
        )


class ResponsableDossierCSVExportView(APIView):
    """Exporte les dossiers visibles par le responsable au format CSV."""

    permission_classes = [IsResponsable]

    def get(self, request, *args: Any, **kwargs: Any) -> HttpResponse:
        workflows = DossierWorkflow.objects.select_related("client", "assigned_agent", "created_by")
        agent_filter = request.query_params.get("agent", "").strip()
        if agent_filter:
            usernames = {agent_filter.lower()}
            if not agent_filter.lower().startswith("agent_"):
                usernames.add(f"agent_{agent_filter.lower()}")
            workflows = workflows.filter(created_by__username__in=usernames)
        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = 'attachment; filename="eqdom_dossiers.csv"'
        response.write("\ufeff")
        writer = csv.writer(response, delimiter=";")
        writer.writerow(["CIN", "Client", "Agent créateur", "Agent assigné", "Statut", "Dernière mise à jour"])
        for workflow in workflows:
            writer.writerow([workflow.client.cin_number, f"{workflow.client.prenom} {workflow.client.nom}", workflow.created_by.get_username(), workflow.assigned_agent.get_username(), workflow.get_current_status_display(), workflow.updated_at.strftime("%d/%m/%Y %H:%M")])
        return response


class ClientTimelineView(APIView):
    """Regroupe les événements audit et les échanges workflow en une timeline."""

    permission_classes = [IsAuthenticated]

    def get(self, request, cin: str, *args: Any, **kwargs: Any) -> Response:
        client = get_object_or_404(ClientProfile, cin_number=cin)
        events: list[dict[str, Any]] = []
        for audit in AuditLog.objects.filter(client_cin__iexact=client.cin_number).select_related("agent"):
            events.append({"timestamp": audit.timestamp, "type": "audit", "author": audit.agent.get_username(), "label": audit.action.replace("_", " ").title(), "detail": audit.get_status_display()})
        # A reverse OneToOne relation raises ``DoesNotExist`` when the client
        # has not reached the workflow stage yet.  A timeline must still work
        # for a newly created client, so treat that case as an empty workflow.
        try:
            workflow = client.workflow
        except DossierWorkflow.DoesNotExist:
            workflow = None
        if workflow:
            events.append({"timestamp": workflow.updated_at, "type": "status", "author": workflow.assigned_agent.get_username(), "label": f"Étape actuelle : {workflow.get_current_status_display()}", "detail": "Workflow mis à jour"})
            for comment in workflow.comments.select_related("author"):
                events.append({"timestamp": comment.created_at, "type": "comment", "author": comment.author.get_username(), "label": "Note interne", "detail": comment.content})
        events.sort(key=lambda item: item["timestamp"], reverse=True)
        return Response({"cin": client.cin_number, "events": events[:50]})


class ResponsableDecisionView(APIView):
    """Valide ou refuse un dossier soumis au responsable."""

    permission_classes = [IsResponsable]

    def post(self, request, dossier_id: int, *args: Any, **kwargs: Any) -> Response:
        serializer = ResponsableDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        workflow = get_object_or_404(
            DossierWorkflow.objects.select_related("client", "created_by", "assigned_agent"),
            pk=dossier_id,
        )
        if workflow.current_status != DossierWorkflow.Status.PENDING_VALIDATION:
            return Response(
                {"detail": "Seuls les dossiers en attente de validation peuvent recevoir une décision."},
                status=status.HTTP_409_CONFLICT,
            )

        action = serializer.validated_data["action"]
        if action == "APPROVE":
            workflow.current_status = DossierWorkflow.Status.FINANCEMENT
            note = (
                f"Décision responsable : dossier validé pour financement. "
                f"Information transmise à {workflow.created_by.get_username()}."
            )
            audit_action = "RESPONSABLE_DOSSIER_APPROVED"
        else:
            workflow.current_status = DossierWorkflow.Status.REFUSE
            motif = serializer.validated_data["motif_refus"].strip()
            note = (
                f"Décision responsable : dossier refusé. Motif : {motif}. "
                f"Information transmise à {workflow.created_by.get_username()}."
            )
            audit_action = "RESPONSABLE_DOSSIER_REJECTED"
        workflow.save(update_fields=["current_status", "updated_at"])
        WorkflowComment.objects.create(workflow=workflow, author=request.user, content=note)
        AuditLog.objects.create(
            agent=request.user,
            client_cin=workflow.client.cin_number,
            action=audit_action,
            status=AuditLog.Status.SUCCESS,
            response_time_ms=0,
        )
        return Response(DossierWorkflowSerializer(workflow, context={"request": request}).data)


class FastTrackDiagnosticView(APIView):
    """Retourne la vue 360° d'un client identifié par sa CIN."""

    permission_classes = [IsAuthenticated]

    def get(self, request, cin: str, *args: Any, **kwargs: Any) -> Response:
        client = get_object_or_404(
            ClientProfile.objects.select_related("core_banking_details"), cin_number=cin
        )
        _ensure_initial_core_banking(client)
        return Response(_diagnostic_payload(client))


class WhatsAppMessageView(APIView):
    """Prépare un message WhatsApp adapté à la situation d'un client."""

    permission_classes = [IsAuthenticated]

    def post(self, request, cin: str, *args: Any, **kwargs: Any) -> Response:
        client = get_object_or_404(
            ClientProfile.objects.select_related("core_banking_details"), cin_number=cin
        )
        try:
            details = client.core_banking_details
        except CoreBankingDetails.DoesNotExist:
            return Response(
                {"detail": "Les détails Core Banking sont absents."},
                status=status.HTTP_409_CONFLICT,
            )
        if not client.telephone:
            return Response(
                {"detail": "Aucun message : le téléphone du client est absent."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        message_type, message, whatsapp_url = build_whatsapp_client_message(
            prenom=client.prenom,
            nom=client.nom,
            telephone=client.telephone,
            mensualite=details.mensualite,
            total_a_regler=details.total_a_regler,
            has_impayees=details.nbr_impayes > 0 and details.total_a_regler > 0,
        )
        AuditLog.objects.create(
            agent=request.user,
            client_cin=client.cin_number,
            action=f"WHATSAPP_{message_type}_PREPARED",
            status=AuditLog.Status.SUCCESS,
            response_time_ms=0,
        )
        return Response({
            "message": message,
            "whatsapp_url": whatsapp_url,
            "message_type": message_type,
            "status": "PREPARED",
        })
