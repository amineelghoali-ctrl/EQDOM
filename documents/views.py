"""API GED pour les dossiers clients."""

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.parsers import JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from fasttrack.models import AuditLog, ClientProfile

from .models import ClientContractSignature, ClientDocument
from .services import build_contract_pdf, decode_signature, extract_payslip_income


def document_payload(document: ClientDocument | None, document_type: str, label: str) -> dict:
    """Construit une ligne de checklist, même lorsqu'aucun fichier n'existe."""
    return {
        "id": document.pk if document else None,
        "document_type": document_type,
        "label": label,
        "status": document.status if document else ClientDocument.Status.MANQUANT,
        "status_label": document.get_status_display() if document else "Manquant",
        "file_url": document.file.url if document and document.file else None,
        "uploaded_at": document.uploaded_at if document else None,
        "ocr_status": document.ocr_status if document else "NOT_APPLICABLE",
        "extracted_monthly_income": document.extracted_monthly_income if document else None,
    }


class ClientDocumentChecklistView(APIView):
    """Retourne la checklist documentaire et accepte un dépôt de fichier."""

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser]

    def get(self, request, cin: str, *args, **kwargs) -> Response:
        client = get_object_or_404(ClientProfile, cin_number=cin)
        records = {item.document_type: item for item in client.ged_documents.all()}
        checklist = [
            document_payload(records.get(value), value, label)
            for value, label in ClientDocument.DocumentType.choices
        ]
        return Response({"cin": client.cin_number, "documents": checklist})

    def post(self, request, cin: str, *args, **kwargs) -> Response:
        client = get_object_or_404(ClientProfile, cin_number=cin)
        document_type = request.data.get("document_type", "")
        uploaded_file = request.FILES.get("file")
        valid_types = {value for value, _ in ClientDocument.DocumentType.choices}
        if document_type not in valid_types or not uploaded_file:
            return Response({"detail": "Le type de document et le fichier sont obligatoires."}, status=400)
        if uploaded_file.size > 8 * 1024 * 1024:
            return Response({"detail": "Le document ne doit pas dépasser 8 Mo."}, status=400)
        document, _ = ClientDocument.objects.update_or_create(
            client=client,
            document_type=document_type,
            defaults={"file": uploaded_file, "status": ClientDocument.Status.CONFORME},
        )
        if document_type == ClientDocument.DocumentType.FICHE_PAIE and (uploaded_file.content_type or "").startswith("image/"):
            result = extract_payslip_income(document.file.path)
            document.ocr_text = result["text"]
            document.ocr_status = result["status"]
            document.extracted_monthly_income = result["income"]
            document.save(update_fields=["ocr_text", "ocr_status", "extracted_monthly_income"])
        AuditLog.objects.create(agent=request.user, client_cin=client.cin_number, action="DOCUMENT_UPLOADED", status=AuditLog.Status.SUCCESS)
        return Response(document_payload(document, document_type, document.get_document_type_display()), status=status.HTTP_201_CREATED)


class ClientDocumentStatusView(APIView):
    """Met à jour le contrôle d'un document déposé."""

    permission_classes = [IsAuthenticated]

    def patch(self, request, document_id: int, *args, **kwargs) -> Response:
        document = get_object_or_404(ClientDocument, pk=document_id)
        new_status = request.data.get("status", "")
        valid_statuses = {value for value, _ in ClientDocument.Status.choices}
        if new_status not in valid_statuses:
            return Response({"detail": "Statut documentaire invalide."}, status=400)
        document.status = new_status
        document.save(update_fields=["status"])
        AuditLog.objects.create(agent=request.user, client_cin=document.client.cin_number, action="DOCUMENT_STATUS_UPDATED", status=AuditLog.Status.SUCCESS)
        return Response(document_payload(document, document.document_type, document.get_document_type_display()))


class ClientContractSignatureView(APIView):
    """Enregistre une signature canvas et produit immédiatement un contrat PDF."""

    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser]

    def get(self, request, cin: str, *args, **kwargs) -> Response:
        client = get_object_or_404(ClientProfile, cin_number=cin)
        signature = getattr(client, "contract_signature", None)
        return Response({
            "signed": bool(signature),
            "contract_url": signature.contract_pdf.url if signature and signature.contract_pdf else None,
            "signed_at": signature.signed_at if signature else None,
        })

    def post(self, request, cin: str, *args, **kwargs) -> Response:
        client = get_object_or_404(ClientProfile, cin_number=cin)
        try:
            signature_file = decode_signature(request.data.get("signature", ""))
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        details = getattr(client, "core_banking_details", None)
        if details is None:
            return Response({"detail": "Les informations de crédit sont nécessaires avant signature."}, status=400)
        record = getattr(client, "contract_signature", None)
        if record is None:
            record = ClientContractSignature.objects.create(
                client=client,
                signed_by=request.user,
                signature_image=signature_file,
            )
        else:
            record.signed_by = request.user
            record.signature_image = signature_file
            record.save(update_fields=["signed_by", "signature_image", "signed_at"])
        contract = build_contract_pdf(client, details, record.signature_image.path)
        record.contract_pdf = contract
        record.save(update_fields=["contract_pdf", "signed_at"])
        AuditLog.objects.create(agent=request.user, client_cin=client.cin_number, action="CONTRACT_SIGNED_AND_GENERATED", status=AuditLog.Status.SUCCESS)
        return Response({"signed": True, "contract_url": record.contract_pdf.url, "signed_at": record.signed_at}, status=201)
