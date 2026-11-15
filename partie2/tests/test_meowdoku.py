"""Tests de la question 6 : conversion des grilles, modèles Meowdoku, vérificateur.

À lancer depuis partie2/ :  python -m tests.test_meowdoku
"""

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "q6_meowdoku"))

from commun import GRILLE_ENONCE, MODELES, grille_generee, resoudre_et_verifier, sortie_solve  # noqa: E402
from exhaustif import grille_aleatoire, solutions_exhaustives                                  # noqa: E402
from grille_vers_csp import donnees, noms_zones                                                # noqa: E402
from meowdoku import Grille, lire_grille                                                       # noqa: E402
from verifier import verifier                                                                  # noqa: E402


def test_conversion():
    texte = donnees(lire_grille(str(GRILLE_ENONCE)), "grille_enonce.txt")
    assert "const N = 6;" in texte and "enum Zone = { A, B, C, D, E, F };" in texte
    assert "    [A, B, C, B, B, D]," in texte and "    [F, A, D, D, D, D]\n];" in texte
    # noms de régions en conflit avec les règles ou les mots-clés : préfixés
    g = Grille(1, 4, ["K", "in", "1x", "Z_K"], [["K", "in", "1x", "Z_K"]])
    assert noms_zones(g) == {"K": "Z_K", "in": "Z_in", "1x": "Z_1x", "Z_K": "Z_Z_K"}


def test_modeles_sur_grilles():
    # N = M = K : chaque modèle trouve une solution, validée par le vérificateur
    for chemin in [GRILLE_ENONCE, grille_generee(6, 0), grille_generee(7, 1)]:
        for nom in MODELES:
            statut, erreurs, _ = resoudre_et_verifier(chemin, nom)
            assert statut == "SATISFIABLE" and not erreurs, (chemin.name, nom, erreurs)


def test_verificateur_rejette():
    g = lire_grille(str(GRILLE_ENONCE))
    bonne = "s SATISFIABLE\n" + "\n".join(
        f"cat[{i}][{j}] = true" for i, j in [(1, 3), (2, 5), (3, 2), (4, 4), (5, 6), (6, 1)])
    assert verifier(g, bonne) == []
    voisins = bonne.replace("cat[2][5]", "cat[2][4]")          # (1,3) et (2,4) voisins
    assert verifier(g, voisins)
    assert verifier(g, "s UNSATISFIABLE\n")


def test_general_contre_exhaustif():
    rng = random.Random(7)
    regles = MODELES["modele2_general"].read_text(encoding="utf-8")
    for _ in range(60):
        g = grille_aleatoire(rng)
        sortie = sortie_solve(donnees(g) + "\n" + regles)
        assert sortie.startswith("s SATISFIABLE") == bool(solutions_exhaustives(g))
        if sortie.startswith("s SATISFIABLE"):
            assert verifier(g, sortie) == []


if __name__ == "__main__":
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print(f"{name}: ok")
