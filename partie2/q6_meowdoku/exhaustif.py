"""Question 6.5 : second modèle généralisé (N, M, K quelconques), comparé à une
recherche exhaustive sur de petites grilles.

    python q6_meowdoku/exhaustif.py [--nombre 300] [--graine 0]

Pour chaque grille aléatoire (N, M entre 2 et 5, K entre 1 et 6 régions connexes,
sans garantie de solution) :
  - recherche exhaustive, indépendante du compilateur : on essaie toutes les façons de
    choisir une case par région (exactement un chat par région) et on garde celles que
    le vérificateur de la partie I accepte ;
  - résolution avec regles/modele2_general.csp ;
  - les réponses SAT/UNSAT doivent coïncider, et chaque solution trouvée par le
    solveur est validée par le vérificateur indépendant (verifier.py).
"""

import argparse
import random
from itertools import product

from commun import MODELES, sortie_solve
from grille_vers_csp import donnees
from meowdoku import Grille, verifier_solution
from generateur import nom_zone
from verifier import verifier


def grille_aleatoire(rng):
    """Grille N x M en K régions connexes, obtenues en faisant grandir K germes."""
    N, M = rng.randint(2, 5), rng.randint(2, 5)
    K = rng.randint(1, min(6, N * M))
    cases = [[None] * M for _ in range(N)]
    germes = rng.sample([(i, j) for i in range(N) for j in range(M)], K)
    bord = []
    for k, (i, j) in enumerate(germes):
        cases[i][j] = k
        bord.append([(i, j)])
    libres = N * M - K
    while libres:
        k = rng.randrange(K)
        if not bord[k]:
            continue
        i, j = rng.choice(bord[k])
        voisins = [(a, b) for a, b in ((i - 1, j), (i + 1, j), (i, j - 1), (i, j + 1))
                   if 0 <= a < N and 0 <= b < M and cases[a][b] is None]
        if not voisins:
            bord[k].remove((i, j))
            continue
        a, b = rng.choice(voisins)
        cases[a][b] = k
        bord[k].append((a, b))
        libres -= 1
    zones = [nom_zone(k) for k in range(K)]
    return Grille(N, M, zones, [[zones[k] for k in ligne] for ligne in cases])


def solutions_exhaustives(grille):
    """Toutes les configurations licites : une case par région, vérifiée par la partie I."""
    regions = list(grille.regions().values())
    return [choix for choix in product(*regions) if not verifier_solution(grille, choix)]


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--nombre", type=int, default=300)
    ap.add_argument("--graine", type=int, default=0)
    args = ap.parse_args()

    rng = random.Random(args.graine)
    regles = MODELES["modele2_general"].read_text(encoding="utf-8")
    accords = sat = verifiees = 0
    for k in range(args.nombre):
        grille = grille_aleatoire(rng)
        attendu = bool(solutions_exhaustives(grille))
        sortie = sortie_solve(donnees(grille) + "\n" + regles)
        obtenu = sortie.startswith("s SATISFIABLE")
        accords += attendu == obtenu
        sat += attendu
        if obtenu:
            erreurs = verifier(grille, sortie)
            verifiees += not erreurs
            assert not erreurs, (k, erreurs)
        assert attendu == obtenu, (k, grille.N, grille.M, grille.cases)
    print(f"{args.nombre} grilles ({sat} SAT, {args.nombre - sat} UNSAT) : "
          f"{accords} réponses identiques à la recherche exhaustive, "
          f"{verifiees} solutions validées par le vérificateur")
