"""Extraction locale d'une CIN marocaine avec EasyOCR.

Ce module ne transmet jamais l'image vers une API externe. EasyOCR charge ses
modeles de reconnaissance localement (un telechargement unique peut etre
necessaire lors de sa premiere execution).
"""

import re
import unicodedata
from functools import lru_cache
from io import BytesIO
from typing import TypedDict


class CinIdentity(TypedDict):
    """Informations que le scanner est autorisé à extraire d'une CIN."""

    cin: str
    nom: str
    prenom: str
    name_detected: bool

class OcrConfigurationError(RuntimeError):
    """Leve lorsque les dependances OCR locales ne sont pas disponibles."""


class CinNotDetectedError(RuntimeError):
    """Leve lorsqu'aucune CIN exploitable n'est trouvee dans l'image."""


@lru_cache(maxsize=1)
def _get_reader():
    """Initialise une seule fois le lecteur OCR pour eviter un cout par scan."""
    try:
        import easyocr
    except ImportError as exc:
        raise OcrConfigurationError(
            "EasyOCR n'est pas installe. Activez l'environnement virtuel puis "
            "executez : pip install -r requirements.txt"
        ) from exc
    return easyocr.Reader(["fr", "en"], gpu=False, verbose=False)


def _extract_cin_from_text(text: str) -> str | None:
    """Normalise les confusions OCR usuelles entre O/0 et I/1.

    EasyOCR peut lire les zéros comme des lettres ``O``. La normalisation est
    appliquée uniquement à la partie numérique, après un préfixe de 1 à 4
    lettres : le préfixe d'une CIN n'est donc jamais modifié.
    """
    direct_matches = re.findall(r"\b[A-Z]{1,4}\s*-?\s*\d{5,8}\b", text)
    if direct_matches:
        # Le numéro de la CIN apparaît généralement dans la zone basse de la
        # carte. Le dernier candidat évite de retenir une date mal lue comme
        # « Y997204 » avant le vrai numéro.
        return re.sub(r"[^A-Z0-9]", "", direct_matches[-1])

    translation = str.maketrans({"O": "0", "I": "1", "L": "1"})
    for token in re.findall(r"\b[A-Z0-9]{6,12}\b", text):
        for prefix_length in range(1, min(4, len(token) - 5) + 1):
            prefix = token[:prefix_length]
            suffix = token[prefix_length:]
            if prefix.isalpha() and re.fullmatch(r"[0-9OIL]{5,8}", suffix):
                return prefix + suffix.translate(translation)
    return None


def _extract_name_from_text(text: str) -> tuple[str, str] | None:
    """Extrait prudemment le nom/prénom lorsqu'ils sont explicitement libellés.

    Ne pas deviner un nom à partir de mots isolés : une mauvaise identité est
    pire qu'un champ à compléter. Les images de test peuvent contenir
    ``Nom : GHOUALI`` et ``Prénom : Amine`` sur des lignes séparées.
    """
    # EasyOCR peut omettre les accents. On retire donc les diacritiques avant
    # de reconnaître les libellés français (NOM / PRENOM).
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    normalized = " ".join(ascii_text.replace("\n", " ").split()).upper()
    # Certaines images sont composées d'une seule ligne, p. ex.
    # « NOM PRENOM : GHOUALI AMINE ». Cette variante reste déterministe.
    combined = re.search(
        r"\b(?:NOM\s*(?:ET|&)?\s*PRENOM|NOMPRENOM)\s*[:\-]?\s*([A-Z' -]{3,80})",
        normalized,
    )
    if combined:
        parts = combined.group(1).strip().split()
        if len(parts) >= 2:
            return " ".join(parts[:-1]).title(), parts[-1].title()

    separator = r"(?=\s+(?:NOM|PRENOM|DATE|NEE?|N[O0]|CIN|NATIONALITE|SEXE)\b|$)"
    nom_match = re.search(rf"\bNOM\s*[:\-]?\s*([A-Z' -]{{2,60}}?){separator}", normalized)
    prenom_match = re.search(rf"\bPRENOM\s*[:\-]?\s*([A-Z' -]{{2,60}}?){separator}", normalized)
    if nom_match and prenom_match:
        return nom_match.group(1).strip().title(), prenom_match.group(1).strip().title()

    return None


