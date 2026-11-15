"""Tests de l'analyseur syntaxique (question 2) : priorités et associativités,
erreurs de syntaxe, mots-clés réservés, exemples, affichage et aller-retour.

À lancer depuis partie2/ :  python -m tests.test_syntax
"""

from pathlib import Path

from lark.exceptions import UnexpectedInput

from syntax import (Access, And, ArrayDecl, BinOp, Call, Compare, ConstArrayDecl, ConstDecl,
                    EnumDecl, EnumDomain, Forall, Implies, IntLit, Neg, Not, Or, RangeDomain,
                    Var, VarDecl, Wildcard, parse, pretty, source)

EXEMPLES = Path(__file__).resolve().parent.parent / "exemples"

a, b, c, x, y = Var("a"), Var("b"), Var("c"), Var("x"), Var("y")
one, two = IntLit(1), IntLit(2)


def parse_expr(text):
    return parse(f"constraint {text};").statements[0].expr


def test_precedence_fragment():
    # cas du code de départ (proplog/) : inchangés
    cases = [
        ("a or b and c",    Or(a, And(b, c))),
        ("a and b or c",    Or(And(a, b), c)),
        ("not a and b",     And(Not(a), b)),
        ("not (a and b)",   Not(And(a, b))),
        ("a or b -> c",     Implies(Or(a, b), c)),
        ("a -> b or c",     Implies(a, Or(b, c))),
        ("not a -> b",      Implies(Not(a), b)),
        ("not not a",       Not(Not(a))),
        ("((a))",           a),
    ]
    for text, expected in cases:
        assert parse_expr(text) == expected, text


def test_associativity():
    cases = [
        ("a and b and c",   And(And(a, b), c)),
        ("a or b or c",     Or(Or(a, b), c)),
        ("a -> b -> c",     Implies(a, Implies(b, c))),
        ("(a -> b) -> c",   Implies(Implies(a, b), c)),
        ("a - b - c",       BinOp("-", BinOp("-", a, b), c)),
        ("a * b * c",       BinOp("*", BinOp("*", a, b), c)),
    ]
    for text, expected in cases:
        assert parse_expr(text) == expected, text


def test_precedence_nouveaux_operateurs():
    cases = [
        ("not x = 2",           Not(Compare("=", x, two))),          # énoncé
        ("x = 1 and y != 2",    And(Compare("=", x, one), Compare("!=", y, two))),
        ("x + 1 * 2",           BinOp("+", x, BinOp("*", one, two))),
        ("(x + 1) * 2",         BinOp("*", BinOp("+", x, one), two)),
        ("- x * 2",             BinOp("*", Neg(x), two)),
        ("x - - 1",             BinOp("-", x, Neg(one))),
        ("x + 1 < y",           Compare("<", BinOp("+", x, one), y)),
        ("a -> x <= 2",         Implies(a, Compare("<=", x, two))),
        ("abs(x - y) = 1",      Compare("=", Call("abs", [BinOp("-", x, y)]), one)),
        ("t[i + 1][j]",         Access("t", [BinOp("+", Var("i"), one), Var("j")])),
        ("t[i][*] = 1",         Compare("=", Access("t", [Var("i"), Wildcard()]), one)),
        ("allDifferent(t[*][*], x)",
                                Call("allDifferent", [Access("t", [Wildcard(), Wildcard()]), x])),
        ("t[u[1]] >= 2",        Compare(">=", Access("t", [Access("u", [one])]), two)),
        ("f()",                 Call("f", [])),
    ]
    for text, expected in cases:
        assert parse_expr(text) == expected, text


