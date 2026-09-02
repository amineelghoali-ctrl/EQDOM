"""Configuration du projet Django EQDOM."""

from .celery import app as celery_app

__all__ = ("celery_app",)
