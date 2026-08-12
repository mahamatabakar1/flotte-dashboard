"""
Conversion entre marque d'immatriculation canadienne et adresse ICAO24.

Le Canada dispose du bloc ICAO24 allant de C00001 a C3FFFF (hexadecimal).
Les marques sont attribuees sequentiellement :
  C-FAAA ... C-FZZZ  puis  C-GAAA ... C-GZZZ
Chaque lettre occupe 26 positions (A-Z).
"""

LETTRES = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

# Base du bloc canadien
BASE_C_F = 0xC00001


def marque_vers_icao24(marque):
    """Convertit une marque (ex. 'GOHS' ou 'C-GOHS') en adresse ICAO24."""
    m = marque.upper().replace("-", "").replace("C", "", 1) if marque.upper().startswith("C") else marque.upper()
    m = m.strip()
    if len(m) != 4 or m[0] not in "FG":
        return None
    if any(c not in LETTRES for c in m[1:]):
        return None

    prefixe = 0 if m[0] == "F" else 1
    a, b, c = (LETTRES.index(x) for x in m[1:])

    offset = prefixe * 26**3 + a * 26**2 + b * 26 + c
    return format(BASE_C_F + offset, "06x")


def icao24_vers_marque(icao24):
    """Convertit une adresse ICAO24 en marque canadienne (ex. 'GOHS')."""
    try:
        valeur = int(icao24, 16)
    except (TypeError, ValueError):
        return None

    offset = valeur - BASE_C_F
    if offset < 0 or offset >= 2 * 26**3:
        return None

    prefixe = "F" if offset < 26**3 else "G"
    reste = offset % (26**3)
    a = reste // (26**2)
    b = (reste // 26) % 26
    c = reste % 26
    return prefixe + LETTRES[a] + LETTRES[b] + LETTRES[c]


if __name__ == "__main__":
    # Paires observees dans nos donnees OpenSky
    tests = [
        ("c06a69", "GOHS"),
        ("c06a35", "GOFS"),
        ("c07bca", "GUWV"),
    ]
    print("Verification sur des paires reelles :\n")
    for icao, attendu in tests:
        obtenu = icao24_vers_marque(icao)
        etat = "OK " if obtenu == attendu else "ECART"
        print(f"  {etat}  {icao} -> {obtenu}   (attendu {attendu})")

    print("\nSens inverse :")
    for icao, marque in tests:
        print(f"  {marque} -> {marque_vers_icao24(marque)}   (attendu {icao})")
