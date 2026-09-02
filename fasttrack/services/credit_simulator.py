"""Moteur de simulation de crédit EQDOM basé sur des règles de gestion."""

from dataclasses import dataclass
from math import pow
from typing import TypedDict

from .quotite_calculator import calculate_cmr_quotite


class CreditSimulationResult(TypedDict):
    mensualite_totale: float
    mensualite_hors_assurance: float
    assurance_mensuelle: float
    frais_dossier: float
    cout_total_credit: float
    taux_applique: float
    taux_base: float
    reduction_convention: float
    quotite_max_client: float
    regle_quotite: str
    eligible: bool
    status_code: str
    message_decision: str


@dataclass(frozen=True)
class EQDOMCreditSimulator:
    """Applique les règles tarifaires et de capacité de remboursement EQDOM."""

    montant: float
    duree_mois: int
    type_produit: str
    profil_client: str
    salaire_net: float
    nb_enfants: int
    mensualites_en_cours: float

    MIN_MONTANT = 5_000.0
    MAX_MONTANT = 300_000.0
    MIN_DUREE = 12
    MAX_DUREE = 84
    TAUX_ANNUELS = {"CONSO": 8.9, "AUTO": 7.5}
    PROFILS_CLIENT = {"FONCTIONNAIRE", "SALARIE_PRIVE", "RETRAITE"}

    def _validate(self) -> None:
        if not self.MIN_MONTANT <= self.montant <= self.MAX_MONTANT:
            raise ValueError("Le montant doit être compris entre 5 000 et 300 000 DH.")
        if not self.MIN_DUREE <= self.duree_mois <= self.MAX_DUREE:
            raise ValueError("La durée doit être comprise entre 12 et 84 mois.")
        if self.type_produit not in self.TAUX_ANNUELS:
            raise ValueError("Le type de produit est invalide.")
        if self.profil_client not in self.PROFILS_CLIENT:
            raise ValueError("Le profil client est invalide.")
        if self.salaire_net < 0 or self.mensualites_en_cours < 0 or self.nb_enfants < 0:
            raise ValueError("Les revenus, charges et enfants ne peuvent pas être négatifs.")

    def simulate(self) -> CreditSimulationResult:
        """Calcule la mensualité, le coût total et la décision de principe."""
        self._validate()
        taux_base = self.TAUX_ANNUELS[self.type_produit]
        reduction_convention = 1.5 if self.profil_client == "FONCTIONNAIRE" else 0.0
        taux_annuel = taux_base - reduction_convention
        taux_mensuel = (taux_annuel / 100) / 12
        mensualite_hors_assurance = self.montant * (
            taux_mensuel / (1 - pow(1 + taux_mensuel, -self.duree_mois))
        )
        assurance_mensuelle = (self.montant * 0.0035) / 12
        frais_dossier = min(self.montant * 0.012, 1500.0)
        mensualite_totale = mensualite_hors_assurance + assurance_mensuelle
        cout_total_credit = mensualite_totale * self.duree_mois + frais_dossier
        if self.profil_client == "FONCTIONNAIRE":
            quotite = calculate_cmr_quotite(
                self.salaire_net,
                self.nb_enfants,
                self.mensualites_en_cours,
            )
            quotite_max = quotite["quotite_max"]
            regle_quotite = "Barème CMR / quotité cessible fonctionnaire"
        else:
            # Règle de gestion appliquée aux profils privés et retraités.
            quotite_max = max(0.0, (self.salaire_net * 0.40) - self.mensualites_en_cours)
            regle_quotite = "Règle interne : 40 % du salaire net"
        eligible = mensualite_totale <= quotite_max
        status_code = "ACCORD_PRINCIPE" if eligible else "REFUS_DÉPASSEMENT_CAPACITÉ"
        message = (
            "Accord de principe : la mensualité respecte la quotité cessible."
            if eligible
            else "Refus : la mensualité dépasse la capacité de remboursement disponible."
        )
        return {
            "mensualite_totale": round(mensualite_totale, 2),
            "mensualite_hors_assurance": round(mensualite_hors_assurance, 2),
            "assurance_mensuelle": round(assurance_mensuelle, 2),
            "frais_dossier": round(frais_dossier, 2),
            "cout_total_credit": round(cout_total_credit, 2),
            "taux_applique": taux_annuel,
            "taux_base": taux_base,
            "reduction_convention": reduction_convention,
            "quotite_max_client": round(quotite_max, 2),
            "regle_quotite": regle_quotite,
            "eligible": eligible,
            "status_code": status_code,
            "message_decision": message,
        }
