"""Générateur de grilles Meowdoku N x N à N régions, possédant au moins une solution.

Méthode : (1) on place d'abord N chats formant une configuration licite,
(2) chaque chat est le germe d'une région, qu'on fait grandir case par case
jusqu'à couvrir toute la grille.

Usage en ligne de commande :
    python generateur.py N [graine] [fichier_sortie]
"""
import random
import sys
from string import ascii_uppercase

from meowdoku import Grille, ecrire_grille


def placer_chats(N, rng):
    """Un chat par ligne et par colonne, sans chats adjacents.

    On place les chats ligne par ligne en essayant les colonnes dans un ordre
    aléatoire ; en cas d'impasse, on revient sur la ligne précédente.
    Renvoie col (col[i] = colonne du chat de la ligne i, indices 0..N-1) ou None.
    """
    col = [None] * N
    libres = set(range(N))

    def placer(i):
        if i == N:
            return True
        candidats = [c for c in sorted(libres) if i == 0 or abs(c - col[i - 1]) >= 2]
        rng.shuffle(candidats)
        for c in candidats:
            col[i] = c
            libres.remove(c)
            if placer(i + 1):
                return True
            libres.add(c)          # impasse : on annule ce choix et on essaie le suivant
        return False

    return col if placer(0) else None


def faire_pousser_regions(N, chats, rng):
    """Partition de la grille en régions connexes contenant chacune un seul chat.

    region[i][j] = numéro de région ; à chaque étape on choisit une région au hasard
    et on lui ajoute une case libre voisine (haut, bas, gauche, droite).
    """
    region = [[None] * N for _ in range(N)]
    bord = []                                   # bord[k] = cases candidates pour la région k
    for k, (i, j) in enumerate(chats):
        region[i][j] = k
        bord.append(voisins(i, j, N))
    actives = list(range(len(chats)))
    reste = N * N - len(chats)
    while reste:
        k = rng.choice(actives)
        if not bord[k]:                        # région bloquée : elle ne grandit plus
            actives.remove(k)
            continue
        i, j = bord[k].pop(rng.randrange(len(bord[k])))
        if region[i][j] is None:
            region[i][j] = k
            bord[k].extend(voisins(i, j, N))
            reste -= 1
    return region


def voisins(i, j, N):
    return [(a, b) for a, b in ((i - 1, j), (i + 1, j), (i, j - 1), (i, j + 1))
            if 0 <= a < N and 0 <= b < N]


def nom_zone(k):
    """A, B, ..., Z, AA, AB, ..."""
    nom = ""
    k += 1
    while k:
        k, r = divmod(k - 1, 26)
        nom = ascii_uppercase[r] + nom
    return nom


def generer_grille(N, graine=None):
    """Renvoie (grille, chats) ; chats = solution construite, cases (i, j) à partir de 1."""
    rng = random.Random(graine)
    col = placer_chats(N, rng)
    if col is None:
        raise ValueError(f"aucune configuration licite pour N = {N} (impossible pour N = 2, 3)")
    chats = [(i, col[i]) for i in range(N)]
    region = faire_pousser_regions(N, chats, rng)
    zones = [nom_zone(k) for k in range(N)]
    cases = [[zones[region[i][j]] for j in range(N)] for i in range(N)]
    return Grille(N, N, zones, cases), [(i + 1, j + 1) for i, j in chats]


def generer_fichier(N, graine, chemin):
    grille, chats = generer_grille(N, graine)
    ecrire_grille(grille, chemin, commentaires=[
        f"Grille generee : N = M = K = {N}, graine = {graine}",
        "Solution construite : " + ", ".join(
            f"{grille.region_de(i, j)} {i} {j}" for i, j in chats),
    ])
    return grille, chats


if __name__ == "__main__":
    if not 2 <= len(sys.argv) <= 4:
        sys.exit("usage : python generateur.py N [graine] [fichier_sortie]")
    N = int(sys.argv[1])
    graine = int(sys.argv[2]) if len(sys.argv) > 2 else None
    sortie = sys.argv[3] if len(sys.argv) > 3 else f"grille_{N}x{N}.txt"
    generer_fichier(N, graine, sortie)
    print(f"grille écrite dans {sortie}")
