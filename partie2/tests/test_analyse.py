"""Tests de l'analyse et du déroulement (question 3).

- la collection de modèles erronés exemples/erreurs/ : chaque modèle est rejeté par
  une CompileError (jamais une autre exception) dont le message contient le texte
  annoncé en première ligne du fichier ;
- de petits modèles dont on connaît le résultat déroulé et simplifié ;
- les accès hors bornes protégés par une condition fausse (aucune erreur) ou non.

À lancer depuis partie2/ :  python -m tests.test_analyse
"""

import subprocess
import sys
from pathlib import Path

from ir import montrer
from solveur import compiler
from symboles import CompileError

PARTIE2 = Path(__file__).resolve().parent.parent
ERREURS = PARTIE2 / "exemples" / "erreurs"


def deroule(texte):
    """Contraintes déroulées (texte) et avertissements d'un modèle."""
    modele, _ = compiler(texte)
    return [montrer(c) for c in modele.contraintes], modele.avertissements


def rejete(texte):
    try:
        compiler(texte)
    except CompileError as e:
        return str(e)
    raise AssertionError(f"modèle accepté : {texte!r}")


def test_collection_erreurs():
    fichiers = sorted(ERREURS.glob("*.csp"))
    assert len(fichiers) >= 30
    for f in fichiers:
        texte = f.read_text(encoding="utf-8")
        attendu = texte.splitlines()[0].removeprefix("// erreur attendue : ")
        msg = rejete(texte)
        assert attendu in msg, (f.name, msg)


def test_ligne_de_commande_erreur():
    # code de retour 1 et message sur stderr, pas de trace Python
    r = subprocess.run([sys.executable, "csp.py", str(ERREURS / "nom_non_declare.csp")],
                       cwd=PARTIE2, capture_output=True, text=True)
    assert r.returncode == 1 and r.stdout == ""
    assert "nom non déclaré 'w'" in r.stderr and "Traceback" not in r.stderr


def test_deroulement():
    cs, _ = deroule("const N = 3; array g[N] : 1..N;"
                    "forall i in 1..N { constraint i < N -> g[i + 1] != g[i]; }")
    assert cs == ["g[2] != g[1]", "g[3] != g[2]"]
    # bornes dépendant d'un indice précédent : j in i..N
    cs, _ = deroule("const N = 3; array b[N][N] : bool;"
                    "forall i in 1..N, j in i..N { constraint b[i][j]; }")
    assert cs == ["b[1][1]", "b[1][2]", "b[1][3]", "b[2][2]", "b[2][3]", "b[3][3]"]
    # forall imbriqués, boucle sur un type énuméré, tableau indicé par un type énuméré
    cs, _ = deroule("enum C = { R, G }; array u[C][2] : bool;"
                    "forall c in C { forall k in 1..2 { constraint u[c][k]; } }")
    assert cs == ["u[R][1]", "u[R][2]", "u[G][1]", "u[G][2]"]


def test_valeurs_connues():
    cs, _ = deroule("const t[2][2] = [[1, 2], [3, 4]]; var x : 0..10;"
                    "constraint x = t[2][1] * 2 + abs(-1);"
                    "constraint x != t[1][2] - 3 * (1 - 2);")
    assert cs == ["x = 7", "x != 5"]
    # tableau constant de valeurs énumérées, indice calculé par un tableau constant
    cs, _ = deroule("enum Z = { A, B }; const r[2] = [B, A]; const p[1] = [2];"
                    "array c[2] : Z; constraint c[p[1]] = r[1]; constraint r[1] > r[2];")
    assert cs == ["c[2] = 1"]                 # B a le code 1 ; B > A est vrai : disparaît


