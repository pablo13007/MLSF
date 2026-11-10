# Partie II — Un langage de contraintes compilé vers SAT

Un compilateur lit un modèle écrit dans un petit langage de contraintes, le traduit en
FNC (format DIMACS), appelle le solveur DPLL de la partie I (réutilisé tel quel, depuis
`../partie1/Session de travail/`), puis affiche la solution dans les termes du modèle.

```
modèle (texte) --Q2--> AST --Q3--> contraintes sans forall --Q4--> FNC --Q5--> solveur --Q5--> valeurs
               syntax.py   analyse.py + deroulement.py     fnc.py      solveur.py (partie I)
```

## Utilisation (depuis `partie2/`)

Seule dépendance : `lark` (voir `../requirements.txt`).

```bash
python csp.py exemples/sudoku.csp                  # FNC au format DIMACS sur la sortie standard
python csp.py exemples/sudoku.csp --dimacs f.cnf   # FNC écrite dans f.cnf
python csp.py exemples/sudoku.csp --solve          # résolution : s SATISFIABLE + « nom = valeur »
python csp.py exemples/queens.csp --ast            # arbre de syntaxe abstraite
python csp.py exemples/queens.csp --deroule        # contraintes déroulées et simplifiées
python csp.py exemples/queens.csp --solve --stats  # tailles et temps sur stderr
python csp.py exemples/queens.csp --solve --heur H1   # autre heuristique de la partie I
```

L'interface est celle conseillée par l'énoncé. Avec `--solve`, la sortie est `s SATISFIABLE`
suivi d'une ligne `nom = valeur` par variable (`grid[1][2] = 5`, `color[3] = Red`,
`x = true`), ou `s UNSATISFIABLE`. Un modèle erroné est rejeté avec un message sur stderr
et le code de retour 1. Le DIMACS contient la correspondance des noms (`c var 3 grid[1][3] = 3`).

## Fichiers

| Fichier | Question | Rôle |
|---|---|---|
| `syntax.py` | Q2 | grammaire Lark (LALR), classes de l'AST, `ASTBuilder`, `parse`, `pretty`, `source` |
| `symboles.py` | Q3 | table des symboles : types, symboles, `CompileError` |
| `analyse.py` | Q3 | vérifications statiques (noms, types, valeurs connues, indices, arguments) |
| `deroulement.py` | Q3 | déroulement des `forall`, calcul des valeurs connues, court-circuit, simplifications |
| `ir.py` | Q3/Q4 | représentation intermédiaire : contraintes sur des cases de variables |
| `fnc.py` | Q1/Q4 | encodage direct des domaines, comparaisons, contraintes globales, Tseitin |
| `solveur.py` | Q1/Q5 | chaîne complète, écriture DIMACS, appel au solveur de la partie I, décodage |
| `csp.py` | — | ligne de commande |
| `exemples/` | | les 4 modèles de l'énoncé, `proplog/` (fragment propositionnel), `erreurs/` (33 modèles erronés), 2 modèles Meowdoku complets |
| `tests/` | | tests de chaque étape |
| `q6_meowdoku/` | Q6 | Meowdoku : conversion des grilles, règles, vérificateur, expériences |
| `rapport.tex` | | rapport (à compiler avec `latexmk -pdf` ou LaTeX Workshop) |

## Tests (depuis `partie2/`)

```bash
for t in syntax analyse fnc exemples meowdoku; do python -m tests.test_$t; done
```

- `test_syntax` : priorités, associativités, erreurs de syntaxe, mots-clés, aller-retour `parse(source(p)) == p`
- `test_analyse` : les 33 modèles erronés, déroulement, simplifications, accès hors bornes protégés ou non
- `test_fnc` : validation aléatoire contre une recherche exhaustive (600 modèles), tailles des encodages
- `test_exemples` : tableau 1 de l'énoncé, solutions vérifiées par des vérificateurs indépendants
- `test_meowdoku` : conversion, modèles Meowdoku, modèle généralisé contre une recherche exhaustive

## Question 6 (depuis `partie2/`)

```bash
python q6_meowdoku/grille_vers_csp.py grille.txt --regles q6_meowdoku/regles/modele2.csp -o g.csp   # 6.1
python csp.py g.csp --solve | python q6_meowdoku/verifier.py grille.txt   # vérificateur indépendant
python q6_meowdoku/resoudre_grilles.py      # 6.2 : grilles résolues avec chaque modèle et vérifiées
python q6_meowdoku/experiences.py           # 6.3, 6.4 : campagne de mesures -> resultats_q6.json (~15 min)
python q6_meowdoku/experiences.py --resume  # tableaux de synthèse
python q6_meowdoku/exhaustif.py             # 6.5 : modèle généralisé contre une recherche exhaustive
```

Règles (`q6_meowdoku/regles/`) : `modele1.csp` (position du chat de chaque région),
`modele2.csp` (une variable par case, avec « au plus un chat par région »),
`modele2_redondant.csp` (+ « au moins un chat par région »), `modele2_general.csp`
(N, M et K quelconques). Les grilles de `q6_meowdoku/grilles/` sont engendrées par le
générateur de la partie I et ne sont pas versionnées : les scripts les recréent.
