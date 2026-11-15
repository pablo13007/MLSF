"""Question 6.1 : convertit une grille Meowdoku de la partie I en déclarations du langage.

    python q6_meowdoku/grille_vers_csp.py grille.txt                          # données seules
    python q6_meowdoku/grille_vers_csp.py grille.txt --regles q6_meowdoku/regles/modele2.csp -o g.csp

Les données produites sont celles de l'énoncé (N lignes, M colonnes, K régions, type
Zone, tableau constant region) ; avec --regles, le fichier des règles est recopié à la
suite : un modèle = les données de la grille + les règles, écrites une fois pour toutes.

Les noms de régions de la grille deviennent les valeurs du type Zone. Un nom qui n'est
pas un identifiant du langage, ou qui est déjà pris (mot-clé, nom utilisé par les
règles : N, M, K, ...), est préfixé par Z_.
"""

import argparse
import re
import sys
from pathlib import Path

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI.parent))
sys.path.insert(0, str(ICI.parent.parent / "partie1" / "Session de travail"))

from meowdoku import lire_grille          # noqa: E402  (partie I)
from syntax import KEYWORDS               # noqa: E402

# noms utilisés par les fichiers de règles (q6_meowdoku/regles/)
NOMS_REGLES = {"N", "M", "K", "Zone", "region", "row", "col", "cat", "inzone",
               "i", "j", "k", "l", "z", "z1", "z2", "i1", "j1", "i2", "j2", "abs",
               "atLeastOne", "atMostOne", "exactlyOne", "allDifferent"}
IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def noms_zones(grille):
    """Nom de région de la grille -> nom de la valeur du type Zone."""
    pris, noms = set(KEYWORDS) | NOMS_REGLES, {}
    for z in grille.zones:
        n = z if IDENT.fullmatch(z) else "Z_" + re.sub(r"\W", "_", z)
        while n in pris:
            n = "Z_" + n
        pris.add(n)
        noms[z] = n
    return noms


def donnees(grille, origine=""):
    """Texte des déclarations de la grille."""
    nz = noms_zones(grille)
    largeur = max(len(n) for n in nz.values())
    lignes = [f"// Données de la grille {origine}".rstrip(),
              f"const N = {grille.N};    // lignes",
              f"const M = {grille.M};    // colonnes",
              f"const K = {len(grille.zones)};    // régions",
              "enum Zone = { " + ", ".join(nz[z] for z in grille.zones) + " };",
              "const region[N][M] = ["]
    for i, ligne in enumerate(grille.cases):
        fin = "," if i < grille.N - 1 else ""
        lignes.append("    [" + ", ".join(nz[z].ljust(largeur) for z in ligne).rstrip() + "]" + fin)
    lignes.append("];")
    return "\n".join(lignes) + "\n"


def modele(chemin_grille, chemin_regles=None):
    grille = lire_grille(chemin_grille)
    texte = donnees(grille, Path(chemin_grille).name)
    if chemin_regles:
        texte += "\n" + Path(chemin_regles).read_text(encoding="utf-8")
    return texte


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Grille Meowdoku (partie I) -> modèle du langage")
    ap.add_argument("grille")
    ap.add_argument("--regles", help="fichier de règles à recopier après les données")
    ap.add_argument("-o", "--sortie", help="fichier de sortie (défaut : sortie standard)")
    args = ap.parse_args()
    try:
        texte = modele(args.grille, args.regles)
    except (OSError, ValueError) as e:
        sys.exit(f"{args.grille}: {e}")
    if args.sortie:
        Path(args.sortie).write_text(texte, encoding="utf-8")
    else:
        sys.stdout.write(texte)
