"""Outils communs aux scripts de la question 6 : chemins, modèles, résolution, mesures."""

import os
import sys
import tempfile
import time
from pathlib import Path

ICI = Path(__file__).resolve().parent
PARTIE2 = ICI.parent
PARTIE1 = PARTIE2.parent / "partie1" / "Session de travail"
for p in (str(ICI), str(PARTIE2), str(PARTIE1)):
    if p not in sys.path:
        sys.path.insert(0, p)

from generateur import generer_fichier                       # noqa: E402  (partie I)
from grille_vers_csp import modele                           # noqa: E402
from mesures import mesurer                                  # noqa: E402  (partie I, question 5)
from meowdoku import lire_grille                             # noqa: E402  (partie I)
from solveur import afficher, compiler, resoudre             # noqa: E402
from verifier import verifier                                # noqa: E402

REGLES = ICI / "regles"
GRILLES = ICI / "grilles"
GRILLE_ENONCE = PARTIE1 / "grilles" / "grille_enonce.txt"

MODELES = {
    "modele1": REGLES / "modele1.csp",
    "modele2": REGLES / "modele2.csp",
    "modele2_redondant": REGLES / "modele2_redondant.csp",
    "modele2_general": REGLES / "modele2_general.csp",
}


def grille_generee(n, graine):
    """Grille N x N à N régions de la partie I (generateur.py), créée si besoin."""
    GRILLES.mkdir(exist_ok=True)
    chemin = GRILLES / f"meow_{n:02d}_{graine}.txt"
    if not chemin.exists():
        generer_fichier(n, graine, str(chemin))
    return chemin


def sortie_solve(texte):
    """Sortie de `csp.py --solve` pour le modèle texte (même format, calculée sur place)."""
    m, fnc = compiler(texte)
    val = resoudre(m, fnc)
    if val is None:
        return "s UNSATISFIABLE\n"
    return "s SATISFIABLE\n" + "\n".join(afficher(m, val)) + "\n"


def resoudre_et_verifier(chemin_grille, nom_modele):
    """(statut, erreurs du vérificateur indépendant, durée) pour une grille et un modèle."""
    texte = modele(str(chemin_grille), MODELES[nom_modele])
    t0 = time.perf_counter()
    sortie = sortie_solve(texte)
    duree = time.perf_counter() - t0
    statut = sortie.split("\n", 1)[0][2:]
    erreurs = verifier(lire_grille(str(chemin_grille)), sortie) if statut == "SATISFIABLE" else []
    return statut, erreurs, duree


def mesure(chemin_grille, nom_modele, heur="H4d", limite=None):
    """Compile, écrit le DIMACS, puis mesure la résolution avec l'instrumentation de la
    partie I (mesures.mesurer : décisions, retours arrière, propagations, temps)."""
    texte = modele(str(chemin_grille), MODELES[nom_modele])
    t0 = time.perf_counter()
    m, fnc = compiler(texte)
    t_compil = time.perf_counter() - t0
    fd, chemin = tempfile.mkstemp(suffix=".cnf")
    os.close(fd)
    try:
        Path(chemin).write_text(fnc.dimacs(), encoding="utf-8")
        r = mesurer(chemin, heur, limite=limite)
    finally:
        os.remove(chemin)
    r.update(variables=fnc.nb_vars, clauses=len(fnc.clauses),
             litteraux=sum(len(c) for c in fnc.clauses), compilation=t_compil)
    return r
