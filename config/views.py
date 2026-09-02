"""Vues d'accueil du projet EQDOM."""

from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.csrf import ensure_csrf_cookie
from decimal import Decimal

from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render

from fasttrack.forms import ClientProfileCompletionForm
from fasttrack.models import (
    AuditLog,
    ClientProfile,
    CoreBankingDetails,
    DossierWorkflow,
    WorkflowComment,
)
from fasttrack.permissions import is_responsable


def home(request):
    """Affiche le point d'entrée du Système des Agences EQDOM."""
    return render(request, "home.html")


@login_required
@ensure_csrf_cookie
def dashboard(request):
    """Affiche le dashboard agent alimenté par l'API de diagnostic."""
    # Un diagnostic 360° exige un profil et son prêt Core Banking associé.
    clients = ClientProfile.objects.filter(
        core_banking_details__isnull=False
    ).order_by("cin_number")
    selected_cin = request.GET.get("cin") or clients.values_list("cin_number", flat=True).first()
    return render(
        request,
        "dashboard.html",
        {"clients": clients, "selected_cin": selected_cin},
    )


@login_required
def complete_client_profile(request, cin: str):
    """Permet à l'agent de compléter un profil créé depuis une CIN scannée."""
    client = get_object_or_404(ClientProfile, cin_number=cin.upper())
    details = _initialize_new_client_dossier(client, request.user)
    form = ClientProfileCompletionForm(
        request.POST or None,
        instance=client,
        credit_details=details,
        require_credit=False,
    )
    if request.method == "POST" and form.is_valid():
        form.save()
        _save_credit_request(client, request.user, form.cleaned_data)
        AuditLog.objects.create(
            agent=request.user,
            client_cin=client.cin_number,
            action="CLIENT_PROFILE_COMPLETED",
            status=AuditLog.Status.SUCCESS,
            response_time_ms=0,
        )
        return redirect(f"/dashboard/?cin={client.cin_number}")
    return render(request, "client_profile_completion.html", {"client": client, "form": form})


def _initialize_new_client_dossier(
    client: ClientProfile, agent
) -> CoreBankingDetails:
    """Initialise un dossier visible sans inventer de données financières."""
    DossierWorkflow.objects.get_or_create(
        client=client,
        defaults={
            "current_status": DossierWorkflow.Status.SCAN_COMPLETED,
            "assigned_agent": agent,
            "created_by": agent,
        },
    )
    details, _ = CoreBankingDetails.objects.get_or_create(
        client=client,
        defaults={
            "produit": "Dossier en constitution",
            "mode_prelevement": "À renseigner",
            "etat": "EN_CONSTITUTION",
            "numero_dossier": f"DOS-{client.cin_number}",
            "montant_credit": Decimal("0.00"),
            "montant_finance": Decimal("0.00"),
            "mensualite": Decimal("0.00"),
            "nb_mensualites_total": 0,
            "nb_mensualites_restantes": 0,
            "mt_restant_du": Decimal("0.00"),
            "total_a_regler": Decimal("0.00"),
            "situation": "EN_CONSTITUTION",
        },
    )
    return details


def _save_credit_request(client: ClientProfile, agent, data: dict) -> None:
    """Enregistre la demande de crédit et la soumet au responsable."""
    details = _initialize_new_client_dossier(client, agent)
    amount = data.get("montant_credit")
    # Lors de l'édition d'un ancien dossier, les champs crédit sont
    # facultatifs : ne pas remplacer les données existantes par des vides.
    if amount is None or amount < 5_000:
        return
    duration = data["nb_mensualites_total"]
    details.produit = data["produit"]
    details.mode_prelevement = data["mode_prelevement"]
    details.etat = "EN_ATTENTE_VALIDATION"
    details.montant_credit = amount
    details.montant_finance = amount
    details.mensualite = data["mensualite"]
    details.nb_mensualites_total = duration
    details.nb_mensualites_restantes = duration
    details.mt_restant_du = amount
    details.total_a_regler = Decimal("0.00")
    details.situation = "EN_ATTENTE_VALIDATION"
    details.save()

    workflow, _ = DossierWorkflow.objects.get_or_create(
        client=client,
        defaults={"assigned_agent": agent, "created_by": agent},
    )
    workflow.current_status = DossierWorkflow.Status.PENDING_VALIDATION
    workflow.assigned_agent = agent
    workflow.save(update_fields=["current_status", "assigned_agent", "updated_at"])
    WorkflowComment.objects.create(
        workflow=workflow,
        author=agent,
        content=(
            "Dossier transmis au responsable pour validation : "
            f"{amount} DH sur {duration} mois."
        ),
    )
    AuditLog.objects.create(
        agent=agent,
        client_cin=client.cin_number,
        action="CREDIT_REQUEST_SUBMITTED_FOR_VALIDATION",
        status=AuditLog.Status.SUCCESS,
        response_time_ms=0,
    )


