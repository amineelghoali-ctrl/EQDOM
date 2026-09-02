"""Géocodage localisé et attribution d'agence, sans modèle persistant."""

from __future__ import annotations

import json
from functools import lru_cache
from math import asin, cos, radians, sin, sqrt
from typing import TypedDict
from urllib.parse import quote
from urllib.request import Request, urlopen


CASABLANCA_COORDINATES = {"latitude": 33.5731, "longitude": -7.5898}
NOMINATIM_USER_AGENT = "EQDOMFastTrack/1.0"


class Agency(TypedDict):
    name: str
    city: str
    latitude: float
    longitude: float


EQDOM_AGENCIES: tuple[Agency, ...] = (
    {"name": "Agence EQDOM Casablanca Anfa", "city": "Casablanca", "latitude": 33.5884, "longitude": -7.6480},
    {"name": "Agence EQDOM Rabat Agdal", "city": "Rabat", "latitude": 34.0027, "longitude": -6.8490},
    {"name": "Agence EQDOM Fès Chefchaouen", "city": "Fès", "latitude": 34.0372, "longitude": -4.9998},
    {"name": "Agence EQDOM Marrakech Guéliz", "city": "Marrakech", "latitude": 31.6349, "longitude": -8.0106},
    {"name": "Agence EQDOM Tanger Centre", "city": "Tanger", "latitude": 35.7730, "longitude": -5.8031},
)

def default_coordinates() -> dict[str, float]:
    """Retourne Casablanca si le service externe est indisponible."""
    return CASABLANCA_COORDINATES.copy()


@lru_cache(maxsize=64)
def get_client_coordinates(ville: str) -> dict[str, float | str]:
    """Géocode une ville marocaine via Nominatim, avec repli Casablanca."""
    city = ville.strip() or "Casablanca"
    url = (
        "https://nominatim.openstreetmap.org/search?"
        f"q={quote(f'{city}, Morocco')}&format=json&limit=1"
    )
    try:
        request = Request(url, headers={"User-Agent": NOMINATIM_USER_AGENT})
        with urlopen(request, timeout=2.5) as response:  # nosec B310 - URL contrôlée
            payload = json.loads(response.read().decode("utf-8"))
        if payload:
            return {
                "latitude": float(payload[0]["lat"]),
                "longitude": float(payload[0]["lon"]),
                "source": "nominatim",
            }
    except (OSError, ValueError, KeyError, IndexError, json.JSONDecodeError):
        pass
    return {**default_coordinates(), "source": "casablanca_fallback"}


def haversine_distance_km(
    latitude_a: float, longitude_a: float, latitude_b: float, longitude_b: float
) -> float:
    """Calcule la distance à vol d'oiseau entre deux coordonnées."""
    earth_radius_km = 6371.0
    latitude_delta = radians(latitude_b - latitude_a)
    longitude_delta = radians(longitude_b - longitude_a)
    calculation = sin(latitude_delta / 2) ** 2 + cos(radians(latitude_a)) * cos(
        radians(latitude_b)
    ) * sin(longitude_delta / 2) ** 2
    return earth_radius_km * 2 * asin(sqrt(calculation))


def get_nearest_agency(latitude: float, longitude: float) -> dict[str, float | str]:
    """Sélectionne l'agence fictive EQDOM la plus proche."""
    agency = min(
        EQDOM_AGENCIES,
        key=lambda item: haversine_distance_km(
            latitude, longitude, item["latitude"], item["longitude"]
        ),
    )
    distance = haversine_distance_km(
        latitude, longitude, agency["latitude"], agency["longitude"]
    )
    return {**agency, "distance_km": round(distance, 1)}


def get_reference_client_city(cin_number: str) -> str:
    """Retourne une localisation de repli sans altérer le dossier client."""
    del cin_number
    return "Casablanca"
