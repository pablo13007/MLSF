"""Ligne de commande du compilateur (interface conseillée par l'énoncé).

À lancer depuis le dossier partie2/ :

    python csp.py model.csp                   # FNC au format DIMACS sur la sortie standard
    python csp.py model.csp --dimacs f.cnf    # FNC écrite dans f.cnf
    python csp.py model.csp --solve           # résolution par le solveur de la partie I

Avec --solve, la sortie est « s SATISFIABLE » suivi d'une ligne « nom = valeur » par
variable, ou « s UNSATISFIABLE ». Les erreurs et avertissements vont sur stderr ;
un modèle erroné donne le code de retour 1.
"""

import argparse
import sys

from solveur import afficher, compiler, resoudre
from symboles import CompileError


def main():
    ap = argparse.ArgumentParser(prog="python csp.py",
                                 description="Compilateur d'un langage de contraintes vers SAT")
    ap.add_argument("model", help="fichier du modèle (.csp)")
    ap.add_argument("--dimacs", metavar="FICHIER", help="écrire la FNC dans FICHIER")
    ap.add_argument("--solve", action="store_true", help="résoudre avec le solveur de la partie I")
    args = ap.parse_args()

    try:
        with open(args.model, encoding="utf-8") as f:
            texte = f.read()
    except OSError as e:
        sys.exit(f"{args.model}: {e.strerror}")

    try:
        modele, fnc = compiler(texte)
    except CompileError as e:
        sys.exit(f"{args.model}: erreur : {e}")
    for a in modele.avertissements:
        print(f"{args.model}: avertissement : {a}", file=sys.stderr)

    commentaires = [f"modèle {args.model}"]
    if not args.solve:
        if args.dimacs:
            with open(args.dimacs, "w", encoding="utf-8") as f:
                f.write(fnc.dimacs(commentaires))
        else:
            sys.stdout.write(fnc.dimacs(commentaires))
        return

    val = resoudre(modele, fnc, args.dimacs, commentaires)
    if val is None:
        print("s UNSATISFIABLE")
    else:
        print("s SATISFIABLE")
        print("\n".join(afficher(modele, val)))


if __name__ == "__main__":
    main()
