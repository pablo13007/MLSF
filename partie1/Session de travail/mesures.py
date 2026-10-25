"""Instrumentation des solveurs DPLL_H (question 5).

dpll_mesure reprend exactement dpll_h (algorithme 3) en comptant, au fil de l'exécution :
    decisions  nombre d'exécutions de la ligne 17 (appel à l'heuristique)
    retours    nombre de retours arrière (branche else, ligne 21)
    unitaires  nombre de propagations unitaires (ligne 5)
    purs       nombre d'applications de la règle du littéral pur (ligne 11)
    temps_heur temps passé dans l'heuristique, pour le ratio temps heuristique / temps total

Solveurs comparés (noms utilisés dans le notebook et le rapport) :
    H0         choix aléatoire (RandomChoice) : identique à l'algorithme 2 à graine égale
    H1         première variable libre (statique par nature)
    H2d..H4d   heuristiques H2 à H4 de la question 4 (dynamiques)
    H2s..H4s   versions statiques : l'ordre des décisions est calculé une seule fois

Usage en ligne de commande (une ligne JSON sur la sortie standard) :
    python mesures.py fichier.cnf --heur H4d [--graine G] [--limite S]
"""
import random
import signal
import sys
import time
from collections import Counter

from dpll import lire_dimacs, simplifier, clause_unitaire, litteral_pur, litteral, random_choice, completer, verifier_modele
from heuristiques import h1_pvl, h2_vppm, h3_lp, h4_vfcm

sys.setrecursionlimit(100_000)


class Mesures:
    """Compteurs d'une exécution de dpll_mesure."""

    def __init__(self):
        self.decisions = self.retours = self.unitaires = self.purs = 0
        self.temps_heur = 0.0


# ---------------------------------------------------------------------------
# Algorithme 3 instrumenté
# ---------------------------------------------------------------------------

def dpll_mesure(F, choix, m):
    """dpll_h(F, choix) en mettant à jour les compteurs m ; renvoie (True, v) ou (False, None)."""
    if any(not c for c in F):
        return False, None
    if not F:
        return True, {}
    l = clause_unitaire(F)
    if l is not None:
        m.unitaires += 1                          # ligne 5
    else:
        l = litteral_pur(F)
        if l is not None:
            m.purs += 1                           # ligne 11
    if l is not None:
        sat, v = dpll_mesure(simplifier(F, l), choix, m)
        if sat:
            v[abs(l)] = l > 0
        return sat, v
    m.decisions += 1                              # ligne 17
    t0 = time.perf_counter()
    p, b = choix(F)
    m.temps_heur += time.perf_counter() - t0
    sat, v = dpll_mesure(simplifier(F, litteral(p, b)), choix, m)
    if not sat:
        m.retours += 1                            # ligne 21 : branche else
        b = not b
        sat, v = dpll_mesure(simplifier(F, litteral(p, b)), choix, m)
    if sat:
        v[p] = b
    return sat, v


# ---------------------------------------------------------------------------
# Versions statiques de H2, H3 et H4
# ---------------------------------------------------------------------------
# Chaque fonction ordre_hX(F) classe toutes les décisions (p, b) possibles selon le critère
# de Hx, avec les mêmes règles d'égalité que heuristiques.py : ordre_hX(F)[0] == hX(F).

def ordre_h2(F):
    """Variables par #(p, F) décroissant, chacune avec sa polarité majoritaire."""
    occ = Counter(l for c in F for l in c)
    variables = sorted({abs(l) for l in occ}, key=lambda p: (-occ[p] - occ[-p], p))
    return [(p, occ[p] >= occ[-p]) for p in variables]


def ordre_h3(F):
    """Littéraux par occ(l, F) décroissant ; une variable y figure avec ses deux polarités."""
    occ = Counter(l for c in F for l in c)
    return [(abs(l), l > 0) for l in sorted(occ, key=lambda l: (-occ[l], abs(l), l < 0))]


def ordre_h4(F):
    """Variables par #_k(p, F) décroissant (k taille minimale), puis les autres par numéro."""
    k = min(len(c) for c in F)
    tete = ordre_h2([c for c in F if len(c) == k])
    vues = {p for p, _ in tete}
    return tete + [(p, True) for p in sorted({abs(l) for c in F for l in c} - vues)]


def statique(ordre):
    """Heuristique statique : l'ordre est calculé une fois, puis on prend la première
    décision (p, b) de cet ordre dont la variable p est encore présente dans F.

    L'ordre est calculé sur la formule de la première décision, c'est-à-dire la formule
    initiale après les propagations unitaires et littéraux purs qui précèdent toute décision
    (sinon les clauses unitaires initiales fixeraient k = 1 pour H4). Comme F ne fait que
    se réduire, toute variable présente plus tard dans F figure dans cet ordre.
    """
    cache = []

    def choix(F):
        if not cache:
            cache.extend(ordre(F))
        presentes = {abs(l) for c in F for l in c}
        return next((p, b) for p, b in cache if p in presentes)

    return choix


def solveur(nom, graine=0):
    """Fonction de choix associée au nom ; une nouvelle à chaque exécution (cache statique, graine)."""
    if nom == "H0":
        rng = random.Random(graine)
        return lambda F: random_choice(F, rng)
    dynamiques = {"H1": h1_pvl, "H2d": h2_vppm, "H3d": h3_lp, "H4d": h4_vfcm}
    statiques = {"H2s": ordre_h2, "H3s": ordre_h3, "H4s": ordre_h4}
    if nom in dynamiques:
        return dynamiques[nom]
    return statique(statiques[nom])


SOLVEURS = ["H0", "H1", "H2d", "H3d", "H4d", "H2s", "H3s", "H4s"]


# ---------------------------------------------------------------------------
# Une exécution mesurée
# ---------------------------------------------------------------------------

class Limite(Exception):
    pass


def _interrompre(signum, frame):
    raise Limite


def mesurer(chemin, nom, graine=0, limite=None):
    """Résout le fichier DIMACS avec le solveur nom ; renvoie un dictionnaire de mesures.

    Si la limite (en secondes) est atteinte, statut = "TIMEOUT" et les compteurs sont ceux
    atteints à l'interruption.
    """
    nb_vars, clauses = lire_dimacs(chemin)
    m, choix = Mesures(), solveur(nom, graine)
    if limite:
        signal.signal(signal.SIGALRM, _interrompre)
        signal.setitimer(signal.ITIMER_REAL, limite)
    cpu0, t0 = time.process_time(), time.perf_counter()
    try:
        sat, v = dpll_mesure(clauses, choix, m)
        statut = "SAT" if sat else "UNSAT"
    except Limite:
        statut, sat = "TIMEOUT", False
    duree, cpu = time.perf_counter() - t0, time.process_time() - cpu0
    if limite:
        signal.setitimer(signal.ITIMER_REAL, 0)
    return {
        "statut": statut,
        "modele_valide": verifier_modele(clauses, completer(v, nb_vars)) if sat else None,
        "decisions": m.decisions, "retours": m.retours,
        "unitaires": m.unitaires, "purs": m.purs,
        "cpu": cpu, "duree": duree, "temps_heur": m.temps_heur,
        "ratio_heur": m.temps_heur / duree if duree > 0 else 0.0,
    }


if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(description="DPLL_H instrumenté (question 5)")
    parser.add_argument("fichier")
    parser.add_argument("--heur", choices=SOLVEURS, default="H4d")
    parser.add_argument("--graine", type=int, default=0)
    parser.add_argument("--limite", type=float, default=None)
    args = parser.parse_args()
    print(json.dumps(mesurer(args.fichier, args.heur, args.graine, args.limite)))
