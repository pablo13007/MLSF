"""Chaîne complète (questions 1 et 5) : texte -> AST -> modèle déroulé -> FNC -> DIMACS
-> solveur de la partie I -> valeurs des variables du modèle.

Le solveur est celui de la partie I, réutilisé tel quel : DPLL avec heuristique de
branchement (heuristiques.dpll_h), H4 dynamique par défaut (retenue en partie I,
question 5). Le passage par un fichier DIMACS, relu par lire_dimacs de la partie I,
fait de ce fichier l'unique interface entre le compilateur et le solveur.
"""

import os
import sys
import tempfile
from pathlib import Path

from lark.exceptions import UnexpectedCharacters, UnexpectedEOF, UnexpectedInput, UnexpectedToken

from analyse import analyser
from deroulement import derouler
from fnc import FNC
from ir import evaluer
from symboles import CompileError
from syntax import parse

PARTIE1 = Path(__file__).resolve().parent.parent / "partie1" / "Session de travail"
sys.path.insert(0, str(PARTIE1))

from dpll import completer, lire_dimacs, verifier_modele          # noqa: E402  (partie I)
from heuristiques import HEURISTIQUES, dpll_h                      # noqa: E402  (partie I)

sys.setrecursionlimit(100_000)


def message_syntaxe(e):
    """Message lisible pour une erreur de syntaxe de Lark."""
    if isinstance(e, UnexpectedToken):
        if e.token.type == "$END":
            return f"ligne {e.line}, colonne {e.column} : fin du texte inattendue"
        attendus = sorted(e.accepts or e.expected)
        return (f"ligne {e.line}, colonne {e.column} : erreur de syntaxe sur '{e.token}'"
                + (f" (attendu : {', '.join(attendus)})" if attendus else ""))
    if isinstance(e, UnexpectedCharacters):
        return f"ligne {e.line}, colonne {e.column} : caractère inattendu '{e.char}'"
    if isinstance(e, UnexpectedEOF):
        return "fin du texte inattendue"
    return str(e)


def compiler(texte):
    """Texte d'un modèle -> (Modele déroulé, FNC). Lève CompileError (syntaxe comprise)."""
    try:
        program = parse(texte)
    except UnexpectedInput as e:
        raise CompileError(message_syntaxe(e)) from None
    table = analyser(program)
    modele = derouler(program, table)
    return modele, FNC(modele)


def resoudre_dimacs(chemin, heur="H4"):
    """Résout un fichier DIMACS avec le solveur de la partie I ; renvoie l'ensemble des
    variables vraies, ou None si la formule est insatisfiable."""
    nb_vars, clauses = lire_dimacs(chemin)
    sat, v = dpll_h(clauses, HEURISTIQUES[heur])
    if not sat:
        return None
    modele = completer(v, nb_vars)
    if not verifier_modele(clauses, modele):
        raise RuntimeError("le solveur a renvoyé un modèle qui ne satisfait pas la FNC")
    return {l for l in modele if l > 0}


def resoudre(modele, fnc, chemin_dimacs=None, heur="H4", commentaires=()):
    """Écrit la FNC, appelle le solveur, décode et vérifie la solution.

    Renvoie None (insatisfiable) ou le dictionnaire Cell -> valeur (bool ou code).
    La solution est vérifiée sur les contraintes déroulées, indépendamment de la FNC.
    """
    temporaire = chemin_dimacs is None
    if temporaire:
        fd, chemin_dimacs = tempfile.mkstemp(suffix=".cnf")
        os.close(fd)
    try:
        with open(chemin_dimacs, "w", encoding="utf-8") as f:
            f.write(fnc.dimacs(commentaires))
        vraies = resoudre_dimacs(chemin_dimacs, heur)
    finally:
        if temporaire:
            os.remove(chemin_dimacs)
    if vraies is None:
        return None
    val = fnc.decoder(vraies)
    fausses = [c for c in modele.contraintes if not evaluer(c, val)]
    if fausses:
        raise RuntimeError(f"{len(fausses)} contrainte(s) violée(s) par la solution décodée")
    return val


def afficher(modele, val):
    """Lignes « nom = valeur », dans l'ordre de déclaration."""
    return [f"{c} = {modele.doms[c].show(val[c])}" for c in modele.cells]
