"""Déroulement et simplification (question 3, seconde passe).

derouler(program, table) remplace chaque forall par ses instances et calcule tout ce
qui est connu, pour ne laisser que des contraintes de l'IR (ir.py) sur des cases de
variables, par exemple grid[1][2] != grid[2][2].

L'évaluation est paresseuse, de gauche à droite : dans a and b, a or b et a -> b,
l'opérande droit n'est pas évalué quand l'opérande gauche (connu) suffit. Une
condition sur des valeurs connues filtre donc les instances :

    forall i in 1..N { constraint i < N -> grid[i + 1][1] != grid[i][1]; }

ne lit jamais grid[N + 1][1]. Un accès hors bornes effectivement évalué est une erreur.

Une contrainte qui se simplifie en vrai disparaît ; une contrainte qui se simplifie en
faux est conservée (le modèle est insatisfiable) et donne un avertissement.
"""

from dataclasses import dataclass, field

from ir import Cell, Cmp, Glob, IAnd, IIff, INot, IOr, mk_and, mk_cmp, mk_iff, mk_not, mk_or
from syntax import (Access, And, BinOp, Call, Compare, Constraint, EnumDomain, Forall, Implies,
                    IntLit, Neg, Not, Or, Var, Wildcard, source_expr)
from symboles import (ArraySym, CompileError, ConstArray, ConstInt, EnumType, EnumVal, EnumValue,
                      LoopIndex, VarSym, show_value)


@dataclass
class Modele:
    """Résultat de la question 3 : variables (cases) et contraintes sans boucle."""
    cells: list                      # toutes les cases de variables, dans l'ordre de déclaration
    doms: dict                       # Cell -> ir.Dom
    contraintes: list = field(default_factory=list)       # formules de l'IR (ou False)
    avertissements: list = field(default_factory=list)


def derouler(program, table):
    cells, doms = [], {}
    for name, sym in table.variables():
        if isinstance(sym, VarSym):
            idxs = [()]
        else:
            idxs = [()]
            for d in sym.dims:
                idxs = [i + (v,) for i in idxs for v in d.values]
        for idx in idxs:
            c = Cell(name, idx)
            cells.append(c)
            doms[c] = sym.dom
    m = Modele(cells, doms)
    ev = Evaluateur(table, doms)
    for s in program.statements:
        if isinstance(s, (Constraint, Forall)):
            ev.statement(s, {}, m)
    return m


def is_formula(x, doms):
    """x est une valeur booléenne (connue ou non), par opposition à un terme entier/énuméré."""
    if isinstance(x, bool):
        return True
    if isinstance(x, Cell):
        return doms[x].kind == "bool"
    return isinstance(x, (INot, IAnd, IOr, IIff, Cmp, Glob))


def code(v):
    """Code entier d'une valeur connue (rang pour une valeur énumérée)."""
    return v.index if isinstance(v, EnumVal) else v


