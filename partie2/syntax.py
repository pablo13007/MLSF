r"""Syntaxe du langage de contraintes (question 2) : grammaire Lark (LALR),
arbre de syntaxe abstraite (AST), affichage.

    texte --(analyseur Lark)--> arbre d'analyse --(ASTBuilder)--> AST

Étend le fragment propositionnel de proplog/ (mêmes classes Program, VarDecl,
Constraint, Var, Not, And, Or, Implies, EnumDomain) au langage complet :
constantes, types énumérés, domaines a..b, tableaux, forall, comparaisons,
arithmétique, accès aux tableaux, tranches et appels de fonction.

Deux affichages :
    pretty(node)  arbre indenté, chaque opérateur entre parenthèses (lecture des priorités) ;
    source(node)  texte du modèle, entièrement parenthésé : parse(source(p)) == p.
"""

from dataclasses import dataclass
from lark import Lark, Transformer

# Rappels sur la notation Lark (voir aussi proplog/syntax.py) :
#   "?regle" : si la règle n'a qu'un enfant, l'enfant remplace le nœud ;
#   "-> nom" : nom du nœud, donc de la méthode d'ASTBuilder appelée ;
#   les chaînes "..." (mots-clés, ponctuation) sont reconnues puis retirées de l'arbre.
# L'analyseur lexical est "basic" : un mot-clé donne toujours un lexème mot-clé,
# jamais un NAME. Les onze mots-clés sont donc réservés (`var in : bool;` est rejeté),
# tandis qu'un nom qui commence par un mot-clé (`index`, `order`) reste un NAME.

GRAMMAR = r"""
?start: program

program: statement*

?statement: const_decl
          | enum_decl
          | var_decl
          | array_decl
          | constraint_decl
          | forall_stmt

// -------------------- DÉCLARATIONS --------------------

// const N = 9;            const region[2][3] = [[1, 1, 2], [3, 3, 2]];
const_decl: "const" NAME "=" expr ";"                 -> const_int
          | "const" NAME dims "=" array_lit ";"       -> const_array

array_lit: "[" [element ("," element)*] "]"
?element: expr
        | array_lit

// enum Color = { Red, Green, Blue };
enum_decl: "enum" NAME "=" "{" NAME ("," NAME)* "}" ";"

// var x : 1..N;           array grid[N][N] : 1..N;
var_decl: "var" NAME ":" domain ";"
array_decl: "array" NAME dims ":" domain ";"

// une dimension : une taille (expression) ou un type énuméré (un nom, résolu à l'analyse)
dims: ("[" expr "]")+

domain: "bool"                                        -> bool_domain
      | sum ".." sum                                  -> range_domain
      | NAME                                          -> named_domain

// constraint e;
constraint_decl: "constraint" expr ";"

// forall i in 1..N, c in Color { ... }   (le corps ne contient que des contraintes et des forall)
forall_stmt: "forall" iterator ("," iterator)* "{" body_stmt* "}"
iterator: NAME "in" domain
?body_stmt: constraint_decl
          | forall_stmt

// -------------------- EXPRESSIONS --------------------
//
// Niveaux, du moins prioritaire au plus prioritaire :
//     ->  <  or  <  and  <  not  <  comparaisons  <  + -  <  *  <  - unaire  <  atomes
// -> est associatif à droite ; or, and, +, -, * à gauche ; les comparaisons ne
// s'enchaînent pas (a = b = c est une erreur de syntaxe).
//     not x = 2        se lit  not (x = 2)
//     a + b * c        se lit  a + (b * c)
//     - a * b          se lit  (- a) * b

?expr: implication

?implication: or_expr
            | or_expr "->" implication              -> implies

?or_expr: and_expr
        | or_expr "or" and_expr                     -> or_op

?and_expr: not_expr
         | and_expr "and" not_expr                  -> and_op

?not_expr: "not" not_expr                           -> not_op
         | comparison

?comparison: sum
           | sum "=" sum                            -> eq
           | sum "!=" sum                           -> ne
           | sum "<" sum                            -> lt
           | sum "<=" sum                           -> le
           | sum ">" sum                            -> gt
           | sum ">=" sum                           -> ge

?sum: product
    | sum "+" product                               -> add
    | sum "-" product                               -> sub

?product: unary
        | product "*" unary                         -> mul

?unary: "-" unary                                   -> neg
      | atom

?atom: INT                                          -> int_lit
     | NAME                                         -> var_ref
     | NAME ("[" index "]")+                        -> access
     | NAME "(" [expr ("," expr)*] ")"              -> call
     | "(" expr ")"

// "*" est à la fois la multiplication et le joker des tranches : aucune
// expression ne commence par "*", d'où l'absence de conflit après "[".
?index: expr
      | "*"                                         -> wildcard

%import common.CNAME -> NAME
%import common.INT
%import common.WS
%import common.CPP_COMMENT
%ignore WS
%ignore CPP_COMMENT
"""

