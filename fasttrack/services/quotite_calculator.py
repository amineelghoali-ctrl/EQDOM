"""Calcul de la quotité CMR selon le barème métier EQDOM."""

from typing import TypedDict


class CmrQuotiteResult(TypedDict):
    quotite_max: float
    eligible: bool
    motif_decision: str


def calculate_cmr_quotite(
    salaire_net: float,
    nb_enfants: int,
    mensualites_actives: float,
) -> CmrQuotiteResult:
    """Calcule la mensualité maximale mobilisable pour un client CMR.

    Raises:
        ValueError: Si l'un des montants ou le nombre d'enfants est négatif.
    """
    if salaire_net < 0 or mensualites_actives < 0 or nb_enfants < 0:
        raise ValueError("Les données de calcul ne peuvent pas être négatives.")

    bareme = {0: 1500.0, 1: 1800.0, 2: 2100.0, 3: 2400.0, 4: 2436.0, 5: 2472.0}
    deduction_insaisissable = bareme.get(nb_enfants, 2508.0)
    quotite_max = round(salaire_net - deduction_insaisissable - mensualites_actives, 2)
    eligible = quotite_max > 0

    motif = (
        "Client éligible : une capacité mensuelle est disponible."
        if eligible
        else "Client non éligible : le revenu disponible est nul ou insuffisant."
    )
    return {
        "quotite_max": max(0.0, quotite_max),
        "eligible": eligible,
        "motif_decision": motif,
    }