@login_required
def create_client_from_scan(request):
    """Crée le client seulement après validation de la saisie agent."""
    cin = request.POST.get("cin", request.GET.get("cin", "")).strip().upper()
    if not cin:
        return redirect("dashboard")
    existing = ClientProfile.objects.filter(cin_number=cin).first()
    if existing:
        return redirect(f"/dashboard/?cin={existing.cin_number}")

    initial = {
        "nom": request.GET.get("nom", "À compléter"),
        "prenom": request.GET.get("prenom", "À compléter"),
    }
    form = ClientProfileCompletionForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            client = form.save(commit=False)
            client.cin_number = cin
            client.save()
            _initialize_new_client_dossier(client, request.user)
            _save_credit_request(client, request.user, form.cleaned_data)
            AuditLog.objects.create(
                agent=request.user,
                client_cin=client.cin_number,
                action="CLIENT_DOSSIER_CREATED_BY_AGENT",
                status=AuditLog.Status.SUCCESS,
                response_time_ms=0,
            )
        return redirect(f"/dashboard/?cin={client.cin_number}")

    scan_client = {"cin_number": cin, **initial}
    return render(
        request,
        "client_profile_completion.html",
        {"client": scan_client, "form": form, "is_new_client": True},
    )


@login_required
@ensure_csrf_cookie
def credit_simulator(request):
    """Affiche le simulateur de crédit accessible aux agents connectés."""
    return render(request, "credit_simulator_page.html")


@login_required
@ensure_csrf_cookie
def responsable_dashboard(request):
    """Affiche la file de validation réservée au responsable."""
    if not is_responsable(request.user):
        return redirect("responsable-login")
    return render(request, "responsable_dashboard.html")


@ensure_csrf_cookie
def responsable_login(request):
    """Authentifie explicitement un responsable avant accès à sa file."""
    error = ""
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        user = authenticate(request, username=username, password=password)
        if user is None:
            error = "Nom d'utilisateur ou mot de passe incorrect."
        elif not is_responsable(user):
            error = "Ce compte est un compte Agent et ne peut pas accéder à l'espace Responsable."
        else:
            login(request, user)
            return redirect("responsable-dashboard")
    return render(request, "responsable_login.html", {"error": error})


@staff_member_required(login_url="/api-auth/login/")
def administration(request):
    """Affiche les statistiques métier avec le même périmètre que le responsable."""
    workflows = DossierWorkflow.objects.select_related(
        "client", "assigned_agent", "created_by"
    ).order_by("-updated_at")
    context = {
        # Un « dossier suivi » est exactement un workflow : les chiffres de
        # cette page sont ainsi identiques à ceux du responsable.
        "workflows": workflows[:8],
        "workflow_count": workflows.count(),
        "pending_count": workflows.filter(
            current_status=DossierWorkflow.Status.PENDING_VALIDATION
        ).count(),
        "financing_count": workflows.filter(
            current_status=DossierWorkflow.Status.FINANCEMENT
        ).count(),
        "refused_count": workflows.filter(
            current_status=DossierWorkflow.Status.REFUSE
        ).count(),
    }
    return render(request, "administration.html", context)
