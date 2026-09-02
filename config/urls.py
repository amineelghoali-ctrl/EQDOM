"""Routes HTTP principales du projet EQDOM."""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

from .views import (
    administration,
    complete_client_profile,
    create_client_from_scan,
    credit_simulator,
    dashboard,
    home,
    responsable_dashboard,
    responsable_login,
)

urlpatterns = [
    path("", home, name="home"),
    path("dashboard/", dashboard, name="dashboard"),
    path("dossiers/nouveau/", create_client_from_scan, name="create-client-from-scan"),
    path("dossiers/<str:cin>/complete/", complete_client_profile, name="complete-client-profile"),
    path("credit-simulator/", credit_simulator, name="credit-simulator"),
    path("responsable/login/", responsable_login, name="responsable-login"),
    path("responsable/dashboard/", responsable_dashboard, name="responsable-dashboard"),
    path("administration/", administration, name="administration"),
    # Compatibilité avec la destination Django historique après authentification.
    path("accounts/profile/", RedirectView.as_view(pattern_name="dashboard", permanent=False)),
    path("admin/", admin.site.urls),
    path("api-auth/", include("rest_framework.urls")),
    path("api/v1/", include("fasttrack.urls")),
    path("api/v1/", include("audit.urls")),
    path("api/v1/", include("documents.urls")),
    path("api/v1/", include("workflow.urls")),
    path("api/v1/", include("dashboard.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