def _extract_name_from_lines(lines: list[str]) -> tuple[str, str] | None:
    """Déduit nom/prénom des lignes latines d'une CIN marocaine.

    Les CIN comportent souvent les valeurs sans libellés français. On accepte
    uniquement des lignes alphabétiques et on écarte les en-têtes, villes et
    mots administratifs. Cette règle est utile sur les images importées et les
    spécimens tout en évitant de créer des données aléatoires.
    """
    ignored_words = {
        "ROYAUME DU MAROC", "CARTE NATIONALE D'IDENTITE", "CARTE NATIONALE",
        "IDENTITE", "NATIONALITE", "MAROC", "SPECIMEN", "BPECIMEN",
        "CASABLANCA", "RABAT", "FES", "MARRAKECH", "TANGER", "AGADIR",
        "VALABLE JUSQUAU", "NE LE", "NEE LE", "DATE", "SEXE",
    }
    candidates: list[tuple[str, bool]] = []
    for line in lines:
        normalized = unicodedata.normalize("NFKD", line).encode("ascii", "ignore").decode()
        normalized = " ".join(normalized.upper().split())
        if (
            len(normalized) < 2
            or normalized in ignored_words
            or any(word in normalized for word in ("CARTE", "ROYAUME", "IDENTITE", "VALABLE", "SPECIMEN"))
            or not re.fullmatch(r"[A-Z][A-Z' -]{1,45}", normalized)
        ):
            continue
        # Les noms latins sont normalement reconnus en majuscules sur la CIN.
        # Une pseudo-ligne arabe mal translittérée (souvent en minuscules) est
        # donc ignorée au profit du prénom latin réellement lisible.
        candidates.append((normalized, line.strip() == line.strip().upper()))

    for index, (candidate, _) in enumerate(candidates):
        # Un nom marocain peut être composé (EL FASSI, BEN SALEM) ; le prénom
        # est en général la ligne latine immédiatement suivante.
        if " " in candidate:
            for following, uppercase_source in candidates[index + 1:index + 4]:
                if uppercase_source and len(following.split()) <= 2:
                    return candidate.title(), following.title()
    return None


def extract_moroccan_cin_identity(
    image_bytes: bytes,
    expected_cin: str | None = None,
) -> CinIdentity:
    """Lit localement la CIN, le nom et le prénom, sans générer de données.

    ``expected_cin`` est utilisé uniquement pour le parcours où l'agent a
    d'abord saisi une CIN. Cela permet de continuer si le numéro est lisible
    mais le texte du nom ne l'est pas.
    """
    try:
        import numpy as np
        from PIL import Image

        image = Image.open(BytesIO(image_bytes)).convert("RGB")
    except ImportError as exc:
        raise OcrConfigurationError(
            "Les dependances d'EasyOCR sont absentes. Executez : "
            "pip install -r requirements.txt"
        ) from exc
    except (OSError, ValueError) as exc:
        raise CinNotDetectedError("Le fichier fourni n'est pas une image lisible.") from exc

    try:
        lines = _get_reader().readtext(np.array(image), detail=0)
        text = "\n".join(lines).upper()
    except OcrConfigurationError:
        raise
    except Exception as exc:
        raise CinNotDetectedError("Impossible de lire le texte de cette image CIN.") from exc

    detected_cin = _extract_cin_from_text(text)
    # Dans le parcours « recherche puis scan », la CIN a déjà été confirmée
    # par l'agent : elle reste prioritaire car l'image peut contenir d'autres
    # numéros (date, numéro de spécimen…) ressemblant à une CIN.
    cin = (expected_cin or "").strip().upper() or detected_cin or ""
    if not cin:
        raise CinNotDetectedError(
            "Aucune CIN marocaine lisible n'a ete detectee dans l'image."
        )
    identity = _extract_name_from_text(text) or _extract_name_from_lines(lines)
    if identity is None:
        # Les valeurs explicites indiquent à l'agent qu'il doit les compléter,
        # sans jamais fabriquer de nom ou de prénom aléatoire.
        nom, prenom, name_detected = "À compléter", "À compléter", False
    else:
        nom, prenom = identity
        name_detected = True
    return {"cin": cin, "nom": nom, "prenom": prenom, "name_detected": name_detected}


def extract_moroccan_cin(image_bytes: bytes) -> str:
    """Compatibilité : retourne uniquement le numéro de CIN détecté."""
    return extract_moroccan_cin_identity(image_bytes)["cin"]
