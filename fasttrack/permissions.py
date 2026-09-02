"""Règles d'autorisation métier Fast-Track."""

from django.core.exceptions import PermissionDenied
from rest_framework.permissions import BasePermission

from .models import UserProfile


def is_responsable(user) -> bool:
    """Indique si l'utilisateur connecté possède le rôle responsable."""
    return bool(
        user
        and user.is_authenticated
        and getattr(getattr(user, "profile", None), "role", None)
        == UserProfile.Role.RESPONSABLE
    )


class IsResponsable(BasePermission):
    """Restreint une API aux responsables Fast-Track."""

    message = "Cette action est réservée au responsable d'agence."

    def has_permission(self, request, view) -> bool:
        return is_responsable(request.user)


def require_responsable(request) -> None:
    """Lève une erreur HTTP 403 pour un utilisateur qui n'est pas responsable."""
    if not is_responsable(request.user):
        raise PermissionDenied("Cet espace est réservé au responsable d'agence.")
