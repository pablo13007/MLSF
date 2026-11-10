"""Analyse sémantique (question 3, première passe).

analyser(program) parcourt les instructions dans l'ordre du texte :
  - une déclaration est vérifiée, ses valeurs connues (tailles, bornes, données) sont
    calculées, puis le nom est ajouté à la table des symboles ;
  - une contrainte (éventuellement dans des forall) est vérifiée sans être déroulée :
    noms déclarés, types, nombre d'indices, valeurs connues là où elles sont exigées,
    tranches seulement en argument d'une contrainte globale, arguments des fonctions.

Ces vérifications sont statiques : elles portent sur le texte de la contrainte, une
seule fois, quelle que soit la valeur des indices de boucle. Une erreur de type est
donc signalée même dans une partie qu'un filtre (i < N -> ...) rendrait inutile.
Seuls les indices hors bornes, qui dépendent des valeurs, sont détectés au
déroulement (deroulement.py), en respectant le court-circuit.

typer(e) renvoie (type, connue, tranche) :
    type     INT, BOOL ou enum T
    connue   la valeur est fixée à la compilation
    tranche  e est une tranche t[..][*] (permise seulement en argument d'une contrainte globale)
"""

from ir import Dom
from syntax import (Access, And, ArrayDecl, BinOp, Call, Compare, ConstArrayDecl, ConstDecl,
                    Constraint, EnumDecl, EnumDomain, Forall, Implies, IntLit, Neg, Not, Or,
                    RangeDomain, Var, VarDecl, Wildcard, source_expr)
from symboles import (BOOL, INT, ArraySym, CompileError, ConstArray, ConstInt, Dim, EnumType,
                      EnumVal, EnumValue, LoopIndex, Table, VarSym, enum_type, type_name)

BOOL_GLOBALS = {"atLeastOne", "atMostOne", "exactlyOne"}
VALUE_GLOBALS = {"allDifferent"}
GLOBALS = BOOL_GLOBALS | VALUE_GLOBALS


def analyser(program):
    """Vérifie le modèle et construit sa table des symboles ; lève CompileError."""
    a = Analyseur()
    for s in program.statements:
        a.statement(s, {})
    return a.table