class Evaluateur:
    """valeur(e, env) : valeur connue (int, bool, EnumVal) ou terme/formule de l'IR.

    env associe aux indices de boucle leur valeur courante. Les types ont déjà été
    vérifiés par analyse.py : seules les erreurs qui dépendent des valeurs restent
    possibles (indice hors bornes).
    """

    def __init__(self, table, doms):
        self.table, self.doms = table, doms

    # ---------------------------------------------------------------- instructions

    def statement(self, s, env, m):
        if isinstance(s, Constraint):
            try:
                r = self.valeur(s.expr, env)
            except CompileError as err:
                raise CompileError(f"{err}{contexte(env)}") from None
            if r is True:
                return
            if r is False:
                m.avertissements.append(f"contrainte toujours fausse : "
                                        f"'{source_expr(s.expr)}'{contexte(env)}")
            m.contraintes.append(r)
        else:
            self.forall(s.iterators, s.body, env, m)

    def forall(self, iterators, body, env, m):
        if not iterators:
            for b in body:
                self.statement(b, env, m)
            return
        (name, d), rest = iterators[0], iterators[1:]
        for v in self.domain_values(d, env):
            env2 = dict(env)
            env2[name] = v
            self.forall(rest, body, env2, m)

    def domain_values(self, d, env):
        if isinstance(d, EnumDomain):
            if d.name == "bool":
                return [False, True]
            return list(self.table.symbols[d.name].values)
        return range(self.valeur(d.lo, env), self.valeur(d.hi, env) + 1)

    # ---------------------------------------------------------------- expressions

    def valeur(self, e, env=None):
        env = env or {}
        if isinstance(e, IntLit):
            return e.value

        if isinstance(e, Var):
            if e.name in env:
                return env[e.name]
            sym = self.table.symbols[e.name]
            if isinstance(sym, ConstInt):
                return sym.value
            if isinstance(sym, EnumValue):
                return sym.value
            if isinstance(sym, VarSym):
                return Cell(e.name, ())
            raise CompileError(f"'{e.name}' n'a pas de valeur")

        if isinstance(e, Access):
            sym = self.table.symbols[e.name]
            idx = tuple(self.index(e, k, i, d, env)
                        for k, (i, d) in enumerate(zip(e.indices, sym.dims), 1))
            if isinstance(sym, ConstArray):
                return sym.data[idx]
            return Cell(e.name, idx)

        if isinstance(e, BinOp):
            a, b = self.valeur(e.left, env), self.valeur(e.right, env)
            return {"+": a + b, "-": a - b, "*": a * b}[e.op]
        if isinstance(e, Neg):
            return -self.valeur(e.expr, env)

        # connecteurs : évaluation paresseuse de gauche à droite
        if isinstance(e, Not):
            return mk_not(self.valeur(e.expr, env))
        if isinstance(e, And):
            a = self.valeur(e.left, env)
            if a is False:
                return False
            return mk_and([a, self.valeur(e.right, env)])
        if isinstance(e, Or):
            a = self.valeur(e.left, env)
            if a is True:
                return True
            return mk_or([a, self.valeur(e.right, env)])
        if isinstance(e, Implies):
            a = self.valeur(e.left, env)
            if a is False:
                return True
            return mk_or([mk_not(a), self.valeur(e.right, env)])

        if isinstance(e, Compare):
            a, b = self.valeur(e.left, env), self.valeur(e.right, env)
            if is_formula(a, self.doms) or is_formula(b, self.doms):
                r = mk_iff(a, b)
                return r if e.op == "=" else mk_not(r)
            x = a if isinstance(a, Cell) else code(a)     # entiers et valeurs énumérées :
            y = b if isinstance(b, Cell) else code(b)     # comparaison des codes
            return mk_cmp(e.op, x, y)

        if isinstance(e, Call):
            if e.name == "abs":
                return abs(self.valeur(e.args[0], env))
            items = []
            for a in e.args:
                items.extend(self.arg_values(a, env))
            return self.globale(e.name, items)

        raise CompileError(f"expression inattendue {e!r}")

    def index(self, e, k, i, d, env):
        v = self.valeur(i, env)
        if v not in d.values:
            raise CompileError(f"l'indice {k} de '{e.name}' vaut {show_value(v)}, "
                               f"hors de {d.text} (dans '{source_expr(e)}')")
        return v

    def arg_values(self, a, env):
        """Valeurs d'un argument de contrainte globale ; une tranche donne plusieurs cases."""
        if not (isinstance(a, Access) and any(isinstance(i, Wildcard) for i in a.indices)):
            return [self.valeur(a, env)]
        sym = self.table.symbols[a.name]
        idxs = [()]
        for k, (i, d) in enumerate(zip(a.indices, sym.dims), 1):
            vs = d.values if isinstance(i, Wildcard) else [self.index(a, k, i, d, env)]
            idxs = [x + (v,) for x in idxs for v in vs]           # ordre ligne par ligne
        if isinstance(sym, ConstArray):
            return [sym.data[x] for x in idxs]
        return [Cell(a.name, x) for x in idxs]

    def globale(self, name, items):
        if name == "allDifferent":
            known = [code(x) for x in items if not isinstance(x, Cell)]
            cells = [x for x in items if isinstance(x, Cell)]
            if len(set(known)) < len(known) or len(set(cells)) < len(cells):
                return False                      # deux fois la même valeur, ou la même case
            parts = [mk_cmp("!=", c, k) for c in cells for k in sorted(set(known))]
            if len(cells) >= 2:
                parts.append(Glob("allDifferent", tuple(cells)))
            return mk_and(parts)
        vrais = sum(1 for x in items if x is True)
        reste = [x for x in items if not isinstance(x, bool)]
        if name == "atLeastOne":
            return True if vrais else mk_or(reste)
        if vrais >= 2:                            # atMostOne, exactlyOne
            return False
        if vrais == 1:
            return mk_and([mk_not(x) for x in reste])
        if name == "atMostOne":
            return True if len(reste) <= 1 else Glob(name, tuple(reste))
        # exactlyOne sans argument vrai
        if not reste:
            return False
        return reste[0] if len(reste) == 1 else Glob(name, tuple(reste))


def contexte(env):
    if not env:
        return ""
    return " (pour " + ", ".join(f"{k} = {show_value(v)}" for k, v in env.items()) + ")"
