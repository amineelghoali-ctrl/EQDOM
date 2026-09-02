from django.apps import AppConfig


class FastTrackConfig(AppConfig):
    """Configuration de l'application Fast-Track."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "fasttrack"

    def ready(self) -> None:
        """Charge les signaux après l'initialisation des modèles Django."""
        from . import signals  # noqa: F401
