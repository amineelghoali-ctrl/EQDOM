from django.db import models

from fasttrack.models import ClientProfile

from .utils import apply_confidential_watermark


class ClientDocument(models.Model):
    class DocumentType(models.TextChoices):
        CIN = "CIN", "CIN"
        FICHE_PAIE = "FICHE_PAIE", "Fiche de paie"
        ATTESTATION_TRAVAIL = "ATTESTATION_TRAVAIL", "Attestation de travail"
        RELEVE_BANQUE = "RELEVE_BANQUE", "Relevé bancaire"
        JUSTIFICATIF_DOMICILE = "JUSTIFICATIF_DOMICILE", "Justificatif de domicile"

    class Status(models.TextChoices):
        CONFORME = "CONFORME", "Conforme"
        EXPIRE = "EXPIRE", "Expiré"
        MANQUANT = "MANQUANT", "Manquant"

    client = models.ForeignKey(ClientProfile, on_delete=models.CASCADE, related_name="ged_documents")
    document_type = models.CharField(max_length=32, choices=DocumentType.choices)
    file = models.FileField(upload_to="client_documents/%Y/%m/")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.MANQUANT)
    # Résultat d'analyse local d'une fiche de paie. Ces champs restent vides
    # pour les autres documents et n'altèrent pas la GED existante.
    ocr_text = models.TextField(blank=True)
    extracted_monthly_income = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    ocr_status = models.CharField(max_length=20, default="NOT_APPLICABLE")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at"]
        constraints = [models.UniqueConstraint(fields=["client", "document_type"], name="unique_client_document_type")]

    def save(self, *args, **kwargs):
        if self.file and self._state.adding:
            self.file = apply_confidential_watermark(self.file)
        super().save(*args, **kwargs)


class ClientContractSignature(models.Model):
    """Signature électronique et contrat PDF associé."""

    client = models.OneToOneField(
        ClientProfile, on_delete=models.CASCADE, related_name="contract_signature"
    )
    signed_by = models.ForeignKey(
        "auth.User", on_delete=models.PROTECT, related_name="signed_client_contracts"
    )
    signature_image = models.ImageField(upload_to="contract_signatures/%Y/%m/")
    contract_pdf = models.FileField(upload_to="client_contracts/%Y/%m/")
    signed_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "signature de contrat"
        verbose_name_plural = "signatures de contrats"
