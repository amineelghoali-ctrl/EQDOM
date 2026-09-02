from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    """Trace CNDP indépendante des traces techniques historiques."""

    class Action(models.TextChoices):
        SCAN_CIN = "SCAN_CIN", "Scan CIN"
        SEARCH_CLIENT = "SEARCH_CLIENT", "Recherche client"
        SIMULATION_CREATED = "SIMULATION_CREATED", "Simulation créée"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="cndp_audit_logs"
    )
    action = models.CharField(max_length=32, choices=Action.choices)
    client_cin = models.CharField(max_length=20, db_index=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-timestamp"]
        indexes = [models.Index(fields=["client_cin", "timestamp"])]

    def __str__(self):
        return f"{self.action} · {self.client_cin} · {self.timestamp:%Y-%m-%d %H:%M}"
