"""Sérialise les objets exposés par l'API Fast-Track."""

from rest_framework import serializers

from .models import ClientProfile, CoreBankingDetails, DossierWorkflow, WorkflowComment


class ScanCINSerializer(serializers.Serializer):
    """Valide le fichier image soumis par l'agent."""

    image = serializers.ImageField(required=True, write_only=True)
    cin_number = serializers.CharField(required=False, max_length=20, trim_whitespace=True)

    def validate_image(self, image):
        max_size = 5 * 1024 * 1024
        if image.size > max_size:
            raise serializers.ValidationError("L'image ne doit pas dépasser 5 Mo.")
        return image


class CreditSimulationSerializer(serializers.Serializer):
    """Valide les paramètres de la simulation de crédit."""

    montant = serializers.FloatField(min_value=5_000, max_value=300_000)
    duree_mois = serializers.IntegerField(min_value=12, max_value=84)
    type_produit = serializers.ChoiceField(choices=["CONSO", "AUTO"])
    profil_client = serializers.ChoiceField(
        choices=["FONCTIONNAIRE", "SALARIE_PRIVE", "RETRAITE"]
    )
    salaire_net = serializers.FloatField(min_value=0)
    nb_enfants = serializers.IntegerField(min_value=0)
    mensualites_en_cours = serializers.FloatField(min_value=0)


class WorkflowStatusSerializer(serializers.Serializer):
    """Valide le changement d'état d'un dossier."""

    current_status = serializers.ChoiceField(choices=DossierWorkflow.Status.choices)


class WorkflowAssignmentSerializer(serializers.Serializer):
    """Valide le transfert d'un dossier vers un autre agent."""

    agent_id = serializers.IntegerField(min_value=1)


class ResponsableDecisionSerializer(serializers.Serializer):
    """Valide la décision prise par le responsable."""

    action = serializers.ChoiceField(choices=["APPROVE", "REJECT"])
    motif_refus = serializers.CharField(required=False, allow_blank=True, max_length=3_000)

    def validate(self, attrs: dict) -> dict:
        if attrs["action"] == "REJECT" and not attrs.get("motif_refus", "").strip():
            raise serializers.ValidationError(
                {"motif_refus": "Le motif du refus est obligatoire."}
            )
        return attrs


class WorkflowCommentCreateSerializer(serializers.Serializer):
    """Valide une note interne ou une réponse."""

    content = serializers.CharField(max_length=3_000, trim_whitespace=True)


class WorkflowCommentSerializer(serializers.ModelSerializer):
    """Sérialise le fil de discussion de manière récursive."""

    author_name = serializers.CharField(source="author.get_username", read_only=True)
    likes_count = serializers.IntegerField(source="likes.count", read_only=True)
    liked_by_current_user = serializers.SerializerMethodField()
    replies = serializers.SerializerMethodField()

    class Meta:
        model = WorkflowComment
        fields = (
            "id", "author_name", "content", "created_at", "likes_count",
            "liked_by_current_user", "replies",
        )

    def get_liked_by_current_user(self, obj: WorkflowComment) -> bool:
        request = self.context.get("request")
        return bool(request and request.user.is_authenticated and obj.likes.filter(pk=request.user.pk).exists())

    def get_replies(self, obj: WorkflowComment) -> list[dict]:
        replies = obj.replies.select_related("author").prefetch_related("likes").all()
        return WorkflowCommentSerializer(replies, many=True, context=self.context).data


class DossierWorkflowSerializer(serializers.ModelSerializer):
    """Expose le statut, l'assignation et les notes de premier niveau."""

    assigned_agent_name = serializers.CharField(source="assigned_agent.get_username", read_only=True)
    assigned_agent_id = serializers.IntegerField(read_only=True)
    created_by_name = serializers.CharField(source="created_by.get_username", read_only=True)
    status_label = serializers.CharField(source="get_current_status_display", read_only=True)
    comments = serializers.SerializerMethodField()

    class Meta:
        model = DossierWorkflow
        fields = (
            "current_status", "status_label", "assigned_agent_id", "assigned_agent_name",
            "created_by_name", "updated_at", "comments",
        )

    def get_comments(self, obj: DossierWorkflow) -> list[dict]:
        comments = obj.comments.filter(parent_comment__isnull=True).select_related("author").prefetch_related("likes")
        return WorkflowCommentSerializer(comments, many=True, context=self.context).data


class ResponsableDossierSerializer(serializers.ModelSerializer):
    """Synthèse d'un dossier affichée dans la file du responsable."""

    cin_number = serializers.CharField(source="client.cin_number", read_only=True)
    client_name = serializers.SerializerMethodField()
    assigned_agent_name = serializers.CharField(source="assigned_agent.get_username", read_only=True)
    created_by_name = serializers.CharField(source="created_by.get_username", read_only=True)
    status_label = serializers.CharField(source="get_current_status_display", read_only=True)
    comments_count = serializers.IntegerField(source="comments.count", read_only=True)

    class Meta:
        model = DossierWorkflow
        fields = (
            "id", "cin_number", "client_name", "current_status", "status_label",
            "assigned_agent_name", "created_by_name", "updated_at", "comments_count",
        )

    def get_client_name(self, obj: DossierWorkflow) -> str:
        return f"{obj.client.prenom} {obj.client.nom}"


class CoreBankingDetailsSerializer(serializers.ModelSerializer):
    class Meta:
        model = CoreBankingDetails
        fields = (
            "produit", "mode_prelevement", "etat", "provenance", "numero_dossier",
            "revendeur", "montant_credit", "montant_precompte", "montant_finance",
            "mensualite", "code_dit", "nb_mensualites_total",
            "nb_mensualites_restantes", "date_acceptation", "date_financement",
            "date_premiere_echeance", "date_derniere_echeance", "banque", "total_traite",
            "nbr_impayes", "age_impayes_jours", "total_impaye", "penalite_retard",
            "int_retard_ttc", "frais_justice", "nbr_reports", "honoraires_avocat",
            "frais_report", "montant_compense", "montant_solde_provision", "mt_restant_du",
            "total_a_regler", "date_dernier_reglement", "situation", "date_situation",
            "restructuration",
        )


class ClientProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClientProfile
        fields = (
            "cin_number", "nom", "prenom", "telephone", "autres_telephones", "ville", "adresse",
            "date_naissance", "employeur", "drpp_number", "cnss_number", "cmr_number",
            "total_engagement", "liveness_verified", "face_match_score", "created_at",
        )
