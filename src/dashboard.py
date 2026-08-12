import json
from datetime import datetime
from pathlib import Path

import pandas as pd
from sqlalchemy import text

from chargement import moteur, BASE

SORTIE = Path(__file__).resolve().parent.parent / "dashboard.html"

COMPAGNIES = {
    "ACA": "Air Canada", "WJA": "WestJet", "JZA": "Jazz", "TSC": "Air Transat",
    "POE": "Porter", "ROU": "Air Canada Rouge", "PVL": "Pivot",
}


def charger_donnees():
    mt = moteur(BASE)
    with mt.connect() as cx:
        resume = pd.read_sql(text("""
            SELECT
                (SELECT COUNT(*) FROM dim_aeronef) AS aeronefs,
                (SELECT COUNT(*) FROM fait_observation) AS observations,
                (SELECT COUNT(DISTINCT horodatage) FROM fait_observation) AS releves
        """), cx)
        evolution = pd.read_sql(text("""
            SELECT horodatage, COUNT(*) AS total,
                SUM(CASE WHEN au_sol = 0 THEN 1 ELSE 0 END) AS en_vol,
                SUM(CASE WHEN au_sol = 1 THEN 1 ELSE 0 END) AS au_sol
            FROM fait_observation GROUP BY horodatage ORDER BY horodatage
        """), cx)
        pays = pd.read_sql(text("""
            SELECT TOP 8 a.pays_origine, COUNT(*) AS observations
            FROM fait_observation f JOIN dim_aeronef a ON a.cle_aeronef = f.cle_aeronef
            GROUP BY a.pays_origine ORDER BY observations DESC
        """), cx)
        compagnies = pd.read_sql(text("""
            SELECT TOP 10 LEFT(f.indicatif,3) AS code, COUNT(*) AS observations
            FROM fait_observation f JOIN dim_aeronef a ON a.cle_aeronef = f.cle_aeronef
            WHERE a.pays_origine = 'Canada' AND f.indicatif IS NOT NULL
            GROUP BY LEFT(f.indicatif,3) ORDER BY observations DESC
        """), cx)
        altitudes = pd.read_sql(text("""
            SELECT altitude FROM fait_observation
            WHERE altitude IS NOT NULL AND au_sol = 0
        """), cx)
    return resume, evolution, pays, compagnies, altitudes


def generer():
    resume, evolution, pays, compagnies, altitudes = charger_donnees()
    r = resume.iloc[0]
    taux = 100 * evolution["en_vol"].sum() / evolution["total"].sum()
    evolution["libelle"] = pd.to_datetime(evolution["horodatage"]).dt.strftime("%d/%m %H:%M")
    compagnies["nom"] = compagnies["code"].map(COMPAGNIES).fillna(compagnies["code"])
    tranches = pd.cut(
        altitudes["altitude"],
        bins=[0, 1000, 3000, 6000, 9000, 12000, 20000],
        labels=["0-1k", "1-3k", "3-6k", "6-9k", "9-12k", "12k+"],
    ).value_counts().sort_index()
    donnees = {
        "evolution": {
            "labels": evolution["libelle"].tolist(),
            "en_vol": evolution["en_vol"].tolist(),
            "au_sol": evolution["au_sol"].tolist(),
        },
        "pays": {
            "labels": pays["pays_origine"].tolist(),
            "valeurs": pays["observations"].tolist(),
        },
        "compagnies": {
            "labels": compagnies["nom"].tolist(),
            "valeurs": compagnies["observations"].tolist(),
        },
        "altitudes": {
            "labels": [str(x) for x in tranches.index],
            "valeurs": [int(x) for x in tranches.values],
        },
    }
    html = TEMPLATE.replace("__DONNEES__", json.dumps(donnees))
    html = html.replace("__AERONEFS__", str(int(r["aeronefs"])))
    html = html.replace("__OBSERVATIONS__", str(int(r["observations"])))
    html = html.replace("__RELEVES__", str(int(r["releves"])))
    html = html.replace("__TAUX__", f"{taux:.1f}")
    html = html.replace("__DATE__", datetime.now().strftime("%d/%m/%Y %H:%M"))
    SORTIE.write_text(html)
    print(f"Tableau de bord genere : {SORTIE}")


