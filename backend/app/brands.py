"""Marken-Normalisierung, damit gleiche Marken nicht mehrfach angelegt werden.

Beispiel: "youngla", "Young LA" und "YOUNGLA" sollen alle auf die bereits
vorhandene Schreibweise "YoungLA" gemappt werden.
"""

import re

# Bekannte Marken mit kanonischer Schreibweise als Startvorschlaege
KNOWN_BRANDS = [
    "Adidas",
    "Alpha Industries",
    "ARKET",
    "Asics",
    "Bershka",
    "Boss",
    "Calvin Klein",
    "Carhartt",
    "COS",
    "Converse",
    "Diesel",
    "Dr. Martens",
    "Edited",
    "Esprit",
    "Fila",
    "G-Star",
    "Gant",
    "Gymshark",
    "H&M",
    "Hollister",
    "Jack & Jones",
    "Lacoste",
    "Levi's",
    "Mango",
    "Marc O'Polo",
    "Massimo Dutti",
    "New Balance",
    "Nike",
    "Only",
    "Patagonia",
    "Pull&Bear",
    "Puma",
    "Ralph Lauren",
    "Reebok",
    "s.Oliver",
    "Salomon",
    "Scotch & Soda",
    "Stradivarius",
    "The North Face",
    "Tommy Hilfiger",
    "Uniqlo",
    "Vans",
    "Veja",
    "Weekday",
    "YoungLA",
    "Zara",
]


def normalize_key(brand: str) -> str:
    """Vergleichsschluessel: Kleinschreibung, ohne Sonderzeichen und Leerzeichen.

    "Young LA" -> "youngla", "Marc O'Polo" -> "marcopolo", "H&M" -> "hm"
    """
    return re.sub(r"[^a-z0-9]", "", brand.lower())


def canonicalize(brand: str, existing: list[str]) -> str:
    """Gibt die kanonische Schreibweise zurueck.

    Existiert bereits eine Marke mit gleichem Schluessel, wird deren
    Schreibweise verwendet. Sonst wird die Eingabe getrimmt uebernommen.
    """
    cleaned = " ".join(brand.split())  # doppelte Leerzeichen entfernen
    if not cleaned:
        return ""

    key = normalize_key(cleaned)
    if not key:
        return cleaned

    # Zuerst in den bereits vom Nutzer verwendeten Marken suchen
    for candidate in existing:
        if normalize_key(candidate) == key:
            return candidate

    # Dann in der Liste bekannter Marken
    for candidate in KNOWN_BRANDS:
        if normalize_key(candidate) == key:
            return candidate

    return cleaned
