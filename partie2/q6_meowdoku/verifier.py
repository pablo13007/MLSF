"""Question 6.2 : vérificateur indépendant d'une solution Meowdoku.

Il ne lit que la grille (format de la partie I) et la sortie texte du compilateur
(`python csp.py modele.csp --solve` : « s SATISFIABLE » puis des lignes « nom = valeur »),
en retrouve les positions des chats, puis applique le vérificateur de la partie I
(meowdoku.verifier_solution) : au plus un chat par ligne et par colonne, exactement
un par région, pas deux chats voisins.

    python q6_meowdoku/verifier.py grille.txt sortie.txt      (ou la sortie sur stdin)

Les deux modèles sont reconnus :
    premier modèle  row[z] = i, col[z] = j    -> chat de la région z en (i, j)
    second modèle   cat[i][j] = true          -> chat en (i, j)
"""

import re
import sys
from pathlib import Path

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
sys.path.insert(0, str(ICI.parent.parent / "partie1" / "Session de travail"))

from grille_vers_csp import noms_zones                 # noqa: E402
from meowdoku import lire_grille, verifier_solution    # noqa: E402  (partie I)


def chats(grille, lignes):
    """(positions des chats, erreurs propres au premier modèle) d'après la sortie."""
    valeurs = dict(l.split(" = ", 1) for l in lignes if " = " in l)
    if any(k.startswith("cat[") for k in valeurs):
        pos = set()
        for k, v in valeurs.items():
            m = re.fullmatch(r"cat\[(\d+)\]\[(\d+)\]", k)
            if m and v == "true":
                pos.add((int(m.group(1)), int(m.group(2))))
        return pos, []
    pos, erreurs = set(), []
    for z, n in noms_zones(grille).items():
        i, j = int(valeurs[f"row[{n}]"]), int(valeurs[f"col[{n}]"])
        if grille.region_de(i, j) != z:
            erreurs.append(f"le chat de la région {z} est en ({i},{j}), hors de sa région")
        pos.add((i, j))
    return pos, erreurs


def verifier(grille, sortie):
    """Liste des règles violées par la sortie (liste vide : solution correcte)."""
    lignes = sortie.strip().splitlines()
    if not lignes or lignes[0] != "s SATISFIABLE":
        return ["la sortie n'annonce pas de solution"]
    pos, erreurs = chats(grille, lignes[1:])
    return erreurs + verifier_solution(grille, pos)


if __name__ == "__main__":
    if len(sys.argv) not in (2, 3):
        sys.exit("usage : python q6_meowdoku/verifier.py grille.txt [sortie.txt]")
    grille = lire_grille(sys.argv[1])
    sortie = Path(sys.argv[2]).read_text() if len(sys.argv) == 3 else sys.stdin.read()
    erreurs = verifier(grille, sortie)
    if erreurs:
        sys.exit("solution incorrecte : " + "; ".join(erreurs))
    print("solution correcte")
