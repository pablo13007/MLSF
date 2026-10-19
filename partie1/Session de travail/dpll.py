"""DPLL : lecture DIMACS (question 2.1) et algorithmes 1 et 2 de l'énoncé (question 2.2).

Représentation des formules :
    littéral  : entier non nul, k pour x_k et -k pour ¬x_k (comme en DIMACS)
    clause    : liste de littéraux
    formule   : liste de clauses (une formule vide est vraie, une clause vide est fausse)
    valuation : dictionnaire variable -> bool

Version volontairement fidèle à l'énoncé : chaque appel récursif reçoit une copie
simplifiée F[l <- 1] de la formule.

Usage en ligne de commande :
    python dpll.py fichier.cnf [--algo 1|2] [--graine G]
"""
import random
import sys

# Chaque appel récursif affecte au moins une variable : profondeur <= nb_vars + 1.
sys.setrecursionlimit(100_000)


# ---------------------------------------------------------------------------
# Lecture DIMACS
# ---------------------------------------------------------------------------

def lire_dimacs(chemin):
    """Lit un fichier DIMACS CNF ; renvoie (nb_vars, clauses)."""
    nb_vars, clauses, courante = None, [], []
    with open(chemin, encoding="utf-8") as f:
        for ligne in f:
            mots = ligne.split()
            if not mots or mots[0].startswith("c"):
                continue
            if mots[0] == "%":                    # marqueur de fin des fichiers SATLIB
                break
            if mots[0] == "p":
                if len(mots) != 4 or mots[1] != "cnf":
                    raise ValueError(f"en-tête invalide : {ligne.strip()}")
                nb_vars = int(mots[2])
                continue
            if nb_vars is None:
                raise ValueError("clause rencontrée avant l'en-tête 'p cnf'")
            for mot in mots:                      # une clause peut tenir sur plusieurs lignes
                l = int(mot)
                if l == 0:
                    clauses.append(courante)
                    courante = []
                elif abs(l) > nb_vars:
                    raise ValueError(f"variable {abs(l)} > {nb_vars} variables annoncées")
                else:
                    courante.append(l)
    if nb_vars is None:
        raise ValueError("en-tête 'p cnf' manquant")
    if courante:                                  # dernière clause sans 0 final
        clauses.append(courante)
    return nb_vars, nettoyer(clauses)


def nettoyer(clauses):
    """Supprime les littéraux répétés et les tautologies (clauses contenant p et ¬p)."""
    resultat = []
    for c in clauses:
        c = list(dict.fromkeys(c))                # [1, 1] -> [1], ordre conservé
        if not any(-l in c for l in c):
            resultat.append(c)
    return resultat


# ---------------------------------------------------------------------------
# Opérations sur les formules
# ---------------------------------------------------------------------------

def simplifier(F, l):
    """F[l <- 1] : on retire les clauses contenant l, et ¬l des autres clauses."""
    return [[m for m in c if m != -l] for c in F if l not in c]


def clause_unitaire(F):
    """Littéral d'une clause unitaire de F, ou None."""
    for c in F:
        if len(c) == 1:
            return c[0]
    return None


def litteral_pur(F):
    """Littéral de F dont l'opposé n'apparaît pas dans F, ou None."""
    litteraux = {l for c in F for l in c}
    for l in sorted(litteraux, key=abs):
        if -l not in litteraux:
            return l
    return None


def random_choice(F, rng):
    """RandomChoice(F) : variable p de F et valeur b au hasard ; renvoie (p, b)."""
    p = rng.choice(sorted({abs(l) for c in F for l in c}))
    b = rng.choice((True, False))
    return p, b


def litteral(p, b):
    """Littéral vrai lorsque p vaut b : F[p <- b] = F[litteral(p, b) <- 1]."""
    return p if b else -p


# ---------------------------------------------------------------------------
# Algorithme 1 : SAT / UNSAT
# ---------------------------------------------------------------------------

def dpll_statut(F, rng=random):
    """True si F est satisfiable, False sinon."""
    if any(not c for c in F):                     # clause vide
        return False
    if not F:                                     # plus aucune clause
        return True
    l = clause_unitaire(F)
    if l is not None:
        return dpll_statut(simplifier(F, l), rng)
    l = litteral_pur(F)
    if l is not None:
        return dpll_statut(simplifier(F, l), rng)
    p, b = random_choice(F, rng)
    if dpll_statut(simplifier(F, litteral(p, b)), rng):
        return True
    return dpll_statut(simplifier(F, litteral(p, not b)), rng)


# ---------------------------------------------------------------------------
# Algorithme 2 : SAT / UNSAT + valuation
# ---------------------------------------------------------------------------

def dpll(F, rng=random):
    """Renvoie (True, v) avec v valuation satisfaisant F, ou (False, None)."""
    if any(not c for c in F):
        return False, None
    if not F:
        return True, {}
    l = clause_unitaire(F)
    if l is None:
        l = litteral_pur(F)
    if l is not None:                             # lignes 5 à 16 : un seul choix possible
        sat, v = dpll(simplifier(F, l), rng)
        if sat:
            v[abs(l)] = l > 0                     # v ∪ {l}
        return sat, v
    p, b = random_choice(F, rng)                  # lignes 17 à 26 : décision
    for valeur in (b, not b):                     # branche then, puis retour arrière
        sat, v = dpll(simplifier(F, litteral(p, valeur)), rng)
        if sat:
            v[p] = valeur                         # v ∪ {p <- valeur}
            return True, v
    return False, None


# ---------------------------------------------------------------------------
# Modèles
# ---------------------------------------------------------------------------

def completer(v, nb_vars):
    """Modèle DIMACS [±1, ..., ±nb_vars] ; les variables absentes de v valent faux.

    Une variable absente de v a disparu de la formule sans être affectée
    (toutes ses clauses étaient déjà satisfaites) : n'importe quelle valeur convient.
    """
    return [x if v.get(x, False) else -x for x in range(1, nb_vars + 1)]


def verifier_modele(clauses, modele):
    """True si chaque clause contient au moins un littéral du modèle."""
    vrais = set(modele)
    return all(any(l in vrais for l in c) for c in clauses)


if __name__ == "__main__":
    import argparse
    import time

    parser = argparse.ArgumentParser(description="DPLL, algorithmes 1 et 2 de l'énoncé")
    parser.add_argument("fichier")
    parser.add_argument("--algo", type=int, choices=(1, 2), default=2)
    parser.add_argument("--graine", type=int, default=None)
    args = parser.parse_args()

    nb_vars, clauses = lire_dimacs(args.fichier)
    rng = random.Random(args.graine)
    t0 = time.perf_counter()
    if args.algo == 1:
        sat, modele = dpll_statut(clauses, rng), None
    else:
        sat, v = dpll(clauses, rng)
        modele = completer(v, nb_vars) if sat else None
    duree = time.perf_counter() - t0

    print("s SATISFIABLE" if sat else "s UNSATISFIABLE")
    if modele is not None:
        if not verifier_modele(clauses, modele):
            sys.exit("modèle incorrect")
        print("v " + " ".join(map(str, modele + [0])))
    print(f"temps : {duree:.3f} s", file=sys.stderr)
