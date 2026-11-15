"""Table des symboles (question 3) : types, valeurs énumérées, symboles, erreurs.

Tous les noms (constantes, types, valeurs énumérées, variables, tableaux, indices
de boucle) partagent un même espace de noms. Un nom doit être déclaré avant d'être
utilisé (ordre du texte).
"""

from dataclasses import dataclass


class CompileError(Exception):
    """Erreur de compilation : modèle rejeté avec un message explicatif."""


# Types : "int", "bool", ou "enum T" pour le type énuméré T.
INT, BOOL = "int", "bool"

def enum_type(name):
    return "enum " + name

def type_name(t):
    if t == INT:
        return "un entier"
    if t == BOOL:
        return "un booléen"
    return "une valeur de " + t[5:]


@dataclass(frozen=True, order=True)
class EnumVal:
    """Valeur d'un type énuméré ; ordre (et code) = rang de déclaration."""
    type: str
    index: int
    name: str

    def __str__(self):
        return self.name


def show_value(v):
    if isinstance(v, bool):
        return "true" if v else "false"
    return str(v)


# Dimensions d'un tableau : une taille n (indices 1..n) ou un type énuméré.

@dataclass
class Dim:
    type: str            # type des indices : INT ou enum T
    values: list         # indices valides, dans l'ordre
    text: str            # "1..n" ou "T", pour les messages


# Symboles

@dataclass
class ConstInt:
    value: int

@dataclass
class ConstArray:
    dims: list
    data: dict           # tuple d'indices -> valeur
    elem: str            # type des cases

@dataclass
class EnumType:
    name: str
    values: list         # EnumVal, dans l'ordre

@dataclass
class EnumValue:
    value: EnumVal

@dataclass
class VarSym:
    dom: object          # ir.Dom
    type: str

@dataclass
class ArraySym:
    dims: list
    dom: object
    type: str

@dataclass
class LoopIndex:
    type: str


class Table:
    """Noms globaux, dans l'ordre de déclaration."""

    def __init__(self):
        self.symbols = {}

    def declare(self, name, sym, scope=None):
        if name in self.symbols or (scope and name in scope):
            raise CompileError(f"'{name}' est déjà déclaré")
        self.symbols[name] = sym

    def lookup(self, name, scope=None):
        if scope and name in scope:
            return scope[name]
        if name in self.symbols:
            return self.symbols[name]
        raise CompileError(f"nom non déclaré '{name}'")

    def variables(self):
        """(nom, symbole) des variables et tableaux de variables, dans l'ordre."""
        return [(n, s) for n, s in self.symbols.items() if isinstance(s, (VarSym, ArraySym))]