def test_declarations():
    p = parse("const N = 3; enum C = { R, G }; var x : 1..N; var c : C; var b : bool;"
              "array t[N][C] : 0..1; const d[2][2] = [[1, 2], [3, 4]];"
              "forall i in 1..N, k in C { constraint t[i][k] = 0; }")
    assert p.statements == [
        ConstDecl("N", IntLit(3)),
        EnumDecl("C", ["R", "G"]),
        VarDecl("x", RangeDomain(one, Var("N"))),
        VarDecl("c", EnumDomain("C")),
        VarDecl("b", EnumDomain("bool")),
        ArrayDecl("t", [Var("N"), Var("C")], RangeDomain(IntLit(0), one)),
        ConstArrayDecl("d", [two, two], [[one, two], [IntLit(3), IntLit(4)]]),
        Forall([("i", RangeDomain(one, Var("N"))), ("k", EnumDomain("C"))],
               [parse("constraint t[i][k] = 0;").statements[0]]),
    ]


def test_syntax_errors():
    cases = [
        ("var x : bool",                        (1, 9)),    # ";" manquant
        ("var x : bool; constraint x or;",      (1, 30)),
        ("constraint (x and y;",                (1, 20)),
        ("constraint x y;",                     (1, 14)),
        ("constraint x <-> y;",                 (1, 15)),   # pas de <-> : "<" puis "->" inattendu
        ("constraint a = b = c;",               (1, 18)),   # comparaisons non enchaînées
        ("constraint x < y < 3;",               (1, 18)),
        ("var x : 1..;",                        (1, 12)),
        ("forall i in 1..3 { var x : bool; }",  (1, 20)),   # pas de déclaration dans un forall
        ("constraint t[];",                     (1, 14)),
        ("const t[2] = [1, 2;",                 (1, 19)),
        ("constraint x = 1.5;",                 (1, 17)),   # pas de flottants
        ("constraint x = $;",                   (1, 16)),   # caractère inconnu
    ]
    for text, (line, column) in cases:
        try:
            parse(text)
        except UnexpectedInput as e:
            assert (e.line, e.column) == (line, column), (text, e.line, e.column)
        else:
            raise AssertionError(f"pas d'erreur de syntaxe dans {text!r}")


def test_keywords_reserved():
    for kw in ["const", "enum", "var", "array", "bool", "constraint",
               "forall", "in", "not", "and", "or"]:
        try:
            parse(f"var {kw} : bool;")
        except UnexpectedInput:
            pass
        else:
            raise AssertionError(f"le mot-clé {kw} accepté comme nom")
    # un nom qui commence par un mot-clé reste un nom ; les fonctions ne sont pas réservées
    parse("var index : bool; var order : bool; var android : bool; var abs : bool;"
          "var allDifferent : bool;")


def test_examples():
    # tous les exemples s'analysent, sauf proplog/syntax-error.csp
    paths = sorted(EXEMPLES.glob("*.csp")) + sorted((EXEMPLES / "proplog").glob("*.csp"))
    assert len(paths) >= 8
    for path in paths:
        try:
            parse(path.read_text())
        except UnexpectedInput:
            assert path.name == "syntax-error.csp", path.name
        else:
            assert path.name != "syntax-error.csp", path.name


def test_round_trip():
    # le texte affiché par source() redonne le même arbre
    paths = [p for p in sorted(EXEMPLES.rglob("*.csp")) if p.name != "syntax-error.csp"]
    for path in paths:
        try:
            p = parse(path.read_text())
        except UnexpectedInput:
            continue                    # exemples d'erreurs de syntaxe de exemples/erreurs/
        assert parse(source(p)) == p, path.name


def test_pretty():
    program = parse("var x : bool;\n"
                    "var y : bool;\n"
                    "constraint not x and y -> x or y;\n")
    assert pretty(program) == ("Program\n"
                               "  Var x : bool\n"
                               "  Var y : bool\n"
                               "  Constraint (((!x) /\\ y) -> (x \\/ y))")
    program = parse("const N = 2; array g[N][N] : 1..N;"
                    "forall i in 1..N { constraint allDifferent(g[i][*]); }")
    assert pretty(program) == ("Program\n"
                               "  Const N = 2\n"
                               "  Array g[N][N] : 1..N\n"
                               "  Forall i in 1..N\n"
                               "    Constraint allDifferent(g[i][*])")


if __name__ == "__main__":
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print(f"{name}: ok")
