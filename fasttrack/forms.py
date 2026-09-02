"""Formulaires métier de l'espace agent."""

from django import forms

from .models import ClientProfile


class ClientProfileCompletionForm(forms.ModelForm):
    """Complète un profil créé minimalement depuis une image de CIN."""

    produit = forms.CharField(max_length=100, label="Produit de crédit")
    montant_credit = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        label="Montant du crédit demandé (DH)",
    )
    mensualite = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=0,
        label="Mensualité proposée (DH)",
    )
    nb_mensualites_total = forms.IntegerField(
        max_value=120,
        label="Durée du crédit (mois)",
    )
    mode_prelevement = forms.ChoiceField(
        choices=(
            ("Prélèvement bancaire", "Prélèvement bancaire"),
            ("Virement", "Virement"),
            ("Retenue à la source", "Retenue à la source"),
            ("À renseigner", "À renseigner"),
        ),
        label="Mode de prélèvement",
    )

    class Meta:
        model = ClientProfile
        fields = (
            "nom",
            "prenom",
            "telephone",
            "autres_telephones",
            "date_naissance",
            "ville",
            "adresse",
            "employeur",
            "drpp_number",
            "cnss_number",
            "cmr_number",
            "total_engagement",
        )
        widgets = {
            "date_naissance": forms.DateInput(attrs={"type": "date"}),
            "adresse": forms.Textarea(attrs={"rows": 3}),
            "total_engagement": forms.NumberInput(attrs={"min": 0, "step": "0.01"}),
        }

    def __init__(self, *args, credit_details=None, require_credit: bool = True, **kwargs):
        super().__init__(*args, **kwargs)
        self.require_credit = require_credit
        # L'agent peut sauvegarder progressivement puis compléter le contact
        # au guichet, sans perdre l'identité extraite par l'OCR.
        self.fields["telephone"].required = False
        if credit_details is not None:
            self.fields["produit"].initial = credit_details.produit
            self.fields["montant_credit"].initial = credit_details.montant_credit
            self.fields["mensualite"].initial = credit_details.mensualite
            self.fields["nb_mensualites_total"].initial = credit_details.nb_mensualites_total
            self.fields["mode_prelevement"].initial = credit_details.mode_prelevement
        if not require_credit:
            for name in (
                "produit", "montant_credit", "mensualite",
                "nb_mensualites_total", "mode_prelevement",
            ):
                self.fields[name].required = False

    def clean(self):
        cleaned_data = super().clean()
        if not self.require_credit:
            return cleaned_data
        amount = cleaned_data.get("montant_credit")
        duration = cleaned_data.get("nb_mensualites_total")
        if amount is not None and amount < 5_000:
            self.add_error("montant_credit", "Le montant minimum est de 5 000 DH.")
        if duration is not None and duration < 1:
            self.add_error("nb_mensualites_total", "La durée doit être d'au moins un mois.")
        return cleaned_data
