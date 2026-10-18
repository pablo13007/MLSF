"""Meowdoku : lecture/écriture de grilles, encodage CNF, format DIMACS, vérification.

Usage en ligne de commande :
    python meowdoku.py grille.txt sortie.cnf
"""
import sys
from itertools import combinations


# ---------------------------------------------------------------------------
# Grilles
# ---------------------------------------------------------------------------

class Grille:
    """Grille N x M découpée en régions.

    zones : liste des noms de régions (ordre de la ligne ZONES)
    cases : cases[i][j] = nom de la région de la case (i+1, j+1)
    """

    def __init__(self, N, M, zones, cases):
        self.N, self.M = N, M
        self.zones = zones
        self.cases = cases

    def regions(self):
        """Dictionnaire nom de région -> liste des cases (i, j), indices à partir de 1."""
        reg = {z: [] for z in self.zones}
        for i in range(self.N):
            for j in range(self.M):
                reg[self.cases[i][j]].append((i + 1, j + 1))
        return reg

    def region_de(self, i, j):
        return self.cases[i - 1][j - 1]


def lire_grille(chemin):
    """Lit un fichier grille (format de la figure 1b) et vérifie sa cohérence."""
    with open(chemin, encoding="utf-8") as f:
        lignes = [l.split() for l in f if l.strip() and not l.startswith("c")]

    if not lignes or lignes[0][0] != "GRID" or len(lignes[0]) != 3:
        raise ValueError("ligne 'GRID N M' attendue")
    N, M = int(lignes[0][1]), int(lignes[0][2])
    if len(lignes) < 2 or lignes[1][0] != "ZONES":
        raise ValueError("ligne 'ZONES ...' attendue")
    zones = lignes[1][1:]
    if len(set(zones)) != len(zones):
        raise ValueError("noms de régions en double")

    cases = lignes[2:2 + N]          # les lignes suivantes (solution éventuelle) sont ignorées
    if len(cases) != N or any(len(l) != M for l in cases):
        raise ValueError(f"{N} lignes de {M} cases attendues")
    inconnues = {z for l in cases for z in l} - set(zones)
    if inconnues:
        raise ValueError(f"régions non déclarées : {sorted(inconnues)}")
    grille = Grille(N, M, zones, cases)
    vides = [z for z, c in grille.regions().items() if not c]
    if vides:
        raise ValueError(f"régions vides : {vides}")
    return grille


def ecrire_grille(grille, chemin, commentaires=()):
    """Écrit une grille au format de la figure 1b."""
    with open(chemin, "w", encoding="utf-8") as f:
        for c in commentaires:
            f.write(f"c {c}\n")
        f.write(f"GRID {grille.N} {grille.M}\n")
        f.write("ZONES " + " ".join(grille.zones) + "\n\n")
        for ligne in grille.cases:
            f.write(" ".join(ligne) + "\n")


def afficher(grille, chats=()):
    """Affichage texte : nom de région de chaque case, '*' à la place des chats."""
    chats = set(chats)
    largeur = max(len(z) for z in grille.zones)
    for i in range(1, grille.N + 1):
        print(" ".join(("*" if (i, j) in chats else grille.region_de(i, j)).rjust(largeur)
                       for j in range(1, grille.M + 1)))


# ---------------------------------------------------------------------------
# Encodage CNF
# ---------------------------------------------------------------------------

def var(i, j, M):
    """Numéro DIMACS de la variable x_{i,j} (i, j à partir de 1)."""
    return (i - 1) * M + j


def case(v, M):
    """Case (i, j) associée au numéro de variable v."""
    return (v - 1) // M + 1, (v - 1) % M + 1


def grille_vers_cnf(grille):
    """Renvoie (nb_variables, clauses) ; une clause est une liste d'entiers DIMACS."""
    N, M = grille.N, grille.M
    x = lambda i, j: var(i, j, M)
    clauses, deja_vues = [], set()

    def ajouter(clause):
        cle = tuple(sorted(clause))
        if cle not in deja_vues:            # évite les doublons entre familles
            deja_vues.add(cle)
            clauses.append(clause)

    # (1) au plus un chat par ligne
    for i in range(1, N + 1):
        for j, k in combinations(range(1, M + 1), 2):
            ajouter([-x(i, j), -x(i, k)])
    # (2) au plus un chat par colonne
    for j in range(1, M + 1):
        for i, k in combinations(range(1, N + 1), 2):
            ajouter([-x(i, j), -x(k, j)])
    # (3) exactement un chat par région : au moins un + au plus un
    for cases in grille.regions().values():
        ajouter([x(i, j) for i, j in cases])
        for (i, j), (k, l) in combinations(cases, 2):
            ajouter([-x(i, j), -x(k, l)])
    # (4) pas de chats en diagonale (horizontal/vertical déjà couverts par (1) et (2))
    for i in range(1, N):
        for j in range(1, M + 1):
            for l in (j - 1, j + 1):
                if 1 <= l <= M:
                    ajouter([-x(i, j), -x(i + 1, l)])
    return N * M, clauses


def ecrire_dimacs(nb_vars, clauses, chemin, commentaires=()):
    with open(chemin, "w", encoding="utf-8") as f:
        for c in commentaires:
            f.write(f"c {c}\n")
        f.write(f"p cnf {nb_vars} {len(clauses)}\n")
        for clause in clauses:
            f.write(" ".join(map(str, clause)) + " 0\n")


def convertir(chemin_grille, chemin_cnf):
    """Programme de la question 1 : fichier grille -> fichier DIMACS."""
    grille = lire_grille(chemin_grille)
    nb_vars, clauses = grille_vers_cnf(grille)
    ecrire_dimacs(nb_vars, clauses, chemin_cnf, commentaires=[
        f"Meowdoku : {chemin_grille}",
        f"GRID {grille.N} {grille.M}, {len(grille.zones)} regions",
        f"variable x_(i,j) = (i-1)*{grille.M} + j  (chat sur la case (i,j))",
    ])
    return nb_vars, len(clauses)


# ---------------------------------------------------------------------------
# Vérifications
# ---------------------------------------------------------------------------

def satisfait(clauses, vraies):
    """True si la valuation (ensemble des variables vraies) satisfait toutes les clauses."""
    return all(any((l > 0) == (abs(l) in vraies) for l in c) for c in clauses)


def chats_depuis_valuation(vraies, M):
    """Positions des chats associées à l'ensemble des variables vraies."""
    return {case(v, M) for v in vraies}


def verifier_solution(grille, chats):
    """Renvoie la liste des règles violées (liste vide <=> configuration licite)."""
    chats = set(chats)
    erreurs = []
    for i in range(1, grille.N + 1):
        if sum(1 for (a, _) in chats if a == i) > 1:
            erreurs.append(f"ligne {i} : plusieurs chats")
    for j in range(1, grille.M + 1):
        if sum(1 for (_, b) in chats if b == j) > 1:
            erreurs.append(f"colonne {j} : plusieurs chats")
    for z, cases in grille.regions().items():
        n = sum(1 for c in cases if c in chats)
        if n != 1:
            erreurs.append(f"région {z} : {n} chat(s)")
    for (i, j) in chats:
        for (k, l) in chats:
            if (i, j) < (k, l) and abs(i - k) <= 1 and abs(j - l) <= 1:
                erreurs.append(f"chats adjacents ({i},{j}) et ({k},{l})")
    return erreurs


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("usage : python meowdoku.py grille.txt sortie.cnf")
    nv, nc = convertir(sys.argv[1], sys.argv[2])
    print(f"{sys.argv[2]} : {nv} variables, {nc} clauses")
