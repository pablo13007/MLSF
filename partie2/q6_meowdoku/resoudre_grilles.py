"""Question 6.2 : résout des grilles avec chacun des modèles et vérifie chaque solution
avec le vérificateur indépendant (verifier.py).

    python q6_meowdoku/resoudre_grilles.py [--tailles 4 5 6 7 8] [--graines 0 1 2]

Grilles : celle de l'énoncé de la partie I, plus des grilles N x N engendrées par le
générateur de la partie I (elles ont toutes au moins une solution).
"""

import argparse

from commun import GRILLE_ENONCE, grille_generee, resoudre_et_verifier

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--tailles", type=int, nargs="+", default=[4, 5, 6, 7, 8])
    ap.add_argument("--graines", type=int, nargs="+", default=[0, 1, 2])
    ap.add_argument("--modeles", nargs="+", default=["modele1", "modele2"])
    args = ap.parse_args()

    grilles = [GRILLE_ENONCE] + [grille_generee(n, g) for n in args.tailles for g in args.graines]
    echecs = 0
    for chemin in grilles:
        for nom in args.modeles:
            statut, erreurs, duree = resoudre_et_verifier(chemin, nom)
            ok = statut == "SATISFIABLE" and not erreurs
            echecs += not ok
            print(f"{chemin.name:20} {nom:18} {statut:14} {duree:7.2f} s  "
                  + ("solution vérifiée" if ok else "ÉCHEC " + "; ".join(erreurs)))
    print(f"{len(grilles) * len(args.modeles) - echecs} résolutions vérifiées sur "
          f"{len(grilles) * len(args.modeles)}")
