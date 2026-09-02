"""Modèles de données pour le parcours Fast-Track."""

from django.conf import settings
from django.db import models


class UserProfile(models.Model):
    """Rôle métier Fast-Track, indépendant des droits techniques Django."""

    class Role(models.TextChoices):
        AGENT = "AGENT", "Agent"
        RESPONSABLE = "RESPONSABLE", "Responsable"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.AGENT)

    class Meta:
        verbose_name = "profil utilisateur"
        verbose_name_plural = "profils utilisateurs"

    def __str__(self) -> str:
        return f"{self.user.get_username()} - {self.get_role_display()}"


class ClientProfile(models.Model):
    """Profil client créé à partir du scan CIN simulé."""

    cin_number = models.CharField(max_length=20, unique=True, db_index=True)
    nom = models.CharField(max_length=100)
    prenom = models.CharField(max_length=100)
    # Le téléphone est saisi par l'agent après le scan CIN ; il ne doit donc
    # pas bloquer l'enregistrement d'un dossier nouvellement scanné.
    telephone = models.CharField(max_length=30, blank=True)
    autres_telephones = models.CharField(max_length=100, blank=True)
    ville = models.CharField(max_length=100, blank=True)
    adresse = models.CharField(max_length=255, blank=True)
    date_naissance = models.DateField(null=True, blank=True)
    employeur = models.CharField(max_length=150, blank=True)
    drpp_number = models.CharField(max_length=30, blank=True)
    cnss_number = models.CharField(max_length=30, blank=True)
    cmr_number = models.CharField(max_length=30, blank=True)
    total_engagement = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    liveness_verified = models.BooleanField(default=False)
    face_match_score = models.FloatField(default=0.0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "profil client"
        verbose_name_plural = "profils clients"

    def __str__(self) -> str:
        return f"{self.prenom} {self.nom} ({self.cin_number})"


class CoreBankingDetails(models.Model):
    """Instantané des informations retournées par le Core Banking."""

    client = models.OneToOneField(
        ClientProfile,
        on_delete=models.CASCADE,
        related_name="core_banking_details",
    )
    produit = models.CharField(max_length=100)
    mode_prelevement = models.CharField(max_length=100)
    etat = models.CharField(max_length=50, default="ACTIF")
    provenance = models.CharField(max_length=100, blank=True)
    numero_dossier = models.CharField(max_length=30, unique=True, null=True, blank=True)
    revendeur = models.CharField(max_length=150, blank=True)
    montant_credit = models.DecimalField(max_digits=12, decimal_places=2)
    montant_precompte = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    montant_finance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    mensualite = models.DecimalField(max_digits=12, decimal_places=2)
    code_dit = models.CharField(max_length=30, blank=True)
    nb_mensualites_total = models.PositiveIntegerField()
    nb_mensualites_restantes = models.PositiveIntegerField()
    date_acceptation = models.DateField(null=True, blank=True)
    date_financement = models.DateField(null=True, blank=True)
    date_premiere_echeance = models.DateField(null=True, blank=True)
    date_derniere_echeance = models.DateField(null=True, blank=True)
    banque = models.CharField(max_length=100, blank=True)
    total_traite = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    nbr_impayes = models.PositiveIntegerField(default=0)
    age_impayes_jours = models.PositiveIntegerField(default=0)
    total_impaye = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    penalite_retard = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    int_retard_ttc = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    frais_justice = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    nbr_reports = models.PositiveIntegerField(default=0)
    honoraires_avocat = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    frais_report = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    montant_compense = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    montant_solde_provision = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    mt_restant_du = models.DecimalField(max_digits=12, decimal_places=2)
    total_a_regler = models.DecimalField(max_digits=12, decimal_places=2)
    date_dernier_reglement = models.DateField(null=True, blank=True)
    situation = models.CharField(max_length=100, default="NORMAL")
    date_situation = models.DateField(null=True, blank=True)
    restructuration = models.BooleanField(default=False)

    class Meta:
        verbose_name = "détail Core Banking"
        verbose_name_plural = "détails Core Banking"

    def __str__(self) -> str:
        return f"{self.client.cin_number} - {self.produit}"


class DossierWorkflow(models.Model):
    """État de traitement collaboratif d'un dossier client."""

    class Status(models.TextChoices):
        SCAN_COMPLETED = "SCAN_COMPLETED", "Scan terminé"
        PENDING_DOCS = "PENDING_DOCS", "Documents en attente"
        PRE_APPROVED = "PRE_APPROVED", "Pré-accord"
        PENDING_VALIDATION = "PENDING_VALIDATION", "En attente de validation"
        FINANCEMENT = "FINANCEMENT", "Financement"
        REFUSE = "REFUSE", "Refusé"

    client = models.OneToOneField(
        ClientProfile,
        on_delete=models.CASCADE,
        related_name="workflow",
    )
    current_status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.SCAN_COMPLETED,
    )
    assigned_agent = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="assigned_workflows",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_workflows",
        help_text="Agent ayant créé le dossier dans Fast-Track.",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        verbose_name = "workflow dossier"
        verbose_name_plural = "workflows dossiers"

    def __str__(self) -> str:
        return f"{self.client.cin_number} - {self.get_current_status_display()}"


class WorkflowComment(models.Model):
    """Note ou réponse interne laissée par un agent sur un workflow."""

    workflow = models.ForeignKey(
        DossierWorkflow,
        on_delete=models.CASCADE,
        related_name="comments",
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="workflow_comments",
    )
    content = models.TextField()
    parent_comment = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="replies",
    )
    likes = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name="liked_workflow_comments",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        verbose_name = "commentaire workflow"
        verbose_name_plural = "commentaires workflow"

    def __str__(self) -> str:
        return f"{self.author} - {self.content[:50]}"


class AuditLog(models.Model):
    """Trace les actions sensibles effectuées par les agents."""

    class Status(models.TextChoices):
        SUCCESS = "SUCCESS", "Succès"
        FAILURE = "FAILURE", "Échec"
        PENDING = "PENDING", "En cours"

    agent = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="fasttrack_audit_logs",
    )
    client_cin = models.CharField(max_length=20, db_index=True)
    action = models.CharField(max_length=100)
    status = models.CharField(max_length=20, choices=Status.choices)
    response_time_ms = models.PositiveIntegerField(default=0)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-timestamp"]
        indexes = [models.Index(fields=["client_cin", "timestamp"])]

    def __str__(self) -> str:
        return f"{self.action} - {self.client_cin} ({self.status})"