def test_normalisation():
    cs, _ = deroule("var x : 1..9; var y : 1..9;"
                    "constraint not (x = 2);"         # x != 2
                    "constraint x > y;"               # y < x
                    "constraint x < 5;"               # x <= 4
                    "constraint 3 <= x;"              # x >= 3
                    "constraint x <= 100;"            # toujours vraie (domaine) : disparaît
                    "constraint not (x < y);"         # y <= x
                    "constraint x >= 9;"              # une seule valeur : x = 9
                    "constraint not (x = 1 and y = 2);")   # De Morgan
    assert cs == ["x != 2", "y < x", "x <= 4", "x >= 3", "y <= x", "x = 9",
                  "(x != 1 or y != 2)"]


def test_court_circuit_et_simplification():
    cs, av = deroule("var b : bool; var c : bool;"
                     "constraint 1 < 2 or c;"         # vraie : disparaît
                     "constraint 1 < 2 -> b;"         # b
                     "constraint 2 < 1 -> c;"         # vraie : disparaît
                     "constraint b and 1 = 1;"        # b
                     "constraint not not c;"          # c
                     "constraint b = (1 = 1);"        # b
                     "constraint b != c;")            # not (b = c)
    assert cs == ["b", "b", "c", "b", "not (b = c)"] and av == []
    cs, av = deroule("var b : bool; constraint 1 > 2 and b;")
    assert cs == ["false"] and len(av) == 1 and "toujours fausse" in av[0]


def test_acces_proteges():
    # aucune erreur : l'accès hors bornes n'est jamais évalué
    for texte in [
        "array a[3] : bool; forall i in 1..3 { constraint i < 3 -> a[i + 1]; }",
        "array a[3] : bool; forall i in 1..3 { constraint i = 3 or a[i + 1]; }",
        "array a[3] : bool; forall i in 1..3 { constraint i < 3 and a[i + 1] or i = 3; }",
        "const N = 3; array g[N][N] : 1..N;"
        "forall i in 1..N { constraint i < N -> g[i + 1][1] != g[i][1]; }",
    ]:
        compiler(texte)
    # erreur : l'accès est évalué (pas de filtre, ou filtre placé après l'accès)
    for texte in [
        "array a[3] : bool; forall i in 1..3 { constraint a[i + 1] -> i < 3; }",
        "array a[3] : bool; forall i in 1..3 { constraint a[i + 1] and i < 3; }",
        "array a[3] : bool; var b : bool; forall i in 1..3 { constraint b -> a[i + 1]; }",
        "array a[3] : bool; constraint atLeastOne(a[0], a[1]);",
    ]:
        assert "hors de 1..3" in rejete(texte), texte


def test_tranches_et_globales():
    cs, _ = deroule("array g[2][3] : 1..5;"
                    "constraint allDifferent(g[*][2]);"
                    "constraint allDifferent(g[2][*], g[1][1]);"
                    "constraint allDifferent(g[1][1], 2, g[1][2]);")
    assert cs == ["allDifferent(g[1][2], g[2][2])",
                  "allDifferent(g[2][1], g[2][2], g[2][3], g[1][1])",
                  "(g[1][1] != 2 and g[1][2] != 2 and allDifferent(g[1][1], g[1][2]))"]
    cs, _ = deroule("array g[2][2] : bool; constraint exactlyOne(g[*][*]);")
    assert cs == ["exactlyOne(g[1][1], g[1][2], g[2][1], g[2][2])"]     # ordre ligne par ligne
    cs, _ = deroule("array a[3] : bool;"
                    "constraint atMostOne(a[1], 1 = 1, a[2]);"       # un argument vrai
                    "constraint atLeastOne(a[1], 1 = 2);"            # argument faux retiré
                    "constraint exactlyOne(1 = 2, a[3]);"
                    "constraint atMostOne(a[1]);")                  # toujours vraie
    assert cs == ["(not a[1] and not a[2])", "a[1]", "a[3]"]
    cs, _ = deroule("array h[2] : 1..3; constraint allDifferent(h[1], h[1]);"
                    "constraint allDifferent(1, 2, 1);")
    assert cs == ["false", "false"]


if __name__ == "__main__":
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print(f"{name}: ok")
