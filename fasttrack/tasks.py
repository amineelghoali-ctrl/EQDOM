"""Tâches Celery du parcours de scan CIN.

Le scan ne fabrique aucune donnée financière ou de contact : il ne crée que
l'identité lue sur l'image. L'agent complète ensuite le dossier.
"""

from time import perf_counter
from typing import Any

from celery import shared_task
from django.contrib.auth import get_user_model
from django.core.files.storage import default_storage

from .models import AuditLog
from .services.cin_ocr import extract_moroccan_cin_identity


@shared_task(bind=True)
def process_cin_scan_task(
    self,
    image_path: str,
    agent_id: int,
    cin_number: str | None = None,
) -> dict[str, Any]:
    """Lit une CIN sans créer de profil avant validation par l'agent."""
    started_at = perf_counter()
    generated_cin = (cin_number or "").strip().upper()

    try:
        with default_storage.open(image_path, "rb") as image_file:
            identity = extract_moroccan_cin_identity(
                image_file.read(),
                expected_cin=generated_cin or None,
            )
        generated_cin = identity["cin"]
        agent = get_user_model().objects.get(pk=agent_id)
        AuditLog.objects.create(
            agent=agent,
            client_cin=generated_cin,
            action="CIN_SCAN_IDENTITY_EXTRACTED",
            status=AuditLog.Status.SUCCESS,
            response_time_ms=int((perf_counter() - started_at) * 1000),
        )

        return {
            "success": True,
            "exists": False,
            "cin": generated_cin,
            "identity": {
                "cin_number": generated_cin,
                "nom": identity["nom"],
                "prenom": identity["prenom"],
                "name_detected": identity["name_detected"],
            },
            "message": "Identité extraite. Complétez le dossier avant son enregistrement.",
        }
    except Exception as exc:
        try:
            agent = get_user_model().objects.get(pk=agent_id)
            AuditLog.objects.create(
                agent=agent, client_cin=generated_cin or "INCONNUE", action="CIN_SCAN",
                status=AuditLog.Status.FAILURE,
                response_time_ms=int((perf_counter() - started_at) * 1000),
            )
        except Exception:
            pass
        raise self.retry(exc=exc, countdown=3, max_retries=2)
