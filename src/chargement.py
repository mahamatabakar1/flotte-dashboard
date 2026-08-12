from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text

SERVEUR = "localhost,1433"
UTILISATEUR = "sa"
MOT_DE_PASSE = "Abc12345!"
BASE = "flotte"

PILOTE = "ODBC+Driver+18+for+SQL+Server"
OPTIONS = "TrustServerCertificate=yes&Encrypt=no"

DOSSIER_TRAITE = Path(__file__).resolve().parent.parent / "data" / "traite"


def moteur(base="master"):
    url = (
        f"mssql+pyodbc://{UTILISATEUR}:{MOT_DE_PASSE}@{SERVEUR}/{base}"
        f"?driver={PILOTE}&{OPTIONS}"
    )
    return create_engine(url, fast_executemany=True)


def creer_base():
    with moteur().connect().execution_options(isolation_level="AUTOCOMMIT") as cx:
        cx.execute(text(
            f"IF DB_ID('{BASE}') IS NULL CREATE DATABASE {BASE}"
        ))
    print(f"Base '{BASE}' prete.")


def creer_tables():
    ddl = """
    IF OBJECT_ID('dim_aeronef') IS NULL
    CREATE TABLE dim_aeronef (
        cle_aeronef   INT IDENTITY(1,1) PRIMARY KEY,
        icao24        VARCHAR(10) NOT NULL UNIQUE,
        pays_origine  VARCHAR(100)
    );

    IF OBJECT_ID('fait_observation') IS NULL
    CREATE TABLE fait_observation (
        cle_observation BIGINT IDENTITY(1,1) PRIMARY KEY,
        cle_aeronef     INT NOT NULL REFERENCES dim_aeronef(cle_aeronef),
        horodatage      DATETIME2 NOT NULL,
        indicatif       VARCHAR(20),
        latitude        FLOAT,
        longitude       FLOAT,
        altitude        FLOAT,
        vitesse_sol     FLOAT,
        au_sol          BIT
    );
    """
    with moteur(BASE).connect().execution_options(isolation_level="AUTOCOMMIT") as cx:
        for bloc in ddl.split(";"):
            if bloc.strip():
                cx.execute(text(bloc))
    print("Tables dim_aeronef et fait_observation pretes.")


def dernier_csv():
    fichiers = sorted(DOSSIER_TRAITE.glob("etats_*.csv"))
    if not fichiers:
        raise FileNotFoundError("Aucun CSV. Lancez transformation.py")
    return fichiers[-1]


def charger(chemin):
    df = pd.read_csv(chemin)
    mt = moteur(BASE)

    # 1. Alimenter la dimension (seulement les nouveaux icao24)
    with mt.connect() as cx:
        existants = pd.read_sql("SELECT icao24 FROM dim_aeronef", cx)

    nouveaux = df[["icao24", "pays_origine"]].drop_duplicates("icao24")
    nouveaux = nouveaux[~nouveaux["icao24"].isin(existants["icao24"])]

    if not nouveaux.empty:
        nouveaux.to_sql("dim_aeronef", mt, if_exists="append", index=False)
    print(f"Nouveaux aeronefs inseres : {len(nouveaux)}")

    # 2. Recuperer les cles et alimenter les faits
    with mt.connect() as cx:
        dim = pd.read_sql("SELECT cle_aeronef, icao24 FROM dim_aeronef", cx)

    faits = df.merge(dim, on="icao24")
    faits = faits[[
        "cle_aeronef", "horodatage", "indicatif", "latitude", "longitude",
        "altitude_barometrique", "vitesse_sol", "au_sol",
    ]].rename(columns={"altitude_barometrique": "altitude"})

    faits.to_sql("fait_observation", mt, if_exists="append", index=False)
    print(f"Observations inserees : {len(faits)}")


if __name__ == "__main__":
    creer_base()
    creer_tables()
    chemin = dernier_csv()
    print(f"Chargement de : {chemin.name}")
    charger(chemin)
