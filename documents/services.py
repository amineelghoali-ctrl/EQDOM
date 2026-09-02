"""Services locaux pour l'OCR documentaire et le contrat PDF."""

from __future__ import annotations

import base64
import re
from decimal import Decimal, InvalidOperation
from io import BytesIO
from pathlib import Path
from typing import Any

from django.core.files.base import ContentFile
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas


def extract_payslip_income(file_path: str) -> dict[str, Any]:
    """Lit localement une image de fiche de paie et tente d'en extraire le net.

    EasyOCR n'appelle aucun service distant. L'échec est volontairement doux :
    le dépôt GED reste disponible et l'agent saisit le montant manuellement.
    """
    try:
        from fasttrack.services.cin_ocr import get_reader

        lines = get_reader().readtext(file_path, detail=0, paragraph=True)
        text = "\n".join(lines)
    except Exception:
        return {"status": "UNAVAILABLE", "text": "", "income": None}

    normalized = text.replace(" ", "")
    patterns = (
        r"(?:NET[AÀ]PAYER|SALAIRENET|NETIMPOSSABLE)[:\-]?([0-9][0-9.,]+)",
        r"(?:NET)[:\-]?([0-9][0-9.,]+)",
    )
    for pattern in patterns:
        match = re.search(pattern, normalized, flags=re.IGNORECASE)
        if not match:
            continue
        raw = match.group(1).replace(".", "").replace(",", ".")
        try:
            return {"status": "EXTRACTED", "text": text[:5000], "income": Decimal(raw)}
        except InvalidOperation:
            continue
    return {"status": "NO_AMOUNT_FOUND", "text": text[:5000], "income": None}


def decode_signature(data_url: str) -> ContentFile:
    """Valide et convertit le PNG créé par le canvas en fichier Django."""
    prefix = "data:image/png;base64,"
    if not data_url.startswith(prefix):
        raise ValueError("La signature doit être une image PNG issue du canvas.")
    try:
        raw = base64.b64decode(data_url[len(prefix):], validate=True)
    except ValueError as exc:
        raise ValueError("Image de signature invalide.") from exc
    if not raw or len(raw) > 2 * 1024 * 1024:
        raise ValueError("La signature doit faire entre 1 octet et 2 Mo.")
    return ContentFile(raw, name="signature.png")


def build_contract_pdf(client, details, signature_path: str) -> ContentFile:
    """Génère le contrat de financement avec la signature enregistrée."""
    output = BytesIO()
    pdf = canvas.Canvas(output, pagesize=A4)
    width, height = A4
    pdf.setTitle(f"Contrat EQDOM - Référence {client.cin_number}")
    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawString(2 * cm, height - 2.2 * cm, "EQDOM — CONTRAT DE FINANCEMENT")
    pdf.setFont("Helvetica", 10)
    pdf.drawString(2 * cm, height - 3 * cm, "EXEMPLAIRE ORIGINAL - CONTRAT DE FINANCEMENT")
    fields = (
        ("Client", f"{client.prenom} {client.nom}"),
        ("CIN", client.cin_number),
        ("Produit", details.produit),
        ("Montant demandé", f"{details.montant_credit:,.2f} DH"),
        ("Mensualité", f"{details.mensualite:,.2f} DH"),
        ("Durée", f"{details.nb_mensualites_total} mois"),
    )
    y = height - 4.3 * cm
    for label, value in fields:
        pdf.setFont("Helvetica-Bold", 10)
        pdf.drawString(2 * cm, y, f"{label} :")
        pdf.setFont("Helvetica", 10)
        pdf.drawString(6.3 * cm, y, str(value))
        y -= 0.7 * cm
    pdf.setStrokeColorRGB(0.75, 0.75, 0.75)
    pdf.line(2 * cm, 7 * cm, 9 * cm, 7 * cm)
    pdf.setFont("Helvetica", 9)
    pdf.drawString(2 * cm, 6.5 * cm, "SIGNATURE ET BON POUR ACCORD DU CLIENT & VISA DE L'AGENCE")
    try:
        pdf.drawImage(str(Path(signature_path)), 2 * cm, 3.5 * cm, width=6 * cm, height=2.5 * cm, preserveAspectRatio=True, mask="auto")
    except Exception:
        pdf.drawString(2 * cm, 5.5 * cm, "Signature enregistrée — image non disponible dans ce rendu.")
    pdf.setFont("Helvetica-Oblique", 8)
    pdf.drawString(2 * cm, 1.7 * cm, "Document généré par le Système d'Information EQDOM SA.")
    pdf.drawString(2 * cm, 1.3 * cm, "EQDOM S.A. au capital de 105.600.000 DH - Agrément n° 345/99 - Siège social : Casablanca. Conforme à la loi CNDP 09-08.")
    pdf.save()
    return ContentFile(output.getvalue(), name=f"contrat_{client.cin_number}.pdf")
