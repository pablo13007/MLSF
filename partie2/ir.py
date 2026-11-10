"""Représentation intermédiaire (IR) : résultat de la question 3, entrée de la question 4.

Après déroulement et simplification, une contrainte ne porte plus que sur des cases
de variables (Cell) et des valeurs connues. Elle est construite avec :

    Cell(name, idx)       une variable du modèle : x -> Cell("x", ()), grid[1][2] -> Cell("grid", (1, 2))
                          (utilisée directement comme formule si la variable est booléenne)
    INot(e), IAnd(es), IOr(es), IIff(a, b)
    Cmp(op, x, y)         x est une Cell entière ou énumérée ; y une Cell ou une valeur (int)
                          variable-valeur    : op parmi =  !=  <=  >=
                          variable-variable  : op parmi =  !=  <   <=
    Glob(name, args)      atLeastOne / atMostOne / exactlyOne (args : formules),
                          allDifferent (args : Cell entières ou énumérées, au moins deux)

Les valeurs énumérées sont numérotées 0, 1, ... dans l'ordre de déclaration
(code entier) ; les comparaisons portent sur ces codes.

Les constructeurs mk_* simplifient au passage : constantes True/False absorbées,
négation poussée jusqu'aux feuilles (De Morgan, not (x = 2) devient x != 2),
comparaisons normalisées (x > y devient y < x, x < 3 devient x <= 2).
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Dom:
    """Domaine d'une variable : kind parmi "bool", "int", "enum" ; values : codes (int)."""
    kind: str
    values: tuple
    enum: str = None            # nom du type énuméré
    labels: tuple = None        # noms des valeurs énumérées (labels[code])

    def show(self, v):
        if self.kind == "bool":
            return "true" if v else "false"
        if self.kind == "enum":
            return self.labels[v]
        return str(v)


@dataclass(frozen=True)
class Cell:
    name: str
    idx: tuple                  # indices : entiers ou valeurs énumérées

    def __str__(self):
        return self.name + "".join(f"[{v}]" for v in self.idx)


@dataclass(frozen=True)
class INot:
    e: object

@dataclass(frozen=True)
class IAnd:
    es: tuple

@dataclass(frozen=True)
class IOr:
    es: tuple

@dataclass(frozen=True)
class IIff:
    a: object
    b: object

@dataclass(frozen=True)
class Cmp:
    op: str
    x: Cell
    y: object

@dataclass(frozen=True)
class Glob:
    name: str
    args: tuple


# ---------------------------------------------------------------------------
# Constructeurs simplificateurs
# ---------------------------------------------------------------------------
def mk_not(e):
    if isinstance(e, bool):
        return not e
    if isinstance(e, INot):
        return e.e
    if isinstance(e, Cmp):
        if isinstance(e.y, Cell):
            return _neg_var_var(e)
        return mk_cmp(NEGATION[e.op], e.x, e.y)
    if isinstance(e, IAnd):                           # De Morgan : la négation descend
        return mk_or([mk_not(x) for x in e.es])
    if isinstance(e, IOr):
        return mk_and([mk_not(x) for x in e.es])
    return INot(e)                                    # variable booléenne, IIff ou Glob

NEGATION = {"=": "!=", "!=": "=", "<=": ">", ">=": "<", "<": ">=", ">": "<="}


def _neg_var_var(e):
    # not (x = y) : x != y ; not (x < y) : y <= x ; not (x <= y) : y < x
    if e.op in ("=", "!="):
        return mk_cmp(NEGATION[e.op], e.x, e.y)
    return mk_cmp("<=" if e.op == "<" else "<", e.y, e.x)


def mk_and(es):
    out = []
    for e in es:
        if e is False:
            return False
        if e is True:
            continue
        out.extend(e.es if isinstance(e, IAnd) else [e])
    if not out:
        return True
    return out[0] if len(out) == 1 else IAnd(tuple(out))


def mk_or(es):
    out = []
    for e in es:
        if e is True:
            return True
        if e is False:
            continue
        out.extend(e.es if isinstance(e, IOr) else [e])
    if not out:
        return False
    return out[0] if len(out) == 1 else IOr(tuple(out))


def mk_iff(a, b):
    """a = b entre deux expressions booléennes."""
    if isinstance(a, bool) and isinstance(b, bool):
        return a == b
    if isinstance(a, bool):
        a, b = b, a
    if isinstance(b, bool):
        return a if b else mk_not(a)
    return IIff(a, b)


def compare_values(op, a, b):
    return {"=": a == b, "!=": a != b, "<": a < b, "<=": a <= b,
            ">": a > b, ">=": a >= b}[op]


FLIP = {"=": "=", "!=": "!=", "<": ">", "<=": ">=", ">": "<", ">=": "<="}


def mk_cmp(op, a, b):
    """Comparaison entre deux termes entiers ou énumérés : valeur connue (int) ou Cell."""
    if not isinstance(a, Cell) and not isinstance(b, Cell):
        return compare_values(op, a, b)
    if not isinstance(a, Cell):                       # c op x  ->  x op' c
        a, b, op = b, a, FLIP[op]
    if isinstance(b, Cell):
        if op in (">", ">="):                         # x > y  ->  y < x
            a, b, op = b, a, FLIP[op]
        return Cmp(op, a, b)
    if op == "<":                                     # variable-valeur : x < c  ->  x <= c-1
        op, b = "<=", b - 1
    elif op == ">":                                   # x > c  ->  x >= c+1
        op, b = ">=", b + 1
    return Cmp(op, a, b)


# ---------------------------------------------------------------------------
# Évaluation (vérification des solutions, tests)
# ---------------------------------------------------------------------------

def evaluer(e, val):
    """Valeur de vérité de la formule e pour la valuation val : Cell -> bool ou code."""
    if isinstance(e, bool):
        return e
    if isinstance(e, Cell):
        return bool(val[e])
    if isinstance(e, INot):
        return not evaluer(e.e, val)
    if isinstance(e, IAnd):
        return all(evaluer(x, val) for x in e.es)
    if isinstance(e, IOr):
        return any(evaluer(x, val) for x in e.es)
    if isinstance(e, IIff):
        return evaluer(e.a, val) == evaluer(e.b, val)
    if isinstance(e, Cmp):
        y = val[e.y] if isinstance(e.y, Cell) else e.y
        return compare_values(e.op, val[e.x], y)
    if isinstance(e, Glob):
        if e.name == "allDifferent":
            vs = [val[x] for x in e.args]
            return len(set(vs)) == len(vs)
        n = sum(evaluer(x, val) for x in e.args)
        return {"atLeastOne": n >= 1, "atMostOne": n <= 1, "exactlyOne": n == 1}[e.name]
    raise TypeError(f"evaluer : nœud inattendu {e!r}")


def montrer(e):
    """Texte lisible d'une formule de l'IR (messages, tests)."""
    if isinstance(e, bool):
        return "true" if e else "false"
    if isinstance(e, Cell):
        return str(e)
    if isinstance(e, INot):
        return f"not {montrer(e.e)}"
    if isinstance(e, IAnd):
        return "(" + " and ".join(montrer(x) for x in e.es) + ")"
    if isinstance(e, IOr):
        return "(" + " or ".join(montrer(x) for x in e.es) + ")"
    if isinstance(e, IIff):
        return f"({montrer(e.a)} = {montrer(e.b)})"
    if isinstance(e, Cmp):
        return f"{e.x} {e.op} {e.y}"
    if isinstance(e, Glob):
        return f"{e.name}(" + ", ".join(montrer(x) for x in e.args) + ")"
    return str(e)
