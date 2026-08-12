import json
from pathlib import Path

import pandas as pd

# Les 17 champs d'un state vector OpenSky, dans l'ordre
COLONNES = [
    "icao24", "indicatif", "pays_origine", "derniere_position", "dernier_contact",
    "longitude", "latitude", "altitude_barometrique", "au_sol", "vitesse_sol",
    "cap", "vitesse_verticale", "capteurs", "altitude_geometrique",
    "squawk", "spi", "source_position",
]

DOSSIER_BRUT = Path(__file__).resolve().parent.parent / "data" / "brut"
DOSSIER_TRAITE = Path(__file__).resolve().parent.parent / "data" / "traite"


def dernier_fichier_brut():
    fichiers = sorted(DOSSIER_BRUT.glob("etats_*.json"))
    if not fichiers:
        raise FileNotFoundError("Aucun fichier brut. Lancez d'abord extraction.py")
    return fichiers[-1]


def construire_dataframe(chemin):
    with open(chemin) as fichier:
        donnees = json.load(fichier)

    df = pd.DataFrame(donnees.get("states") or [], columns=COLONNES)

    # Nettoyage
    df["indicatif"] = df["indicatif"].str.strip().replace("", pd.NA)
    df["horodatage"] = pd.to_datetime(donnees["time"], unit="s", utc=True)
    df["icao24"] = df["icao24"].str.lower()

    # Colonnes inutiles pour notre analyse
    df = df.drop(columns=["capteurs", "spi", "squawk"])

    return df


if __name__ == "__main__":
    chemin = dernier_fichier_brut()
    df = construire_dataframe(chemin)

    print(f"Fichier source : {chemin.name}")
    print(f"Lignes : {len(df)}  |  Colonnes : {len(df.columns)}")
    print()
    print("Repartition par pays :")
    print(df["pays_origine"].value_counts().head(5).to_string())
    print()
    print(f"Avions au sol : {int(df['au_sol'].sum())}")
    print(f"Avions en vol : {int((~df['au_sol']).sum())}")
    print()
    print(df[["icao24", "indicatif", "pays_origine", "altitude_barometrique", "au_sol"]].head(10).to_string(index=False))

    DOSSIER_TRAITE.mkdir(parents=True, exist_ok=True)
    sortie = DOSSIER_TRAITE / f"{chemin.stem}.csv"
    df.to_csv(sortie, index=False)
    print(f"\nEnregistre : {sortie}")
