"""Complète les profils existants sans prêt mock associé."""

from django.core.management.base import BaseCommand

from fasttrack.models import ClientProfile, CoreBankingDetails
from fasttrack.services.mock_core_banking import build_core_banking_defaults


class Command(BaseCommand):
    help = "Ajoute des détails Core Banking mock aux profils incomplets."

    def handle(self, *args, **options) -> None:
        created = 0
        enriched = 0
        clients = ClientProfile.objects.filter(core_banking_details__isnull=True)
        for client in clients:
            CoreBankingDetails.objects.create(
                client=client,
                **build_core_banking_defaults(),
            )
            created += 1
        # Les profils créés avant l'ajout des champs AS/400 ont un numéro de
        # dossier vide : on les enrichit sans toucher aux profils complets.
        details_without_dossier = CoreBankingDetails.objects.filter(
            numero_dossier__isnull=True
        )
        for details in details_without_dossier:
            defaults = build_core_banking_defaults()
            for field, value in defaults.items():
                setattr(details, field, value)
            details.save()
            enriched += 1
        self.stdout.write(
            self.style.SUCCESS(
                f"{created} dossier(s) créé(s), {enriched} dossier(s) enrichi(s)."
            )
        )
