"""Prépare les relances WhatsApp sans effectuer d'envoi automatique."""

import re
from decimal import Decimal
from urllib.parse import quote


def build_whatsapp_reminder(
    *,
    prenom: str,
    nom: str,
    telephone: str,
    total_a_regler: Decimal,
) -> tuple[str, str]:
    """Retourne le message de relance et son lien WhatsApp prérempli.

    L'URL ouvre WhatsApp ; l'agent conserve la validation finale de l'envoi.
    """
    digits = re.sub(r"\D", "", telephone)
    if digits.startswith("0"):
        digits = f"212{digits[1:]}"
    elif not digits.startswith("212"):
        digits = f"212{digits}"

    amount = f"{total_a_regler:,.2f}".replace(",", " ").replace(".", ",")
    message = (
        f"Bonjour {prenom.title()} {nom.title()}, c'est EQDOM. "
        f"Votre dossier présente des impayés d'un montant de {amount} DH. "
        "Veuillez régulariser votre situation auprès de votre agence EQDOM."
    )
    return message, f"https://wa.me/{digits}?text={quote(message)}"


def build_whatsapp_client_message(
    *,
    prenom: str,
    nom: str,
    telephone: str,
    mensualite: Decimal,
    total_a_regler: Decimal,
    has_impayees: bool,
) -> tuple[str, str, str]:
    """Construit un message WhatsApp adapté à la situation du dossier."""
    if has_impayees:
        message, url = build_whatsapp_reminder(
            prenom=prenom,
            nom=nom,
            telephone=telephone,
            total_a_regler=total_a_regler,
        )
        return "PAYMENT_REMINDER", message, url

    digits = re.sub(r"\D", "", telephone)
    if digits.startswith("0"):
        digits = f"212{digits[1:]}"
    elif not digits.startswith("212"):
        digits = f"212{digits}"
    monthly_amount = f"{mensualite:,.2f}".replace(",", " ").replace(".", ",")
    message = (
        f"Bonjour {prenom.title()} {nom.title()}, c'est EQDOM. "
        f"Votre dossier est à jour. Votre mensualité actuelle est de {monthly_amount} DH. "
        "Nous restons à votre disposition dans votre agence EQDOM."
    )
    return "ACCOUNT_UP_TO_DATE", message, f"https://wa.me/{digits}?text={quote(message)}"