class Analyseur:

    def __init__(self):
        self.table = Table()
        # évaluation des valeurs connues des déclarations (import tardif : deroulement
        # importe lui-même ce module)
        from deroulement import Evaluateur
        self.ev = Evaluateur(self.table, {})

    # ---------------------------------------------------------------- instructions

    def statement(self, s, scope):
        if isinstance(s, ConstDecl):
            self.const_int(s)
        elif isinstance(s, ConstArrayDecl):
            self.const_array(s)
        elif isinstance(s, EnumDecl):
            t = EnumType(s.name, [EnumVal(enum_type(s.name), k, v) for k, v in enumerate(s.values)])
            self.table.declare(s.name, t)
            for v in t.values:
                self.table.declare(v.name, EnumValue(v))
        elif isinstance(s, VarDecl):
            dom, t = self.domain(s.domain, s.name)
            self.table.declare(s.name, VarSym(dom, t))
        elif isinstance(s, ArrayDecl):
            dims = [self.dim(d, s.name, k + 1) for k, d in enumerate(s.dims)]
            dom, t = self.domain(s.domain, s.name)
            self.table.declare(s.name, ArraySym(dims, dom, t))
        elif isinstance(s, Constraint):
            t, _, _ = self.typer(s.expr, scope)
            if t != BOOL:
                raise CompileError(f"la contrainte '{source_expr(s.expr)}' est {type_name(t)}, "
                                   "pas un booléen")
        elif isinstance(s, Forall):
            inner = dict(scope)
            for name, d in s.iterators:
                t = self.iterator_type(d, inner, name)
                self.table_free(name, inner)
                inner[name] = LoopIndex(t)
            for b in s.body:
                self.statement(b, inner)
        else:
            raise CompileError(f"instruction inattendue {s!r}")

    def table_free(self, name, scope):
        if name in self.table.symbols or name in scope:
            raise CompileError(f"'{name}' est déjà déclaré")

    def const_int(self, s):
        t, known, _ = self.typer(s.expr, {})
        if t != INT or not known:
            raise CompileError(f"la constante '{s.name}' doit être un entier connu")
        self.table.declare(s.name, ConstInt(self.ev.valeur(s.expr)))

    def const_array(self, s):
        dims = [self.dim(d, s.name, k + 1) for k, d in enumerate(s.dims)]
        data, types = {}, set()

        def remplir(values, k, idx):
            if not isinstance(values, list) or len(values) != len(dims[k].values):
                raise CompileError(f"les données de '{s.name}' n'ont pas la forme "
                                   + "".join(f"[{d.text}]" for d in dims)
                                   + f" (dimension {k + 1})")
            for i, v in zip(dims[k].values, values):
                if k + 1 < len(dims):
                    remplir(v, k + 1, idx + (i,))
                else:
                    if isinstance(v, list):
                        raise CompileError(f"les données de '{s.name}' ont trop de dimensions")
                    t, known, _ = self.typer(v, {})
                    if not known or t == BOOL:
                        raise CompileError(f"les cases de '{s.name}' doivent être des entiers "
                                           "ou des valeurs énumérées connus")
                    types.add(t)
                    data[idx + (i,)] = self.ev.valeur(v)

        remplir(s.values, 0, ())
        if len(types) > 1:
            raise CompileError(f"les cases de '{s.name}' mélangent plusieurs types")
        elem = types.pop() if types else INT
        self.table.declare(s.name, ConstArray(dims, data, elem))

    def dim(self, e, name, k):
        """Dimension k du tableau name : un type énuméré ou une taille connue >= 1."""
        if isinstance(e, Var) and isinstance(self.table.symbols.get(e.name), EnumType):
            t = self.table.symbols[e.name]
            return Dim(enum_type(t.name), list(t.values), t.name)
        t, known, _ = self.typer(e, {})
        if t != INT or not known:
            raise CompileError(f"la dimension {k} de '{name}' doit être un entier connu "
                               "ou un type énuméré")
        n = self.ev.valeur(e)
        if n < 1:
            raise CompileError(f"la dimension {k} de '{name}' vaut {n} : elle doit être >= 1")
        return Dim(INT, list(range(1, n + 1)), f"1..{n}")

    def domain(self, d, name):
        """Domaine d'une variable : (ir.Dom, type)."""
        if isinstance(d, EnumDomain):
            if d.name == "bool":
                return Dom("bool", (0, 1)), BOOL
            sym = self.table.lookup(d.name)
            if not isinstance(sym, EnumType):
                raise CompileError(f"'{d.name}' n'est pas un type énuméré (domaine de '{name}')")
            return (Dom("enum", tuple(range(len(sym.values))), sym.name,
                        tuple(v.name for v in sym.values)), enum_type(sym.name))
        self.check_bounds(d, {}, f"domaine de '{name}'")
        lo, hi = self.ev.valeur(d.lo), self.ev.valeur(d.hi)
        if lo > hi:
            raise CompileError(f"le domaine {lo}..{hi} de '{name}' est vide")
        return Dom("int", tuple(range(lo, hi + 1))), INT

    def check_bounds(self, d, scope, what):
        for b in (d.lo, d.hi):
            t, known, _ = self.typer(b, scope)
            if t != INT or not known:
                raise CompileError(f"les bornes du {what} doivent être des entiers connus")

    def iterator_type(self, d, scope, name):
        if isinstance(d, EnumDomain):
            if d.name == "bool":
                return BOOL
            sym = self.table.lookup(d.name, scope)
            if not isinstance(sym, EnumType):
                raise CompileError(f"'{d.name}' n'est pas un type énuméré (boucle sur '{name}')")
            return enum_type(sym.name)
        self.check_bounds(d, scope, f"forall sur '{name}'")
        return INT

    # ---------------------------------------------------------------- expressions

    def typer(self, e, scope, slice_ok=False):
        if isinstance(e, IntLit):
            return INT, True, False

        if isinstance(e, Var):
            sym = self.table.lookup(e.name, scope)
            if isinstance(sym, LoopIndex):
                return sym.type, True, False
            if isinstance(sym, ConstInt):
                return INT, True, False
            if isinstance(sym, EnumValue):
                return sym.value.type, True, False
            if isinstance(sym, VarSym):
                return sym.type, False, False
            if isinstance(sym, EnumType):
                raise CompileError(f"'{e.name}' est un type, pas une valeur")
            k = len(sym.dims)
            raise CompileError(f"'{e.name}' est un tableau à {k} dimension(s) : "
                               f"il faut {k} indice(s)")

        if isinstance(e, Access):
            return self.access(e, scope, slice_ok)

        if isinstance(e, (BinOp, Neg)):
            for x in ((e.left, e.right) if isinstance(e, BinOp) else (e.expr,)):
                t, known, _ = self.typer(x, scope)
                if t != INT:
                    raise CompileError(f"arithmétique sur {type_name(t)} : '{source_expr(x)}'")
                if not known:
                    raise CompileError(f"arithmétique sur une valeur inconnue : '{source_expr(x)}' "
                                       "(seules les valeurs connues à la compilation se calculent)")
            return INT, True, False

        if isinstance(e, Compare):
            lt, lk, _ = self.typer(e.left, scope)
            rt, rk, _ = self.typer(e.right, scope)
            if lt != rt:
                raise CompileError(f"comparaison entre {type_name(lt)} et {type_name(rt)} : "
                                   f"'{source_expr(e)}'")
            if lt == BOOL and e.op not in ("=", "!="):
                raise CompileError(f"seules = et != s'appliquent aux booléens : '{source_expr(e)}'")
            return BOOL, lk and rk, False

        if isinstance(e, (And, Or, Implies, Not)):
            op = {And: "and", Or: "or", Implies: "->", Not: "not"}[type(e)]
            known = True
            for x in ((e.expr,) if isinstance(e, Not) else (e.left, e.right)):
                t, k, _ = self.typer(x, scope)
                if t != BOOL:
                    raise CompileError(f"'{op}' attend des booléens, pas {type_name(t)} : "
                                       f"'{source_expr(x)}'")
                known = known and k
            return BOOL, known, False

        if isinstance(e, Call):
            return self.call(e, scope)

        raise CompileError(f"expression inattendue {e!r}")

    def access(self, e, scope, slice_ok):
        sym = self.table.lookup(e.name, scope)
        if not isinstance(sym, (ConstArray, ArraySym)):
            raise CompileError(f"'{e.name}' n'est pas un tableau")
        if len(e.indices) != len(sym.dims):
            raise CompileError(f"'{e.name}' a {len(sym.dims)} dimension(s), "
                               f"mais {len(e.indices)} indice(s) dans '{source_expr(e)}'")
        is_slice = False
        for k, (i, d) in enumerate(zip(e.indices, sym.dims), 1):
            if isinstance(i, Wildcard):
                if not slice_ok:
                    raise CompileError(f"tranche '{source_expr(e)}' : une tranche n'est permise "
                                       "qu'en argument d'une contrainte globale")
                is_slice = True
                continue
            t, known, _ = self.typer(i, scope)
            if not known:
                raise CompileError(f"l'indice {k} de '{source_expr(e)}' doit être une valeur connue")
            if t != d.type:
                raise CompileError(f"l'indice {k} de '{source_expr(e)}' doit être "
                                   f"{type_name(d.type)}, pas {type_name(t)}")
        if isinstance(sym, ConstArray):
            return sym.elem, not is_slice, is_slice
        return sym.type, False, is_slice

    def call(self, e, scope):
        if e.name == "abs":
            if len(e.args) != 1:
                raise CompileError(f"abs attend 1 argument, pas {len(e.args)}")
            t, known, _ = self.typer(e.args[0], scope)
            if t != INT or not known:
                raise CompileError(f"abs attend un entier connu : '{source_expr(e)}'")
            return INT, True, False
        if e.name not in GLOBALS:
            if e.name in self.table.symbols or e.name in scope:
                raise CompileError(f"'{e.name}' n'est pas une fonction")
            raise CompileError(f"fonction inconnue '{e.name}' (fonctions : abs, "
                               + ", ".join(sorted(GLOBALS)) + ")")
        if not e.args:
            raise CompileError(f"{e.name} attend au moins un argument")
        types, known = set(), True
        for a in e.args:
            t, k, _ = self.typer(a, scope, slice_ok=True)
            if e.name in BOOL_GLOBALS and t != BOOL:
                raise CompileError(f"{e.name} attend des booléens, pas {type_name(t)} : "
                                   f"'{source_expr(a)}'")
            if e.name in VALUE_GLOBALS and t == BOOL:
                raise CompileError(f"{e.name} attend des entiers ou des valeurs énumérées, "
                                   f"pas des booléens : '{source_expr(a)}'")
            types.add(t)
            known = known and k
        if len(types) > 1:
            raise CompileError(f"{e.name} : arguments de types différents")
        return BOOL, known, False
