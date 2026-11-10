"""Ligne de commande du compilateur (interface conseillée par l'énoncé).

À lancer depuis le dossier partie2/ :

    python csp.py model.csp                   # FNC au format DIMACS sur la sortie standard
    python csp.py model.csp --dimacs f.cnf    # FNC écrite dans f.cnf
    python csp.py model.csp --solve           # résolution par le solveur de la partie I
    python csp.py model.csp --ast             # arbre de syntaxe abstraite (question 2)
    python csp.py model.csp --deroule         # contraintes déroulées et simplifiées (question 3)

Avec --solve, la sortie est « s SATISFIABLE » suivi d'une ligne « nom = valeur » par
variable, ou « s UNSATISFIABLE ». Les erreurs et avertissements vont sur stderr ;
un modèle erroné donne le code de retour 1.
"""

import argparse
import sys
import time

from lark.exceptions import UnexpectedInput

from ir import montrer
from solveur import HEURISTIQUES, afficher, compiler, message_syntaxe, resoudre
from symboles import CompileError
from syntax import parse, pretty


def main():
    ap = argparse.ArgumentParser(prog="python csp.py",
                                 description="Compilateur d'un langage de contraintes vers SAT")
    ap.add_argument("model", help="fichier du modèle (.csp)")
    ap.add_argument("--dimacs", metavar="FICHIER", help="écrire la FNC dans FICHIER")
    ap.add_argument("--solve", action="store_true", help="résoudre avec le solveur de la partie I")
    ap.add_argument("--heur", choices=sorted(HEURISTIQUES), default="H4",
                    help="heuristique de branchement du solveur (défaut : H4)")
    ap.add_argument("--ast", action="store_true", help="afficher l'arbre de syntaxe et s'arrêter")
    ap.add_argument("--deroule", action="store_true",
                    help="afficher les contraintes déroulées et s'arrêter")
    ap.add_argument("--stats", action="store_true", help="tailles et temps sur stderr")
    args = ap.parse_args()

    try:
        with open(args.model, encoding="utf-8") as f:
            texte = f.read()
    except OSError as e:
        sys.exit(f"{args.model}: {e.strerror}")

    if args.ast:
        try:
            print(pretty(parse(texte)))
        except UnexpectedInput as e:
            sys.exit(f"{args.model}: {message_syntaxe(e)}")
        return

    t0 = time.perf_counter()
    try:
        modele, fnc = compiler(texte)
    except CompileError as e:
        sys.exit(f"{args.model}: erreur : {e}")
    t_compil = time.perf_counter() - t0
    for a in modele.avertissements:
        print(f"{args.model}: avertissement : {a}", file=sys.stderr)
    if args.stats:
        print(f"c {len(modele.cells)} cases, {len(modele.contraintes)} contraintes déroulées, "
              f"{fnc.nb_vars} variables ({fnc.nb_aux} auxiliaires), {len(fnc.clauses)} clauses, "
              f"compilation {t_compil:.2f} s", file=sys.stderr)

    if args.deroule:
        for c in modele.contraintes:
            print(montrer(c))
        return

    commentaires = [f"modèle {args.model}"]
    if not args.solve:
        if args.dimacs:
            with open(args.dimacs, "w", encoding="utf-8") as f:
                f.write(fnc.dimacs(commentaires))
        else:
            sys.stdout.write(fnc.dimacs(commentaires))
        return

    t0 = time.perf_counter()
    val = resoudre(modele, fnc, args.dimacs, args.heur, commentaires)
    if args.stats:
        print(f"c résolution {time.perf_counter() - t0:.2f} s", file=sys.stderr)
    if val is None:
        print("s UNSATISFIABLE")
    else:
        print("s SATISFIABLE")
        print("\n".join(afficher(modele, val)))


if __name__ == "__main__":
    main()
