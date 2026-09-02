"""Automatisations liées aux dossiers Fast-Track."""

from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import UserProfile

# Les informations Core Banking ne doivent jamais être générées lors d'un
# scan ou d'une saisie agent. Les seules données de démonstration sont créées
# explicitement par ``seed_mock_data`` pour les clients MOCK.


@receiver(post_save, sender=get_user_model())
def create_user_profile(sender, instance, created: bool, **kwargs: object) -> None:
    """Crée le profil de rôle métier pour chaque nouvel utilisateur."""
    if created:
        UserProfile.objects.get_or_create(user=instance)
