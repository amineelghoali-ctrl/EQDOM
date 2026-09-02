#!/usr/bin/env python
"""Utilitaire d'administration Django pour le projet EQDOM."""

import os
import sys


def main() -> None:
    """Exécute les commandes de gestion Django."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Django est introuvable. Activez l'environnement virtuel et installez "
            "les dépendances avec 'pip install -r requirements.txt'."
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
