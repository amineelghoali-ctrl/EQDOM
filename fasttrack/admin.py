"""Configuration de l'administration Django Fast-Track."""

from django.contrib import admin

from .models import AuditLog, ClientProfile, CoreBankingDetails, UserProfile

# Désactive le menu technique de Django Admin sur tous les écrans métier.
admin.site.enable_nav_sidebar = False


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    """Gestion des rôles métier Agent et Responsable."""

    list_display = ("user", "role")
    list_filter = ("role",)
    search_fields = ("user__username",)


@admin.register(ClientProfile)
class ClientProfileAdmin(admin.ModelAdmin):
    """Administration des profils clients."""

    list_display = ("cin_number", "nom", "prenom", "telephone", "ville", "liveness_verified")
    search_fields = ("cin_number", "nom", "prenom", "telephone", "ville", "adresse")
    list_filter = ("liveness_verified", "created_at")

    def get_changeform_initial_data(self, request):
        """Préremplit la CIN lorsque la création provient de l'OCR."""
        initial = super().get_changeform_initial_data(request)
        cin_number = request.GET.get("cin_number", "").strip().upper()
        if cin_number:
            initial["cin_number"] = cin_number
        return initial


@admin.register(CoreBankingDetails)
class CoreBankingDetailsAdmin(admin.ModelAdmin):
    """Administration des détails de prêt simulés."""

    list_display = ("client", "produit", "mensualite", "nbr_impayes", "total_a_regler")
    search_fields = ("client__cin_number", "client__nom", "client__prenom")
    list_filter = ("produit", "mode_prelevement", "nbr_impayes")


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    """Consultation des traces d'activité agent."""

    list_display = ("timestamp", "agent", "client_cin", "action", "status", "response_time_ms")
    search_fields = ("client_cin", "agent__username", "action")
    list_filter = ("status", "action", "timestamp")
    readonly_fields = ("agent", "client_cin", "action", "status", "response_time_ms", "timestamp")
