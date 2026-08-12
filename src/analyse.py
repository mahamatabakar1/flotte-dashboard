import pandas as pd
from sqlalchemy import text

from chargement import moteur, BASE

REQUETES = {
    "Volume global": """
        SELECT
            (SELECT COUNT(*) FROM dim_aeronef)      AS aeronefs_distincts,
            (SELECT COUNT(*) FROM fait_observation) AS observations,
            (SELECT COUNT(DISTINCT horodatage) FROM fait_observation) AS releves
    """,

    "Top 10 aeronefs les plus observes": """
        SELECT TOP 10
            a.icao24,
            a.pays_origine,
            COUNT(*)                                   AS nb_observations,
            SUM(CASE WHEN f.au_sol = 1 THEN 1 ELSE 0 END) AS fois_au_sol,
            CAST(AVG(f.altitude) AS DECIMAL(10,1))     AS altitude_moyenne
        FROM fait_observation f
        JOIN dim_aeronef a ON a.cle_aeronef = f.cle_aeronef
        GROUP BY a.icao24, a.pays_origine
        ORDER BY nb_observations DESC
    """,

    "Taux d'utilisation par pays": """
        SELECT
            a.pays_origine,
            COUNT(*)                                          AS observations,
            SUM(CASE WHEN f.au_sol = 0 THEN 1 ELSE 0 END)      AS en_vol,
            CAST(100.0 * SUM(CASE WHEN f.au_sol = 0 THEN 1 ELSE 0 END)
                 / COUNT(*) AS DECIMAL(5,1))                   AS taux_utilisation_pct
        FROM fait_observation f
        JOIN dim_aeronef a ON a.cle_aeronef = f.cle_aeronef
        GROUP BY a.pays_origine
        HAVING COUNT(*) >= 5
        ORDER BY observations DESC
    """,

    "Evolution par releve": """
        SELECT
            horodatage,
            COUNT(*)                                      AS aeronefs_detectes,
            SUM(CASE WHEN au_sol = 0 THEN 1 ELSE 0 END)   AS en_vol,
            SUM(CASE WHEN au_sol = 1 THEN 1 ELSE 0 END)   AS au_sol,
            CAST(AVG(vitesse_sol) AS DECIMAL(10,1))       AS vitesse_moyenne
        FROM fait_observation
        GROUP BY horodatage
        ORDER BY horodatage
    """,

    "Transporteurs canadiens (indicatifs)": """
        SELECT TOP 15
            LEFT(f.indicatif, 3)  AS prefixe_compagnie,
            COUNT(*)              AS observations,
            COUNT(DISTINCT f.cle_aeronef) AS aeronefs_distincts
        FROM fait_observation f
        JOIN dim_aeronef a ON a.cle_aeronef = f.cle_aeronef
        WHERE a.pays_origine = 'Canada' AND f.indicatif IS NOT NULL
        GROUP BY LEFT(f.indicatif, 3)
        HAVING COUNT(*) >= 2
        ORDER BY observations DESC
    """,
}


def executer():
    mt = moteur(BASE)
    with mt.connect() as cx:
        for titre, sql in REQUETES.items():
            print("\n" + "=" * 70)
            print(titre.upper())
            print("=" * 70)
            df = pd.read_sql(text(sql), cx)
            if df.empty:
                print("(aucun resultat)")
            else:
                print(df.to_string(index=False))


if __name__ == "__main__":
    executer()