KEYWORDS = {"const", "enum", "var", "array", "bool", "constraint",
            "forall", "in", "not", "and", "or"}


# ------------------------------------------------------------
# AST
# ------------------------------------------------------------

# Déclarations et instructions

@dataclass
class Program:
    statements: list

class Domain:
    pass

@dataclass
class EnumDomain(Domain):
    """Domaine nommé : "bool" ou le nom d'un type énuméré (résolu à l'analyse)."""
    name: str

@dataclass
class RangeDomain(Domain):
    """Intervalle lo..hi, bornes données par des expressions (connues)."""
    lo: object
    hi: object

@dataclass
class ConstDecl:
    """const N = e;"""
    name: str
    expr: object

@dataclass
class ConstArrayDecl:
    """const t[d1]...[dk] = [...]; values : listes imbriquées d'expressions."""
    name: str
    dims: list
    values: list

@dataclass
class EnumDecl:
    name: str
    values: list

@dataclass
class VarDecl:
    name: str
    domain: Domain

@dataclass
class ArrayDecl:
    """array t[d1]...[dk] : domaine; chaque di est une expression (taille ou nom de type)."""
    name: str
    dims: list
    domain: Domain

@dataclass
class Constraint:
    expr: object

@dataclass
class Forall:
    """forall x1 in D1, ..., xk in Dk { body } ; iterators : liste de (nom, Domain)."""
    iterators: list
    body: list


# Expressions

@dataclass
class Var:
    """Un nom utilisé comme valeur : x, N, Red, i."""
    name: str

@dataclass
class IntLit:
    value: int

@dataclass
class And:
    left: object
    right: object

@dataclass
class Or:
    left: object
    right: object

@dataclass
class Not:
    expr: object

@dataclass
class Implies:
    left: object
    right: object

@dataclass
class Compare:
    """op parmi = != < <= > >=."""
    op: str
    left: object
    right: object

@dataclass
class BinOp:
    """op parmi + - *."""
    op: str
    left: object
    right: object

@dataclass
class Neg:
    expr: object

@dataclass
class Access:
    """t[e1]...[ek] ; un indice peut être Wildcard() (tranche)."""
    name: str
    indices: list

@dataclass
class Wildcard:
    pass

@dataclass
class Call:
    """f(e1, ..., en) : abs ou contrainte globale."""
    name: str
    args: list


