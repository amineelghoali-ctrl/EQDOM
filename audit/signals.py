"""Signal applicatif : les vues métier restent découplées de l'audit CNDP."""

from django.dispatch import Signal, receiver

from .models import AuditLog

access_logged = Signal()


@receiver(access_logged)
def persist_access_log(sender, *, user, action, client_cin, **kwargs):
    if user and user.is_authenticated:
        AuditLog.objects.create(user=user, action=action, client_cin=(client_cin or "INCONNU")[:20])
