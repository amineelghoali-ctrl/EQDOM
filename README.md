# EQDOM Fast-Track Agence

Projet Django REST Framework de demonstration. Toutes les donnees client sont
fictives ; n'importez aucune donnee client reelle.

## Demarrage local

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py runserver
```

L'interface est disponible sur `http://127.0.0.1:8000/dashboard/` et
l'administration sur `http://127.0.0.1:8000/administration/`.

## Compte de demonstration

| Champ | Valeur |
| --- | --- |
| Utilisateur | `agent_demo` |
| Mot de passe | `EqdomDemo!2026` |

## Circuit responsable

| Rôle | Utilisateur | Mot de passe |
| --- | --- | --- |
| Responsable | `responsable_demo` | `EqdomResponsable!2026` |
| Agent 2 | `agent_demo_2` | `EqdomAgent2!2026` |

Le responsable accède à `/responsable/dashboard/`. Il voit tous les dossiers,
peut les filtrer par agent, commenter le workflow et prendre une décision sur
les dossiers à l'état **En attente de validation**. Une validation passe le
dossier à **Financement** ; un refus exige un motif et est tracé dans le fil.

## Recherche d'une CIN par image : OCR local

Le bouton **CIN par image** utilise **EasyOCR** directement sur la machine
serveur. Aucune cle Google, aucun compte Cloud et aucune transmission de
l'image a un service tiers ne sont necessaires.

EasyOCR est installe avec `pip install -r requirements.txt`. Au premier scan,
il peut telecharger une fois ses modeles de reconnaissance francais/anglais ;
les scans suivants reutilisent ces modeles localement. Une connexion internet
peut donc etre requise uniquement pour ce premier telechargement des modeles.

Le scan extrait la CIN, recherche le dossier et :

- affiche le diagnostic si le client existe ;
- ouvre l'ajout de client avec la CIN pre-remplie sinon.

## Localisation agence et revenus MRE

Le diagnostic client affiche une carte Leaflet/OpenStreetMap et attribue une
agence EQDOM fictive selon la ville mock du dossier. Le géocodage Nominatim
utilise un délai court ; si le service est indisponible, Casablanca est utilisée
automatiquement.

Le simulateur accepte les revenus en MAD, EUR ou USD. Il tente le taux public
Frankfurter, sans clé API. En cas d'indisponibilité, le calcul reste disponible
avec les taux de sécurité suivants : `1 EUR = 10.80 MAD` et `1 USD = 9.90 MAD`.

## Scan asynchrone

Le parcours de creation par scan peut utiliser Redis et Celery. Avec Docker :

```powershell
docker run --name eqdom-redis -p 6379:6379 redis:7-alpine
```

Dans un second terminal :

```powershell
.\.venv\Scripts\Activate.ps1
celery -A config worker -l info
```