class ASTBuilder(Transformer):
    """Construit l'AST de bas en haut : Lark appelle la méthode nommée d'après
    chaque règle (ou alias), avec ses enfants déjà transformés."""

    def NAME(self, token):
        return str(token)

    def INT(self, token):
        return int(token)

    def program(self, items):
        return Program(items)

    # Déclarations

    def const_int(self, items):
        return ConstDecl(items[0], items[1])

    def const_array(self, items):
        return ConstArrayDecl(items[0], items[1], items[2])

    def array_lit(self, items):
        # [ ] donne [None] (élément optionnel absent)
        return [x for x in items if x is not None]

    def enum_decl(self, items):
        return EnumDecl(items[0], list(items[1:]))

    def var_decl(self, items):
        return VarDecl(items[0], items[1])

    def array_decl(self, items):
        return ArrayDecl(items[0], items[1], items[2])

    def dims(self, items):
        return list(items)

    def bool_domain(self, items):
        return EnumDomain("bool")

    def range_domain(self, items):
        return RangeDomain(items[0], items[1])

    def named_domain(self, items):
        return EnumDomain(items[0])

    def constraint_decl(self, items):
        return Constraint(items[0])

    def forall_stmt(self, items):
        iterators = [x for x in items if isinstance(x, tuple)]
        body = [x for x in items if not isinstance(x, tuple)]
        return Forall(iterators, body)

    def iterator(self, items):
        return (items[0], items[1])

    # Expressions

    def int_lit(self, items):
        return IntLit(items[0])

    def var_ref(self, items):
        return Var(items[0])

    def access(self, items):
        return Access(items[0], list(items[1:]))

    def wildcard(self, items):
        return Wildcard()

    def call(self, items):
        return Call(items[0], [x for x in items[1:] if x is not None])

    def and_op(self, items):
        return And(items[0], items[1])

    def or_op(self, items):
        return Or(items[0], items[1])

    def not_op(self, items):
        return Not(items[0])

    def implies(self, items):
        return Implies(items[0], items[1])

    def neg(self, items):
        return Neg(items[0])

    def add(self, items):
        return BinOp("+", items[0], items[1])

    def sub(self, items):
        return BinOp("-", items[0], items[1])

    def mul(self, items):
        return BinOp("*", items[0], items[1])


def _comparison(op):
    return lambda self, items: Compare(op, items[0], items[1])

for _name, _op in [("eq", "="), ("ne", "!="), ("lt", "<"), ("le", "<="), ("gt", ">"), ("ge", ">=")]:
    setattr(ASTBuilder, _name, _comparison(_op))


parser = Lark(GRAMMAR, parser="lalr", lexer="basic")


def parse(text: str) -> Program:
    """Analyse un modèle complet ; lève lark.exceptions.UnexpectedInput en cas d'erreur."""
    return ASTBuilder().transform(parser.parse(text))


# ------------------------------------------------------------
# Affichage
# ------------------------------------------------------------

def pretty(node) -> str:
    """Arbre indenté : une instruction par ligne, chaque opérateur entre parenthèses."""
    return "\n".join(_pretty_lines(node, 0))


def _pretty_lines(node, depth):
    pad = "  " * depth
    if isinstance(node, Program):
        yield pad + "Program"
        for s in node.statements:
            yield from _pretty_lines(s, depth + 1)
    elif isinstance(node, ConstDecl):
        yield f"{pad}Const {node.name} = {pretty_expr(node.expr)}"
    elif isinstance(node, ConstArrayDecl):
        yield f"{pad}Const {node.name}{_dims(node.dims, pretty_expr)} = {_lit(node.values, pretty_expr)}"
    elif isinstance(node, EnumDecl):
        yield f"{pad}Enum {node.name} = {{{', '.join(node.values)}}}"
    elif isinstance(node, VarDecl):
        yield f"{pad}Var {node.name} : {_domain(node.domain, pretty_expr)}"
    elif isinstance(node, ArrayDecl):
        yield f"{pad}Array {node.name}{_dims(node.dims, pretty_expr)} : {_domain(node.domain, pretty_expr)}"
    elif isinstance(node, Constraint):
        yield f"{pad}Constraint {pretty_expr(node.expr)}"
    elif isinstance(node, Forall):
        its = ", ".join(f"{x} in {_domain(d, pretty_expr)}" for x, d in node.iterators)
        yield f"{pad}Forall {its}"
        for s in node.body:
            yield from _pretty_lines(s, depth + 1)
    else:
        raise TypeError(f"pretty : nœud inattendu {node!r}")


