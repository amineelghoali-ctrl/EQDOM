"""Génère les dossiers clients fictifs du démonstrateur EQDOM."""

import random
from datetime import date, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from faker import Faker

from fasttrack.models import ClientProfile, CoreBankingDetails
from fasttrack.services.mock_core_banking import build_core_banking_defaults


MOCK_CLIENTS = (
    {"prenom": "AMINE", "nom": "GHOUALI", "telephone": "0674354575", "ville": "Casablanca", "adresse": "Boulevard Zerktouni, Casablanca"},
    {"prenom": "ACHRAF", "nom": "GHALI", "ville": "Rabat", "adresse": "Avenue Fal Ould Oumeir, Agdal, Rabat"},
    {"prenom": "ANAS", "nom": "TAZI", "ville": "Fès", "adresse": "Avenue Hassan II, Fès"},
    {"prenom": "ADAM", "nom": "NORRI", "ville": "Marrakech", "adresse": "Avenue Mohammed VI, Guéliz, Marrakech"},
    {"prenom": "MOHAMED", "nom": "AKKAD", "ville": "Tanger", "adresse": "Boulevard Pasteur, Tanger"},
    {"prenom": "MEHDI", "nom": "HADIDI", "ville": "Kénitra", "adresse": "Avenue Mohammed V, Kénitra"},
    {"prenom": "SALAHDIN", "nom": "RAWI", "ville": "Oujda", "adresse": "Boulevard Mohammed V, Oujda"},
    {"prenom": "OMAR", "nom": "NABI", "ville": "Agadir", "adresse": "Avenue des FAR, Agadir"},
    {"prenom": "HIBA", "nom": "NAIL", "ville": "Meknès", "adresse": "Avenue des FAR, Meknès"},
)


class Command(BaseCommand):
    help = "Crée ou met à jour les 9 dossiers clients fictifs EQDOM."

    def handle(self, *args, **options) -> None:
        fake = Faker("fr_FR")
        created_count = 0
        for index, identity in enumerate(MOCK_CLIENTS, start=1):
            cin = f"MOCK{index:06d}"
            has_impayees = index == 1
            client, created = ClientProfile.objects.update_or_create(
                cin_number=cin,
                defaults={
                    **identity,
                    "telephone": identity.get("telephone", f"06{random.randint(10000000, 99999999)}"),
                    "autres_telephones": f"05{random.randint(10000000, 99999999)}",
                    "date_naissance": fake.date_of_birth(minimum_age=25, maximum_age=65),
                    "employeur": fake.company(),
                    "drpp_number": f"DRPP{random.randint(100000, 999999)}",
                    "cnss_number": f"CNSS{random.randint(100000, 999999)}",
                    "cmr_number": f"CMR{random.randint(100000, 999999)}",
                    "total_engagement": Decimal(str(random.randrange(5000, 50001, 500))),
                    "liveness_verified": index != len(MOCK_CLIENTS),
                    "face_match_score": round(random.uniform(0.84, 0.99), 2),
                },
            )
            montant = Decimal(str(random.randrange(30000, 120001, 5000)))
            impaye = Decimal(str(random.randrange(700, 6001, 100) if has_impayees else 0))
            penalite = (impaye * Decimal("0.04")).quantize(Decimal("0.01"))
            CoreBankingDetails.objects.update_or_create(
                client=client,
                defaults={
                    **build_core_banking_defaults(),
                    "produit": random.choice(["Crédit Personnel", "Crédit Auto", "Crédit Équipement"]),
                    "mode_prelevement": random.choice(["Virement", "Prélèvement bancaire"]),
                    "montant_credit": montant,
                    "mensualite": Decimal(str(random.randrange(900, 3501, 100))),
                    "nb_mensualites_total": 60,
                    "nb_mensualites_restantes": random.randint(6, 52),
                    "nbr_impayes": random.randint(1, 4) if has_impayees else 0,
                    "age_impayes_jours": random.randint(15, 140) if has_impayees else 0,
                    "total_impaye": impaye,
                    "penalite_retard": penalite,
                    "int_retard_ttc": penalite,
                    "frais_justice": Decimal("0.00"),
                    "mt_restant_du": (montant * Decimal("0.45")).quantize(Decimal("0.01")),
                    "total_a_regler": (impaye + penalite * 2).quantize(Decimal("0.01")),
                    "date_dernier_reglement": date.today() - timedelta(days=random.randint(0, 120)),
                },
            )
            created_count += int(created)

        removed_count, _ = ClientProfile.objects.filter(cin_number="MOCK000010").delete()
        self.stdout.write(self.style.SUCCESS(f"9 clients mock mis à jour ({created_count} nouveaux, {removed_count} ancien enregistrement supprimé)."))