TEMPLATE = """<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<title>Utilisation de flotte - Quebec</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.0/chart.umd.min.js"></script>
<style>
  :root { --bleu:#1b3a5c; --accent:#2e86ab; --sol:#c85a3c; --fond:#f4f2ed; }
  * { box-sizing:border-box; }
  body { margin:0; background:var(--fond); font-family:-apple-system,BlinkMacSystemFont,sans-serif; color:#1a1a1a; }
  header { background:var(--bleu); color:#fff; padding:32px 40px; }
  h1 { margin:0 0 6px; font-size:26px; font-weight:600; }
  header p { margin:0; opacity:.75; font-size:14px; }
  .conteneur { max-width:1200px; margin:0 auto; padding:32px 40px 60px; }
  .kpis { display:grid; grid-template-columns:repeat(auto-fit,minmax(200px,1fr)); gap:16px; margin-bottom:32px; }
  .kpi { background:#fff; border-radius:10px; padding:22px 24px; border-left:3px solid var(--accent); }
  .kpi .valeur { font-size:34px; font-weight:600; color:var(--bleu); line-height:1.1; }
  .kpi .titre { font-size:12px; text-transform:uppercase; letter-spacing:1px; color:#777; margin-top:6px; }
  .grille { display:grid; grid-template-columns:repeat(auto-fit,minmax(460px,1fr)); gap:20px; }
  .carte { background:#fff; border-radius:10px; padding:24px; }
  .carte h2 { margin:0 0 18px; font-size:15px; font-weight:600; color:var(--bleu); }
  footer { text-align:center; padding:24px; font-size:12px; color:#888; }
</style>
</head>
<body>
<header>
  <h1>Utilisation de flotte aerienne - espace aerien quebecois</h1>
  <p>Donnees OpenSky Network - genere le __DATE__</p>
</header>
<div class="conteneur">
  <div class="kpis">
    <div class="kpi"><div class="valeur">__AERONEFS__</div><div class="titre">Aeronefs distincts</div></div>
    <div class="kpi"><div class="valeur">__OBSERVATIONS__</div><div class="titre">Observations</div></div>
    <div class="kpi"><div class="valeur">__TAUX__ %</div><div class="titre">Taux d'utilisation</div></div>
    <div class="kpi"><div class="valeur">__RELEVES__</div><div class="titre">Releves effectues</div></div>
  </div>
  <div class="grille">
    <div class="carte"><h2>Evolution : en vol vs au sol</h2><canvas id="g1"></canvas></div>
    <div class="carte"><h2>Transporteurs canadiens</h2><canvas id="g2"></canvas></div>
    <div class="carte"><h2>Repartition par pays d'immatriculation</h2><canvas id="g3"></canvas></div>
    <div class="carte"><h2>Distribution des altitudes (m)</h2><canvas id="g4"></canvas></div>
  </div>
</div>
<footer>Pipeline ETL - Python, SQL Server, schema en etoile</footer>
<script>
const D = __DONNEES__;
const BLEU = '#2e86ab', ROUGE = '#c85a3c', FONCE = '#1b3a5c';
new Chart(document.getElementById('g1'), {
  type: 'line',
  data: { labels: D.evolution.labels, datasets: [
    { label:'En vol', data:D.evolution.en_vol, borderColor:BLEU, backgroundColor:'rgba(46,134,171,.1)', fill:true, tension:.3 },
    { label:'Au sol', data:D.evolution.au_sol, borderColor:ROUGE, backgroundColor:'rgba(200,90,60,.1)', fill:true, tension:.3 }
  ]},
  options: { responsive:true, scales:{ y:{ beginAtZero:true } } }
});
new Chart(document.getElementById('g2'), {
  type: 'bar',
  data: { labels: D.compagnies.labels, datasets:[{ label:'Observations', data:D.compagnies.valeurs, backgroundColor:BLEU }] },
  options: { indexAxis:'y', plugins:{ legend:{ display:false } } }
});
new Chart(document.getElementById('g3'), {
  type: 'doughnut',
  data: { labels: D.pays.labels, datasets:[{ data:D.pays.valeurs,
    backgroundColor:['#1b3a5c','#2e86ab','#5fa8c9','#94c5d8','#c85a3c','#d98b6f','#e8b4a0','#cfcfcf'] }] },
  options: { plugins:{ legend:{ position:'right' } } }
});
new Chart(document.getElementById('g4'), {
  type: 'bar',
  data: { labels: D.altitudes.labels, datasets:[{ label:'Aeronefs', data:D.altitudes.valeurs, backgroundColor:FONCE }] },
  options: { plugins:{ legend:{ display:false } }, scales:{ y:{ beginAtZero:true } } }
});
</script>
</body>
</html>"""


if __name__ == "__main__":
    generer()
