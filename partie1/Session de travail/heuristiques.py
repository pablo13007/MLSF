"""DPLL avec heuristique de branchement (question 4, algorithme 3 de l'énoncé).

Seule la ligne 17 change par rapport à l'algorithme 2 : la décision (p, b) est donnée
par une heuristique au lieu de RandomChoice. Une heuristique est une fonction F -> (p, b).

Heuristiques retenues, toutes calculées sur la formule courante F (versions dynamiques) :
    H1  Première Variable Libre (PVL)
    H2  Variable la plus fréquente avec Polarité Majoritaire (VPPM)
    H3  Littéral le plus fréquent (LP)
    H4  Variable la plus fréquente dans les Clauses de taille Minimale (VFCM / MOMS)

Les variables présentes dans F sont exactement les variables non encore affectées :
simplifier fait disparaître de la formule chaque variable affectée.
En cas d'égalité, on retient la plus petite variable (puis la polarité positive),
ce qui rend le solveur déterministe.

Usage en ligne de commande :
    python heuristiques.py fichier.cnf [--heur H1|H2|H3|H4]
"""
import sys
from collections import Counter

from dpll import lire_dimacs, simplifier, clause_unitaire, litteral_pur, litteral, completer, verifier_modele


# ---------------------------------------------------------------------------
# Heuristiques : F -> (p, b)
# ---------------------------------------------------------------------------

def h1_pvl(F):
    """H1 : plus petite variable présente dans F, avec la valeur 1."""
    return min(abs(l) for c in F for l in c), True


def variable_majoritaire(clauses):
    """Variable p maximisant #(p) dans les clauses, valeur 1 si #+(p) >= #-(p)."""
    occ = Counter(l for c in clauses for l in c)                 # occ[l] = occ(l, F)
    variables = sorted({abs(l) for l in occ})
    p = max(variables, key=lambda x: occ[x] + occ[-x])          # max garde le premier ex aequo
    return p, occ[p] >= occ[-p]


def h2_vppm(F):
    """H2 : variable la plus fréquente de F, polarité majoritaire."""
    return variable_majoritaire(F)


def h3_lp(F):
    """H3 : littéral l le plus fréquent de F ; p = |l|, b = 1 si l est positif."""
    occ = Counter(l for c in F for l in c)
    l = max(sorted(occ, key=lambda l: (abs(l), l < 0)), key=lambda l: occ[l])
    return abs(l), l > 0


def h4_vfcm(F):
    """H4 : H2 restreinte aux clauses de taille minimale k de F.

    Au moment d'une décision, F ne contient ni clause vide ni clause unitaire
    (lignes 1 à 16), donc k >= 2.
    """
    k = min(len(c) for c in F)
    return variable_majoritaire([c for c in F if len(c) == k])


HEURISTIQUES = {"H1": h1_pvl, "H2": h2_vppm, "H3": h3_lp, "H4": h4_vfcm}


# ---------------------------------------------------------------------------
# Algorithme 3 : DPLL_H
# ---------------------------------------------------------------------------

def dpll_h(F, choix):
    """Algorithme 2 dont la décision est confiée à choix(F) ; renvoie (True, v) ou (False, None)."""
    if any(not c for c in F):
        return False, None
    if not F:
        return True, {}
    l = clause_unitaire(F)
    if l is None:
        l = litteral_pur(F)
    if l is not None:                             # lignes 5 à 16 : inchangées
        sat, v = dpll_h(simplifier(F, l), choix)
        if sat:
            v[abs(l)] = l > 0
        return sat, v
    p, b = choix(F)                               # ligne 17 : Heuristics(F, H)
    for valeur in (b, not b):
        sat, v = dpll_h(simplifier(F, litteral(p, valeur)), choix)
        if sat:
            v[p] = valeur
            return True, v
    return False, None


if __name__ == "__main__":
    import argparse
    import time

    parser = argparse.ArgumentParser(description="DPLL avec heuristique de branchement (algorithme 3)")
    parser.add_argument("fichier")
    parser.add_argument("--heur", choices=sorted(HEURISTIQUES), default="H4")
    args = parser.parse_args()

    nb_vars, clauses = lire_dimacs(args.fichier)
    t0 = time.perf_counter()
    sat, v = dpll_h(clauses, HEURISTIQUES[args.heur])
    duree = time.perf_counter() - t0

    print("s SATISFIABLE" if sat else "s UNSATISFIABLE")
    if sat:
        modele = completer(v, nb_vars)
        if not verifier_modele(clauses, modele):
            sys.exit("modèle incorrect")
        print("v " + " ".join(map(str, modele + [0])))
    print(f"temps : {duree:.3f} s", file=sys.stderr)
