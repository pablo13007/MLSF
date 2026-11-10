"""Traduction en FNC (questions 1 et 4).

1. Encodage direct des domaines (question 4). Une variable x de domaine {v1, ..., vk}
   devient k variables booléennes x_v (x_v vraie ssi x vaut v), avec les clauses
   « exactement une » : x_v1 ∨ ... ∨ x_vk, et ¬x_vi ∨ ¬x_vj pour i < j.
   Une variable bool reste une variable booléenne.

2. Chaque contrainte de l'IR devient une formule propositionnelle en forme normale
   négative (FNN), sur les littéraux DIMACS (to_prop). La polarité est propagée vers
   le bas : une comparaison ou une contrainte globale sous une négation est traduite
   directement sous sa forme niée.

   Comparaisons (x, y variables ; c valeur ; D(x) domaine de x) :
       x = c     x_c                         x != c    ¬x_c
       x <= c    ∨_{v ∈ D(x), v <= c} x_v    x >= c    ∨_{v ∈ D(x), v >= c} x_v
       x = y     ∧_{v ∈ D(x)} (¬x_v ∨ y_v)   (¬x_v si v ∉ D(y))
       x != y    ∧_{v ∈ D(x) ∩ D(y)} (¬x_v ∨ ¬y_v)
       x < y     ∧_{v ∈ D(x)} (¬x_v ∨ ∨_{w ∈ D(y), w > v} y_w)
       x <= y    idem avec w >= v
   Toutes ces traductions reposent sur les clauses « exactement une » des domaines.

   Contraintes globales (encodage deux à deux, sans variable auxiliaire) :
       atLeastOne(l1..ln)   l1 ∨ ... ∨ ln
       atMostOne(l1..ln)    ∧_{i<j} (¬li ∨ ¬lj)
       exactlyOne           les deux
       allDifferent(e1..en) pour chaque valeur v : atMostOne(e1 = v, ..., en = v)

3. Mise en FNC de la formule FNN (question 1) : transformation de Tseitin, sous la
   forme de Plaisted et Greenbaum. Une conjonction au sommet donne une clause par
   conjoint ; une disjonction de littéraux est déjà une clause ; seule une conjonction
   imbriquée dans une disjonction reçoit une variable auxiliaire a, avec les clauses
   a -> conjoint. Dans une FNN, toute sous-formule apparaît positivement : l'implication
   a -> φ suffit (l'équivalence de Tseitin n'est pas nécessaire), ce qui divise par deux
   le nombre de clauses de définition. Une même sous-formule n'est définie qu'une fois.

Formules propositionnelles : int (littéral DIMACS), ("and", (...)), ("or", (...)), True, False.
"""

from itertools import combinations

from ir import Cell, Cmp, Glob, IAnd, IIff, INot, IOr, mk_not


# ---------------------------------------------------------------------------
# Formules propositionnelles en FNN
# ---------------------------------------------------------------------------

def p_and(xs):
    out, seen = [], set()
    for x in xs:
        if x is False:
            return False
        if x is True:
            continue
        for y in (x[1] if isinstance(x, tuple) and x[0] == "and" else (x,)):
            if isinstance(y, int) and -y in seen:
                return False                      # l ∧ ¬l
            if y not in seen:
                seen.add(y)
                out.append(y)
    if not out:
        return True
    return out[0] if len(out) == 1 else ("and", tuple(out))


def p_or(xs):
    out, seen = [], set()
    for x in xs:
        if x is True:
            return True
        if x is False:
            continue
        for y in (x[1] if isinstance(x, tuple) and x[0] == "or" else (x,)):
            if isinstance(y, int) and -y in seen:
                return True                       # l ∨ ¬l
            if y not in seen:
                seen.add(y)
                out.append(y)
    if not out:
        return False
    return out[0] if len(out) == 1 else ("or", tuple(out))


def p_not(p):
    """Négation d'une formule FNN (De Morgan) : le résultat est encore en FNN."""
    if isinstance(p, bool):
        return not p
    if isinstance(p, int):
        return -p
    op, xs = p
    return (p_or if op == "and" else p_and)([p_not(x) for x in xs])


# ---------------------------------------------------------------------------
# Traduction
# ---------------------------------------------------------------------------

