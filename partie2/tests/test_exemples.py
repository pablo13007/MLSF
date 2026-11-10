"""Tests de bout en bout (question 5) : les modèles du dossier exemples/ donnent les
réponses du tableau 1 de l'énoncé, et les solutions sont vérifiées par des
vérificateurs indépendants du compilateur, qui ne lisent que la sortie texte de
`python csp.py modele.csp --solve` (lignes « nom = valeur »).

À lancer depuis partie2/ :  python -m tests.test_exemples
"""

import re
import subprocess
import sys
from pathlib import Path

PARTIE2 = Path(__file__).resolve().parent.parent
EXEMPLES = PARTIE2 / "exemples"


def solve(path):
    """(statut, {nom: valeur}) d'après la sortie de csp.py --solve."""
    r = subprocess.run([sys.executable, "csp.py", str(path), "--solve"],
                       cwd=PARTIE2, capture_output=True, text=True, check=True)
    lignes = r.stdout.splitlines()
    statut = lignes[0]
    valeurs = dict(l.split(" = ") for l in lignes[1:])
    return statut, valeurs


def tableau(valeurs, name):
    """{(i, j, ...): valeur entière} des cases name[i][j]... ."""
    t = {}
    for k, v in valeurs.items():
        m = re.fullmatch(rf"{name}((?:\[\w+\])+)", k)
        if m:
            idx = tuple(int(i) for i in re.findall(r"\[(\w+)\]", m.group(1)))
            t[idx] = int(v) if v.lstrip("-").isdigit() else v
    return t


def test_pigeonhole():
    statut, _ = solve(EXEMPLES / "pigeonhole.csp")
    assert statut == "s UNSATISFIABLE"


def test_queens():
    statut, val = solve(EXEMPLES / "queens.csp")
    assert statut == "s SATISFIABLE"
    q = tableau(val, "queen")
    N = 8
    assert sorted(q) == [(i,) for i in range(1, N + 1)]
    cols = [q[(i,)] for i in range(1, N + 1)]
    assert sorted(cols) == list(range(1, N + 1))                     # une reine par colonne
    for i in range(N):
        for j in range(i + 1, N):
            assert abs(cols[i] - cols[j]) != j - i                   # pas de diagonale commune


def test_coloring():
    statut, val = solve(EXEMPLES / "coloring.csp")
    assert statut == "s SATISFIABLE"
    color = tableau(val, "color")
    edges = [(1, 2), (2, 3), (3, 4), (4, 5), (5, 1), (6, 8), (8, 10), (10, 7), (7, 9), (9, 6),
             (1, 6), (2, 7), (3, 8), (4, 9), (5, 10)]
    assert all(color[(u,)] in ("Red", "Green", "Blue") for u in range(1, 11))
    assert all(color[(u,)] != color[(v,)] for u, v in edges)
    assert color[(1,)] == "Red" and color[(2,)] == "Green"


def test_sudoku():
    statut, val = solve(EXEMPLES / "sudoku.csp")
    assert statut == "s SATISFIABLE"
    g = tableau(val, "grid")
    rows = [[g[(i, j)] for j in range(1, 10)] for i in range(1, 10)]
    cols = [[g[(i, j)] for i in range(1, 10)] for j in range(1, 10)]
    boxes = [[g[(3 * bi + a, 3 * bj + b)] for a in range(1, 4) for b in range(1, 4)]
             for bi in range(3) for bj in range(3)]
    for groupe in rows + cols + boxes:
        assert sorted(groupe) == list(range(1, 10))
    # cases données (lues dans le fichier du modèle)
    texte = (EXEMPLES / "sudoku.csp").read_text()
    donnees = re.search(r"const given\[N\]\[N\] = \[(.*?)\];", texte, re.S).group(1)
    nombres = [int(x) for x in re.findall(r"\d+", donnees)]
    assert len(nombres) == 81
    for k, v in enumerate(nombres):
        if v:
            assert rows[k // 9][k % 9] == v


def test_fragment_propositionnel():
    statut, val = solve(EXEMPLES / "proplog" / "subject.csp")
    assert statut == "s SATISFIABLE"
    x, y, z = (val[n] == "true" for n in "xyz")
    assert (x or y) and (not x and z) and (not z or y)
    assert solve(EXEMPLES / "proplog" / "pigeonhole.csp")[0] == "s UNSATISFIABLE"


def test_sortie_dimacs():
    # sans option : DIMACS sur la sortie standard, avec la correspondance nom <-> numéro
    r = subprocess.run([sys.executable, "csp.py", str(EXEMPLES / "pigeonhole.csp")],
                       cwd=PARTIE2, capture_output=True, text=True, check=True)
    lignes = r.stdout.splitlines()
    assert "c var 1 hole[1] = 1" in lignes and "p cnf 12 34" in lignes


if __name__ == "__main__":
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print(f"{name}: ok")