def pretty_expr(e) -> str:
    """Expression avec la notation de proplog/ (!, /\\, \\/), chaque opérateur parenthésé."""
    if isinstance(e, Var):
        return e.name
    if isinstance(e, IntLit):
        return str(e.value)
    if isinstance(e, Not):
        return f"(!{pretty_expr(e.expr)})"
    if isinstance(e, And):
        return f"({pretty_expr(e.left)} /\\ {pretty_expr(e.right)})"
    if isinstance(e, Or):
        return f"({pretty_expr(e.left)} \\/ {pretty_expr(e.right)})"
    if isinstance(e, Implies):
        return f"({pretty_expr(e.left)} -> {pretty_expr(e.right)})"
    if isinstance(e, (Compare, BinOp)):
        return f"({pretty_expr(e.left)} {e.op} {pretty_expr(e.right)})"
    if isinstance(e, Neg):
        return f"(-{pretty_expr(e.expr)})"
    if isinstance(e, Access):
        return e.name + "".join(f"[{pretty_expr(i)}]" for i in e.indices)
    if isinstance(e, Wildcard):
        return "*"
    if isinstance(e, Call):
        return f"{e.name}({', '.join(pretty_expr(a) for a in e.args)})"
    raise TypeError(f"pretty : expression inattendue {e!r}")


def source(node) -> str:
    """Texte du modèle, avec toutes les parenthèses : parse(source(p)) == p."""
    if isinstance(node, Program):
        return "\n".join(source(s) for s in node.statements) + "\n"
    if isinstance(node, ConstDecl):
        return f"const {node.name} = {source_expr(node.expr)};"
    if isinstance(node, ConstArrayDecl):
        return f"const {node.name}{_dims(node.dims, source_expr)} = {_lit(node.values, source_expr)};"
    if isinstance(node, EnumDecl):
        return f"enum {node.name} = {{ {', '.join(node.values)} }};"
    if isinstance(node, VarDecl):
        return f"var {node.name} : {_domain(node.domain, source_expr)};"
    if isinstance(node, ArrayDecl):
        return f"array {node.name}{_dims(node.dims, source_expr)} : {_domain(node.domain, source_expr)};"
    if isinstance(node, Constraint):
        return f"constraint {source_expr(node.expr)};"
    if isinstance(node, Forall):
        its = ", ".join(f"{x} in {_domain(d, source_expr)}" for x, d in node.iterators)
        return f"forall {its} {{ " + " ".join(source(s) for s in node.body) + " }"
    raise TypeError(f"source : nœud inattendu {node!r}")


def source_expr(e) -> str:
    if isinstance(e, Var):
        return e.name
    if isinstance(e, IntLit):
        return str(e.value)
    if isinstance(e, Not):
        return f"(not {source_expr(e.expr)})"
    if isinstance(e, And):
        return f"({source_expr(e.left)} and {source_expr(e.right)})"
    if isinstance(e, Or):
        return f"({source_expr(e.left)} or {source_expr(e.right)})"
    if isinstance(e, Implies):
        return f"({source_expr(e.left)} -> {source_expr(e.right)})"
    if isinstance(e, (Compare, BinOp)):
        return f"({source_expr(e.left)} {e.op} {source_expr(e.right)})"
    if isinstance(e, Neg):
        return f"(- {source_expr(e.expr)})"
    if isinstance(e, Access):
        return e.name + "".join(f"[{source_expr(i)}]" for i in e.indices)
    if isinstance(e, Wildcard):
        return "*"
    if isinstance(e, Call):
        return f"{e.name}({', '.join(source_expr(a) for a in e.args)})"
    raise TypeError(f"source : expression inattendue {e!r}")


def _dims(dims, show):
    return "".join(f"[{show(d)}]" for d in dims)


def _domain(d, show):
    if isinstance(d, EnumDomain):
        return d.name
    # parenthèses toujours valides autour d'une borne : (1)..(N)
    return f"{show(d.lo)}..{show(d.hi)}"


def _lit(values, show):
    if isinstance(values, list):
        return "[" + ", ".join(_lit(v, show) for v in values) + "]"
    return show(values)