class FNC:
    """FNC d'un modèle déroulé (deroulement.Modele)."""

    def __init__(self, modele):
        self.modele = modele
        self.doms = modele.doms
        self.nb_vars = 0
        self.clauses = []
        self._vues = set()
        self.lits = {}                # (Cell, code) -> numéro ; (Cell, None) pour un booléen
        self.noms = []                # (numéro, texte) des variables nommées
        self._definitions = {}        # sous-formule -> variable auxiliaire
        self.nb_aux = 0
        for c in modele.cells:
            self.encoder_domaine(c)
        for f in modele.contraintes:
            self.ajouter(f)

    def nouvelle(self):
        self.nb_vars += 1
        return self.nb_vars

    def clause(self, lits):
        cle = tuple(sorted(set(lits)))
        if any(-l in cle for l in cle):           # tautologie
            return
        if cle not in self._vues:
            self._vues.add(cle)
            self.clauses.append(list(dict.fromkeys(lits)))

    # ------------------------------------------------ encodage direct des domaines

    def encoder_domaine(self, c):
        dom = self.doms[c]
        if dom.kind == "bool":
            n = self.nouvelle()
            self.lits[(c, None)] = n
            self.noms.append((n, str(c)))
            return
        xs = []
        for v in dom.values:
            n = self.nouvelle()
            self.lits[(c, v)] = n
            self.noms.append((n, f"{c} = {dom.show(v)}"))
            xs.append(n)
        self.clause(xs)                                    # au moins une valeur
        for a, b in combinations(xs, 2):                   # au plus une valeur
            self.clause([-a, -b])

    def x(self, c, v):
        """Littéral x_v de la case c ; False si v n'est pas dans son domaine."""
        return self.lits.get((c, v), False)

    # ------------------------------------------------ IR -> FNN

    def to_prop(self, e, pol=True):
        """Formule FNN équivalente à e (pol=True) ou à not e (pol=False)."""
        if isinstance(e, bool):
            return e == pol
        if isinstance(e, Cell):
            n = self.lits[(e, None)]
            return n if pol else -n
        if isinstance(e, INot):
            return self.to_prop(e.e, not pol)
        if isinstance(e, (IAnd, IOr)):
            conj = isinstance(e, IAnd) == pol
            return (p_and if conj else p_or)([self.to_prop(x, pol) for x in e.es])
        if isinstance(e, IIff):
            a, b = self.to_prop(e.a), self.to_prop(e.b)
            if pol:          # (¬a ∨ b) ∧ (a ∨ ¬b)
                return p_and([p_or([p_not(a), b]), p_or([a, p_not(b)])])
            return p_and([p_or([a, b]), p_or([p_not(a), p_not(b)])])      # a xor b
        if isinstance(e, Cmp):
            if not pol:
                return self.to_prop(mk_not(e, self.doms))  # x = y niée devient x != y, etc.
            return self.comparaison(e)
        if isinstance(e, Glob):
            p = self.globale(e)
            return p if pol else p_not(p)
        raise TypeError(f"to_prop : nœud inattendu {e!r}")

    def comparaison(self, e):
        op, x, y = e.op, e.x, e.y
        dx = self.doms[x].values
        if not isinstance(y, Cell):                        # variable-valeur
            if op == "=":
                return self.x(x, y)
            if op == "!=":
                return p_not(self.x(x, y))
            ok = [v for v in dx if (v <= y if op == "<=" else v >= y)]
            return p_or([self.x(x, v) for v in ok])
        dy = self.doms[y].values                           # variable-variable
        if op == "=":
            return p_and([p_or([-self.x(x, v), self.x(y, v)]) for v in dx])
        if op == "!=":
            return p_and([p_or([-self.x(x, v), -self.x(y, v)]) for v in dx if v in dy])
        strict = op == "<"
        return p_and([p_or([-self.x(x, v)] + [self.x(y, w) for w in dy if (w > v if strict else w >= v)])
                      for v in dx])

    def globale(self, e):
        if e.name == "allDifferent":
            valeurs = sorted({v for c in e.args for v in self.doms[c].values})
            return p_and([self.au_plus_un([self.x(c, v) for c in e.args]) for v in valeurs])
        ls = [self.to_prop(a) for a in e.args]
        if e.name == "atLeastOne":
            return p_or(ls)
        if e.name == "atMostOne":
            return self.au_plus_un(ls)
        return p_and([p_or(ls), self.au_plus_un(ls)])      # exactlyOne

    @staticmethod
    def au_plus_un(ls):
        """Encodage deux à deux : n(n-1)/2 clauses ¬li ∨ ¬lj, aucune variable auxiliaire."""
        ls = [l for l in ls if l is not False]
        return p_and([p_or([p_not(a), p_not(b)]) for a, b in combinations(ls, 2)])

    # ------------------------------------------------ FNN -> FNC (Tseitin / Plaisted-Greenbaum)

    def ajouter(self, f):
        p = self.to_prop(f)
        if p is True:
            return
        if p is False:
            self.clauses.append([])                         # contrainte fausse : clause vide
            return
        for conj in (p[1] if isinstance(p, tuple) and p[0] == "and" else (p,)):
            self.clause(self.en_clause(conj))

    def en_clause(self, p):
        """Littéraux d'une clause équivalente (à définitions près) à p, un littéral ou un "or"."""
        if isinstance(p, int):
            return [p]
        if p[0] == "and":
            return [self.definir(p)]
        return [l if isinstance(l, int) else self.definir(l) for l in p[1]]

    def definir(self, p):
        """Variable auxiliaire a pour la conjonction p, avec les clauses a -> conjoint."""
        if p not in self._definitions:
            a = self.nouvelle()
            self.nb_aux += 1
            self._definitions[p] = a
            for conj in p[1]:
                self.clause([-a] + self.en_clause(conj))
        return self._definitions[p]

    # ------------------------------------------------ DIMACS et décodage

    def dimacs(self, commentaires=()):
        lignes = [f"c {c}" for c in commentaires]
        lignes += [f"c var {n} {nom}" for n, nom in self.noms]
        lignes.append(f"p cnf {self.nb_vars} {len(self.clauses)}")
        lignes += [" ".join(map(str, c + [0])) for c in self.clauses]
        return "\n".join(lignes) + "\n"

    def decoder(self, vraies):
        """Valeur de chaque case (bool, ou code de valeur) à partir des variables vraies."""
        val = {}
        for c in self.modele.cells:
            dom = self.doms[c]
            if dom.kind == "bool":
                val[c] = self.lits[(c, None)] in vraies
            else:
                vs = [v for v in dom.values if self.lits[(c, v)] in vraies]
                if len(vs) != 1:
                    raise ValueError(f"{c} : {len(vs)} valeurs vraies dans le modèle")
                val[c] = vs[0]
        return val
