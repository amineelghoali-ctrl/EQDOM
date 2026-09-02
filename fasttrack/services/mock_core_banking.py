"""Génération de valeurs initiales cohérentes pour le Core Banking."""

import random
from datetime import date, timedelta
from decimal import Decimal


def build_core_banking_defaults() -> dict[str, object]:
    """Retourne un prêt cohérent pour un dossier créé manuellement."""
    has_impayees = random.choice([False, False, True])
    montant_credit = Decimal(str(random.randrange(30000, 100001, 5000)))
    total_impaye = Decimal(str(random.randrange(600, 5001, 100) if has_impayees else 0))
    penalite = (total_impaye * Decimal("0.04")).quantize(Decimal("0.01"))

    return {
        "produit": "Crédit Personnel",
        "mode_prelevement": "Prélèvement bancaire",
        "etat": "ACTIF",
        "provenance": "AGENCE",
        "numero_dossier": f"DOS-SI-{random.randint(100000, 999999)}",
        "revendeur": "EQDOM Direct",
        "montant_credit": montant_credit,
        "montant_precompte": Decimal("0.00"),
        "montant_finance": montant_credit,
        "mensualite": Decimal(str(random.randrange(900, 3001, 100))),
        "code_dit": "DIT-SI",
        "nb_mensualites_total": 60,
        "nb_mensualites_restantes": random.randint(12, 48),
        "date_acceptation": date.today() - timedelta(days=random.randint(180, 720)),
        "date_financement": date.today() - timedelta(days=random.randint(120, 600)),
        "date_premiere_echeance": date.today() - timedelta(days=random.randint(90, 500)),
        "date_derniere_echeance": date.today() + timedelta(days=random.randint(180, 1200)),
        "banque": "Banque partenaire",
        "total_traite": (montant_credit * Decimal("0.55")).quantize(Decimal("0.01")),
        "nbr_impayes": random.randint(1, 3) if has_impayees else 0,
        "age_impayes_jours": random.randint(15, 90) if has_impayees else 0,
        "total_impaye": total_impaye,
        "penalite_retard": penalite,
        "int_retard_ttc": penalite,
        "frais_justice": Decimal("0.00"),
        "nbr_reports": 0,
        "honoraires_avocat": Decimal("0.00"),
        "frais_report": Decimal("0.00"),
        "montant_compense": Decimal("0.00"),
        "montant_solde_provision": Decimal("0.00"),
        "mt_restant_du": (montant_credit * Decimal("0.45")).quantize(Decimal("0.01")),
        "total_a_regler": (total_impaye + penalite * 2).quantize(Decimal("0.01")),
        "date_dernier_reglement": date.today() - timedelta(days=random.randint(0, 60)),
        "situation": "IMPAYE" if has_impayees else "NORMAL",
        "date_situation": date.today(),
        "restructuration": False,
    }
