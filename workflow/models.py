from django.conf import settings
from django.db import models

from fasttrack.models import DossierWorkflow


class OverrideRequest(models.Model):
    """Demande de dérogation distincte du workflow de dossier existant."""

    workflow = models.ForeignKey(DossierWorkflow, on_delete=models.CASCADE, related_name="override_requests")
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="requested_overrides")
    reason = models.TextField()
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="approved_overrides"
    )
    is_approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Dérogation {self.workflow.client.cin_number}"
