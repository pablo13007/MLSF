"""Tests de la traduction en FNC (questions 1 et 4) : validation aléatoire et tailles.

Validation aléatoire (filet de sécurité de la question 1, étendu aux domaines finis) :
on engendre des modèles aléatoires avec peu de variables, on les compile, puis on
compare au résultat d'une recherche exhaustive, calculée par un évaluateur de l'AST
écrit ici, indépendamment du compilateur (ni IR, ni déroulement) :
  1. la FNC est satisfiable si et seulement si le modèle l'est ;
  2. la solution décodée du modèle de la FNC est une solution du modèle ;
  3. (équivalence) pour chaque valuation des variables du modèle, la FNC à laquelle on
     ajoute les clauses unitaires fixant ces variables est satisfiable si et seulement
     si la valuation satisfait le modèle : les variables auxiliaires ne changent rien.

À lancer depuis partie2/ :  python -m tests.test_fnc
"""

import random
from itertools import product

from solveur import compiler, dpll_h, HEURISTIQUES
from syntax import (And, Call, Compare, Constraint, Implies, IntLit, Not, Or, Program, Var,
                    source)

h4 = HEURISTIQUES["H4"]


# ---------------------------------------------------------------------------
# Évaluateur de référence, sur l'AST
# ---------------------------------------------------------------------------

def eval_ast(e, val, enum_codes):
    if isinstance(e, IntLit):
        return e.value
    if isinstance(e, Var):
        return val[e.name] if e.name in val else enum_codes[e.name]
    if isinstance(e, Not):
        return not eval_ast(e.expr, val, enum_codes)
    if isinstance(e, (And, Or, Implies)):
        a, b = eval_ast(e.left, val, enum_codes), eval_ast(e.right, val, enum_codes)
        return {And: a and b, Or: a or b, Implies: (not a) or b}[type(e)]
    if isinstance(e, Compare):
        a, b = eval_ast(e.left, val, enum_codes), eval_ast(e.right, val, enum_codes)
        return {"=": a == b, "!=": a != b, "<": a < b, "<=": a <= b,
                ">": a > b, ">=": a >= b}[e.op]
    if isinstance(e, Call):
        vs = [eval_ast(a, val, enum_codes) for a in e.args]
        if e.name == "allDifferent":
            return len(set(vs)) == len(vs)
        n = sum(map(bool, vs))
        return {"atLeastOne": n >= 1, "atMostOne": n <= 1, "exactlyOne": n == 1}[e.name]
    raise TypeError(e)


# ---------------------------------------------------------------------------
# Modèles aléatoires
# ---------------------------------------------------------------------------

def random_bool(rng, depth, bools, ints, enums):
    """Expression booléenne aléatoire (AST) sur les variables données."""
    if depth == 0 or rng.random() < 0.25:
        k = rng.randrange(4 if ints else 1)
        if k == 0 or not ints:
            return Var(rng.choice(bools))
        if k == 1:                                     # variable entière contre constante
            ops = ["=", "!=", "<", "<=", ">", ">="]
            a, c = Var(rng.choice(ints)), IntLit(rng.randint(0, 5))
            return Compare(rng.choice(ops), *((a, c) if rng.random() < 0.7 else (c, a)))
        if k == 2:                                     # deux variables entières
            ops = ["=", "!=", "<", "<=", ">", ">="]
            return Compare(rng.choice(ops), Var(rng.choice(ints)), Var(rng.choice(ints)))
        names, values = enums                          # valeurs énumérées
        b = Var(rng.choice(values)) if rng.random() < 0.5 else Var(rng.choice(names))
        return Compare(rng.choice(["=", "!=", "<", ">="]), Var(rng.choice(names)), b)
    k = rng.randrange(7 if ints else 5)
    sub = lambda: random_bool(rng, depth - 1, bools, ints, enums)
    if k == 0:
        return Not(sub())
    if k == 1:
        return And(sub(), sub())
    if k == 2:
        return Or(sub(), sub())
    if k == 3:
        return Implies(sub(), sub())
    if k == 4:
        return Compare(rng.choice(["=", "!="]), sub(), sub())        # entre booléens
    if k == 5:
        name = rng.choice(["atLeastOne", "atMostOne", "exactlyOne"])
        return Call(name, [sub() for _ in range(rng.randint(1, 4))])
    args = [Var(x) for x in rng.sample(ints, rng.randint(2, len(ints)))]
    if rng.random() < 0.3:
        args.append(IntLit(rng.randint(1, 4)))
    return Call("allDifferent", args)


