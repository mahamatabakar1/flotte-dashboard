import json
from datetime import datetime
from pathlib import Path

import requests

from auth import TokenManager

API_URL = "https://opensky-network.org/api/states/all"

# Boite englobante approximative du Quebec
QUEBEC = {
    "lamin": 45.0,
    "lamax": 62.0,
    "lomin": -80.0,
    "lomax": -57.0,
}

DOSSIER_BRUT = Path(__file__).resolve().parent.parent / "data" / "brut"


def extraire_etats():
    tm = TokenManager()
    entetes = {"Authorization": f"Bearer {tm.get_token()}"}
    reponse = requests.get(API_URL, headers=entetes, params=QUEBEC, timeout=60)
    reponse.raise_for_status()
    return reponse.json()


def sauvegarder(donnees):
    DOSSIER_BRUT.mkdir(parents=True, exist_ok=True)
    horodatage = datetime.now().strftime("%Y%m%d_%H%M%S")
    chemin = DOSSIER_BRUT / f"etats_{horodatage}.json"
    with open(chemin, "w") as fichier:
        json.dump(donnees, fichier)
    return chemin


if __name__ == "__main__":
    donnees = extraire_etats()
    etats = donnees.get("states") or []
    print(f"Avions detectes au-dessus du Quebec : {len(etats)}")
    for etat in etats[:5]:
        icao24 = etat[0]
        indicatif = (etat[1] or "").strip() or "(inconnu)"
        pays = etat[2]
        altitude = etat[7]
        print(f"  {icao24}  {indicatif:10s}  {pays:20s}  altitude: {altitude}")
    chemin = sauvegarder(donnees)
    print(f"Donnees brutes enregistrees dans : {chemin}")
