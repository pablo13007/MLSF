# Projet MLSF — Un solveur SAT pour Meowdoku

Projet du cours MLSF (2026-27), par Pablo Bosch et Cécile Chevrière.
Partie I : encoder le puzzle Meowdoku en formule SAT (CNF), puis le résoudre avec un solveur DPLL écrit nous-mêmes.
Partie II : un compilateur d'un petit langage de contraintes vers SAT, qui réutilise le solveur de la partie I
(détails, commandes et tests dans [`partie2/README.md`](partie2/README.md)).

## Arborescence

```
partie1/
├── rapport.tex / .pdf        Rapport (sources LaTeX et PDF compilé)
├── figures/                  Figures TikZ du rapport
└── Session de travail/
    ├── meowdoku.py           Q1 : grilles, encodage CNF, export DIMACS, vérification
    ├── generateur.py         Q1 : génération de grilles N×N ayant une solution
    ├── dpll.py               Q2 : lecture DIMACS, DPLL (algorithmes 1 et 2)
    ├── resoudre.py           Q3 : chaîne complète grille → CNF → DPLL → solution
    ├── heuristiques.py       Q4 : DPLL avec heuristique de branchement (H1 à H4)
    ├── mesures.py            Q5 : DPLL_H instrumenté, versions statiques, mesures
    ├── resultats_q5.json     Q5 : mesures brutes de la campagne
    ├── grilles/              Grilles d'exemple (dont celle de l'énoncé)
    └── projet_partie1.ipynb  Tests et expériences
partie2/
├── csp.py                    Ligne de commande du compilateur
├── syntax.py                 Q2 : grammaire Lark, AST
├── symboles.py, analyse.py   Q3 : table des symboles, vérifications
├── deroulement.py, ir.py     Q3 : déroulement des forall, simplifications
├── fnc.py                    Q1/Q4 : encodage des domaines, comparaisons, globales, Tseitin
├── solveur.py                Q1/Q5 : DIMACS, appel au solveur de la partie I, décodage
├── exemples/                 Modèles de l'énoncé, fragment propositionnel, modèles erronés
├── tests/                    Tests de chaque étape
├── q6_meowdoku/              Q6 : conversion des grilles, règles, vérificateur, expériences
└── rapport.tex               Rapport de la partie II
```

## Installation

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## Utilisation (depuis `partie1/Session de travail/`)

```bash
python generateur.py 8 42 grilles/grille_8x8.txt        # générer une grille
python meowdoku.py grilles/grille_enonce.txt f.cnf      # encoder en DIMACS
python dpll.py f.cnf --algo 2                           # résoudre un CNF
python resoudre.py grilles/grille_enonce.txt sol.txt    # résoudre une grille
python heuristiques.py f.cnf --heur H4                  # résoudre un CNF avec une heuristique
python mesures.py f.cnf --heur H4s --limite 60          # mesures (décisions, retours, ...) en JSON
```

## Utilisation de la partie II (depuis `partie2/`)

```bash
python csp.py exemples/sudoku.csp --solve        # résoudre un modèle
python csp.py exemples/sudoku.csp --dimacs f.cnf # écrire la FNC
```

## Rapport

Compiler `partie1/rapport.tex` et `partie2/rapport.tex` avec `latexmk -pdf` ou LaTeX Workshop.
Le PDF n'est pas régénéré automatiquement : il faut le recompiler après chaque modification du `.tex`.