def random_model(rng, finite):
    """(texte du modèle, contraintes AST, domaines {nom: valeurs}, codes des valeurs énumérées)."""
    doms, decls = {}, []
    bools = ["b1", "b2", "b3"]
    for b in bools:
        decls.append(f"var {b} : bool;")
        doms[b] = [False, True]
    ints, enums, codes = [], ([], []), {}
    if finite:
        ints = ["x1", "x2", "x3"]
        for x, (lo, hi) in zip(ints, [(1, 3), (1, 3), (2, 4)]):
            decls.append(f"var {x} : {lo}..{hi};")
            doms[x] = list(range(lo, hi + 1))
        decls.append("enum C = { R, G, B };")
        decls.append("var c1 : C; var c2 : C;")
        doms["c1"] = doms["c2"] = [0, 1, 2]
        codes = {"R": 0, "G": 1, "B": 2}
        enums = (["c1", "c2"], list(codes))
    cs = [random_bool(rng, rng.randint(1, 3), bools, ints, enums)
          for _ in range(rng.randint(1, 3))]
    texte = "\n".join(decls) + "\n" + source(Program([Constraint(c) for c in cs]))
    return texte, cs, doms, codes


def valuations(doms):
    names = list(doms)
    for vs in product(*(doms[n] for n in names)):
        yield dict(zip(names, vs))


def satisfait(cs, val, codes):
    return all(eval_ast(c, val, codes) for c in cs)


def valeurs_par_nom(modele, val):
    """Valuation du solveur, indexée par nom de variable (cases sans indice)."""
    return {c.name: val[c] for c in modele.cells}


def check_model(texte, cs, doms, codes, equivalence):
    modele, fnc = compiler(texte)
    solutions = [v for v in valuations(doms) if satisfait(cs, v, codes)]
    sat, v = dpll_h([list(c) for c in fnc.clauses], h4)
    assert sat == bool(solutions), texte                                     # 1.
    if sat:
        vraies = {p for p, b in v.items() if b}
        assert satisfait(cs, valeurs_par_nom(modele, fnc.decoder(vraies)), codes), texte   # 2.
    if equivalence:                                                           # 3.
        cells = {c.name: c for c in modele.cells}
        for val in valuations(doms):
            units = []
            for n, x in val.items():
                c = cells[n]
                units.append([fnc.lits[(c, None)] if x else -fnc.lits[(c, None)]]
                             if doms[n] == [False, True] else [fnc.lits[(c, x)]])
            ok, _ = dpll_h([list(c) for c in fnc.clauses] + units, h4)
            assert ok == satisfait(cs, val, codes), (texte, val)


def test_aleatoire_propositionnel():
    rng = random.Random(1)
    for k in range(300):
        check_model(*random_model(rng, finite=False), equivalence=k < 100)


def test_aleatoire_domaines_finis():
    rng = random.Random(2)
    for k in range(300):
        check_model(*random_model(rng, finite=True), equivalence=k < 15)


# ---------------------------------------------------------------------------
# Tailles des encodages (énoncé, question 4)
# ---------------------------------------------------------------------------

def taille(texte):
    _, fnc = compiler(texte)
    return fnc.nb_vars, len(fnc.clauses), fnc.nb_aux


def test_encodage_direct():
    # var x : 1..3 : x1, x2, x3 et les 4 clauses (x1 ∨ x2 ∨ x3), (¬x1 ∨ ¬x2), (¬x1 ∨ ¬x3), (¬x2 ∨ ¬x3)
    _, fnc = compiler("var x : 1..3;")
    assert fnc.nb_vars == 3 and sorted(map(sorted, fnc.clauses)) == \
        [[-3, -2], [-3, -1], [-2, -1], [1, 2, 3]]
    assert taille("var b : bool;") == (1, 0, 0)


def test_comparaisons():
    base = 2 * 4                                      # x, y : 1..3, 4 clauses chacune
    assert taille("var x : 1..3; var y : 1..3; constraint x = 2;")[1] == base + 1
    assert taille("var x : 1..3; var y : 1..3; constraint x <= 2;")[1] == base + 1   # x1 ∨ x2
    assert taille("var x : 1..3; var y : 1..3; constraint x != y;")[1] == base + 3   # 3 binaires
    assert taille("var x : 1..3; var y : 1..3; constraint x = y;")[1] == base + 3
    assert taille("var x : 1..3; var y : 1..3; constraint x < y;")[1] == base + 3


def test_globales_et_tseitin():
    # atMostOne deux à deux : n(n-1)/2 clauses, aucune variable auxiliaire
    assert taille("array a[6] : bool; constraint atMostOne(a[*]);") == (6, 15, 0)
    assert taille("array a[6] : bool; constraint exactlyOne(a[*]);") == (6, 16, 0)
    # allDifferent de 3 variables 1..3 : 3 valeurs x 3 paires
    assert taille("array h[3] : 1..3; constraint allDifferent(h[*]);") == (9, 12 + 9, 0)
    # une contrainte déjà clause, ou qui s'y ramène, n'introduit pas de variable auxiliaire
    for c in ["a -> b", "not (a and b)", "a or not b or c", "(a and b) -> c"]:
        assert taille(f"var a : bool; var b : bool; var c : bool; constraint {c};") == (3, 1, 0), c
    # conjonction sous une disjonction : une variable auxiliaire
    assert taille("var a : bool; var b : bool; var c : bool; constraint a or (b and c);") == (4, 3, 1)
    # not atMostOne : disjonction de conjonctions, une auxiliaire par paire
    assert taille("array a[3] : bool; constraint not atMostOne(a[*]);")[2] == 3


if __name__ == "__main__":
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print(f"{name}: ok")
