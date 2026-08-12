"""Integration du registre des aeronefs civils canadiens (Transport Canada)."""

from pathlib import Path

import pandas as pd
from sqlalchemy import text

from chargement import moteur, BASE
from icao24_canada import marque_vers_icao24

FICHIER = Path.home() / "Downloads" / "ccarcsdb" / "carscurr.txt"

# Positions des colonnes utiles (voir carslayout.txt)
COLONNES = {
    0: "marque",
    3: "constructeur",
    4: "modele",
    10: "categorie",
}


def lire_registre():
    df = pd.read_csv(
        FICHIER,
        header=None,
        usecols=list(COLONNES.keys()),
        names=None,
        encoding="latin-1",
        on_bad_lines="skip",
        low_memory=False,
        dtype=str,
    )
    df.columns = [COLONNES[i] for i in sorted(COLONNES)]

    for c in df.columns:
        df[c] = df[c].astype(str).str.strip()

    df["icao24"] = df["marque"].apply(marque_vers_icao24)
    df = df[df["icao24"].notna()]
    df = df.drop_duplicates("icao24")
    return df


def creer_table():
    ddl = """
    IF OBJECT_ID('dim_registre') IS NULL
    CREATE TABLE dim_registre (
        icao24        VARCHAR(10) PRIMARY KEY,
        marque        VARCHAR(10),
        constructeur  VARCHAR(60),
        modele        VARCHAR(80),
        categorie     VARCHAR(60)
    );
    """
    with moteur(BASE).connect().execution_options(isolation_level="AUTOCOMMIT") as cx:
        cx.execute(text(ddl))
        cx.execute(text("TRUNCATE TABLE dim_registre"))


def charger(df):
    mt = moteur(BASE)
    colonnes = ["icao24", "marque", "constructeur", "modele", "categorie"]
    df[colonnes].to_sql("dim_registre", mt, if_exists="append", index=False, chunksize=1000)


def verifier():
    with moteur(BASE).connect() as cx:
        res = pd.read_sql(text("""
            SELECT
                (SELECT COUNT(*) FROM dim_registre) AS registre,
                (SELECT COUNT(*) FROM dim_aeronef a
                 JOIN dim_registre r ON r.icao24 = a.icao24) AS apparies,
                (SELECT COUNT(*) FROM dim_aeronef WHERE pays_origine = 'Canada') AS canadiens
        """), cx)
        print(res.to_string(index=False))

        print("\nExemples d'appariements :")
        ex = pd.read_sql(text("""
            SELECT TOP 12 a.icao24, r.marque, r.constructeur, r.modele
            FROM dim_aeronef a
            JOIN dim_registre r ON r.icao24 = a.icao24
        """), cx)
        print(ex.to_string(index=False))


if __name__ == "__main__":
    print(f"Lecture de {FICHIER.name} ...")
    df = lire_registre()
    print(f"Aeronefs avec ICAO24 calculable : {len(df)}")
    print(df[["marque", "icao24", "constructeur", "modele"]].head(5).to_string(index=False))

    print("\nChargement en base ...")
    creer_table()
    charger(df)
    print("Termine.\n")
    verifier()
