from .models import AuditLog
from .signals import access_logged


class CNDPAccessAuditMiddleware:
    """Observe les routes sensibles après leur succès, sans modifier leurs vues."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if response.status_code >= 400 or not getattr(request, "user", None) or not request.user.is_authenticated:
            return response
        path = request.path.rstrip("/")
        action, cin = None, ""
        if path.endswith("/agent/scan-cin") or path.endswith("/agent/scan-search"):
            action = AuditLog.Action.SCAN_CIN
            cin = request.POST.get("cin_number", "")
        elif path.endswith("/agent/search-client"):
            action = AuditLog.Action.SEARCH_CLIENT
            cin = request.GET.get("cin", "")
        elif path.endswith("/credit/simulate"):
            if getattr(response, "data", {}).get("eligible"):
                action = AuditLog.Action.SIMULATION_CREATED
                cin = request.GET.get("cin", "")
        elif "/agent/client/" in path and path.endswith("/fast-track-diagnostic"):
            action = AuditLog.Action.SEARCH_CLIENT
            cin = path.split("/agent/client/", 1)[1].split("/", 1)[0]
        if action:
            access_logged.send(sender=self.__class__, user=request.user, action=action, client_cin=cin.upper())
        return response
