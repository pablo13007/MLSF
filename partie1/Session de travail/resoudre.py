"""Résolution d'une grille Meowdoku (question 3).

grille --(question 1)--> fichier DIMACS --(question 2 : DPLL, algorithme 2)--> valuation
       --> fichier solution au format de la figure 2, relu et vérifié.

Usage en ligne de commande :
    python resoudre.py grille.txt solution.txt [--cnf fichier.cnf] [--graine G]
"""
import os
import random
import sys

from dpll import lire_dimacs, dpll
from meowdoku import lire_grille, grille_vers_cnf, ecrire_dimacs, chats_depuis_valuation, verifier_solution


def ecrire_solution(chemin_grille, grille, chats, chemin):
    """Fichier solution : copie de la grille, puis région -> case du chat, puis grille de '*'."""
    with open(chemin_grille, encoding="utf-8") as f:
        copie = f.read().rstrip("\n")
    chat_de = {grille.region_de(i, j): (i, j) for i, j in chats}
    with open(chemin, "w", encoding="utf-8") as f:
        f.write(copie + "\n\n")
        for z in grille.zones:
            i, j = chat_de[z]
            f.write(f"{z} {i} {j}\n")
        f.write("\n")
        for i in range(1, grille.N + 1):
            f.write(" ".join("*" if (i, j) in chats else "." for j in range(1, grille.M + 1)) + "\n")


def lire_solution(chemin, grille):
    """Relit un fichier solution ; renvoie les chats du dictionnaire et ceux de la grille de '*'."""
    with open(chemin, encoding="utf-8") as f:
        lignes = [l.split() for l in f if l.strip() and not l.startswith("c")]
    lignes = lignes[2 + grille.N:]               # on saute GRID, ZONES et la grille recopiée
    K = len(grille.zones)
    dictionnaire = {z: (int(i), int(j)) for z, i, j in lignes[:K]}
    if sorted(dictionnaire) != sorted(grille.zones):
        raise ValueError("le dictionnaire doit donner un chat par région déclarée")
    etoiles = {(i + 1, j + 1) for i, l in enumerate(lignes[K:K + grille.N])
               for j, s in enumerate(l) if s == "*"}
    return dictionnaire, etoiles


def resoudre(chemin_grille, chemin_solution, chemin_cnf=None, graine=0):
    """Résout la grille, écrit le fichier solution et le vérifie ; renvoie les positions des chats."""
    if chemin_cnf is None:
        chemin_cnf = os.path.splitext(chemin_solution)[0] + ".cnf"
    grille = lire_grille(chemin_grille)
    nb_vars, clauses = grille_vers_cnf(grille)             # question 1 : grille -> DIMACS
    ecrire_dimacs(nb_vars, clauses, chemin_cnf, commentaires=[f"Meowdoku : {chemin_grille}"])
    _, clauses = lire_dimacs(chemin_cnf)                   # question 2 : lecture DIMACS
    sat, v = dpll(clauses, random.Random(graine))          # question 2 : algorithme 2
    if not sat:
        raise ValueError(f"{chemin_grille} : aucune solution (grille illicite)")
    chats = chats_depuis_valuation({p for p, b in v.items() if b}, grille.M)
    ecrire_solution(chemin_grille, grille, chats, chemin_solution)

    # Vérification à partir du fichier écrit, indépendamment du solveur.
    dictionnaire, etoiles = lire_solution(chemin_solution, grille)
    if set(dictionnaire.values()) != etoiles:
        raise ValueError("le dictionnaire et la grille de '*' ne coïncident pas")
    if any(grille.region_de(i, j) != z for z, (i, j) in dictionnaire.items()):
        raise ValueError("un chat n'est pas dans la région annoncée")
    erreurs = verifier_solution(grille, etoiles)
    if erreurs:
        raise ValueError("solution illicite : " + ", ".join(erreurs))
    return chats


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Résolution d'une grille Meowdoku par DPLL")
    parser.add_argument("grille")
    parser.add_argument("solution")
    parser.add_argument("--cnf", default=None, help="fichier DIMACS intermédiaire")
    parser.add_argument("--graine", type=int, default=0)
    args = parser.parse_args()
    try:
        resoudre(args.grille, args.solution, args.cnf, args.graine)
    except ValueError as e:
        sys.exit(str(e))
    print(f"{args.solution} : solution écrite et vérifiée")
