"""Questions 6.3, 6.4 et 6.6 : campagne de mesures sur des grilles de tailles croissantes.

Le compilateur et le solveur sont les mêmes pour toutes les mesures ; seuls changent le
fichier de règles (le modèle) et l'heuristique du solveur. Les mesures sont celles de la
partie I, question 5 (mesures.mesurer) : statut, décisions, retours arrière, propagations
unitaires, temps CPU de résolution, plus la taille de la FNC et le temps de compilation.

    python q6_meowdoku/experiences.py            # lance la campagne -> resultats_q6.json
    python q6_meowdoku/experiences.py --resume   # tableaux de synthèse à partir du JSON

Campagnes :
    6.3/6.6  modele1 / modele2,             heuristiques H0 (aléatoire), H1, H4d, N = 6..14
    6.4      modele2 / modele2_redondant,   heuristiques H1, H4d,             N = 6..20
"""

import argparse
import json
import statistics
from pathlib import Path

from commun import grille_generee, mesure

ICI = Path(__file__).resolve().parent
RESULTATS = ICI / "resultats_q6.json"
GRAINES = [0, 1, 2]
LIMITE = 60

CAMPAGNES = [
    (range(6, 15, 2), ["modele1", "modele2"], ["H0", "H1", "H4d"]),
    (range(6, 21, 2), ["modele2", "modele2_redondant"], ["H1", "H4d"]),
]


def taches():
    vues = set()
    for tailles, modeles, heurs in CAMPAGNES:
        for n in tailles:
            for g in GRAINES:
                for m in modeles:
                    for h in heurs:
                        if (n, g, m, h) not in vues:
                            vues.add((n, g, m, h))
                            yield n, g, m, h


def executer(tache):
    n, g, m, h = tache
    r = mesure(grille_generee(n, g), m, h, limite=LIMITE)
    r.update(n=n, graine=g, modele=m, heur=h)
    print(f"N={n:2} graine={g} {m:18} {h:4} {r['statut']:7} décisions={r['decisions']:6} "
          f"cpu={r['cpu']:6.2f} s", flush=True)
    return r


def resume(resultats):
    """Médiane sur les graines, par taille ; TIMEOUT compté à la limite."""
    def table(modeles, heurs, champ, titre):
        print(f"\n{titre}")
        tailles = sorted({r["n"] for r in resultats if r["modele"] in modeles})
        entetes = [f"{m}/{h}" for m in modeles for h in heurs]
        print("N    " + "".join(f"{e:>24}" for e in entetes))
        for n in tailles:
            cases = []
            for m in modeles:
                for h in heurs:
                    rs = [r for r in resultats if (r["n"], r["modele"], r["heur"]) == (n, m, h)]
                    if not rs:
                        cases.append("-")
                        continue
                    med = statistics.median(r[champ] for r in rs)
                    to = sum(r["statut"] == "TIMEOUT" for r in rs)
                    cases.append((f"{med:.2f}" if isinstance(med, float) else f"{med:g}")
                                 + (f" ({to} TO)" if to else ""))
            print(f"{n:<5}" + "".join(f"{c:>24}" for c in cases))

    table(["modele1", "modele2"], ["H0", "H1", "H4d"], "variables", "6.3 : variables")
    table(["modele1", "modele2"], ["H0", "H1", "H4d"], "clauses", "6.3 : clauses")
    table(["modele1", "modele2"], ["H0", "H1", "H4d"], "compilation", "6.3 : compilation (s)")
    table(["modele1", "modele2"], ["H0", "H1", "H4d"], "decisions", "6.3 : décisions (médiane)")
    table(["modele1", "modele2"], ["H0", "H1", "H4d"], "cpu", "6.3 : temps CPU de résolution (s, médiane)")
    table(["modele2", "modele2_redondant"], ["H1", "H4d"], "variables", "6.4 : variables")
    table(["modele2", "modele2_redondant"], ["H1", "H4d"], "decisions", "6.4 : décisions (médiane)")
    table(["modele2", "modele2_redondant"], ["H1", "H4d"], "retours", "6.4 : retours arrière (médiane)")
    table(["modele2", "modele2_redondant"], ["H1", "H4d"], "unitaires", "6.4 : propagations unitaires (médiane)")
    table(["modele2", "modele2_redondant"], ["H1", "H4d"], "cpu", "6.4 : temps CPU de résolution (s, médiane)")
    invalides = [r for r in resultats if r["statut"] == "SAT" and not r["modele_valide"]]
    unsat = [r for r in resultats if r["statut"] == "UNSAT"]
    print(f"\n{len(resultats)} mesures, {len(unsat)} UNSAT (attendu : 0), "
          f"{len(invalides)} modèles invalides (attendu : 0)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--resume", action="store_true", help="synthèse du fichier de résultats")
    args = ap.parse_args()
    if not args.resume:
        resultats = [executer(t) for t in taches()]
        RESULTATS.write_text(json.dumps(resultats, indent=1), encoding="utf-8")
    resume(json.loads(RESULTATS.read_text(encoding="utf-8")))
