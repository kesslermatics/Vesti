"""Zentrale Definition der Garderoben-Kategorien und Metadaten-Optionen.

Diese Werte werden sowohl fuer die KI-Extraktion (als erlaubte Werte)
als auch im Frontend zur Bestaetigung / Bearbeitung verwendet.
"""

# Hauptkategorien eines Kleidungsstuecks
CATEGORIES = [
    "Oberteil",
    "Hemd",
    "T-Shirt",
    "Pullover",
    "Jacke",
    "Mantel",
    "Hose",
    "Jeans",
    "Shorts",
    "Rock",
    "Kleid",
    "Anzug",
    "Schuhe",
    "Guertel",
    "Muetze",
    "Accessoire",
    "Sonstiges",
]

# Stil / Anlass-Charakter
STYLES = [
    "elegant",
    "schick",
    "leger",
    "sportlich",
    "business",
    "casual",
    "festlich",
    "vintage",
]

# Anlaesse fuer die die das Teil geeignet ist
OCCASIONS = [
    "Alltag",
    "Buero",
    "Sport",
    "Party",
    "Date",
    "Hochzeit",
    "Urlaub",
    "Zuhause",
]

# Passende Jahreszeiten
SEASONS = [
    "Fruehling",
    "Sommer",
    "Herbst",
    "Winter",
    "ganzjaehrig",
]

# Materialien / Texturen
MATERIALS = [
    "Baumwolle",
    "Leinen",
    "Wolle",
    "Denim",
    "Leder",
    "Seide",
    "Polyester",
    "Strick",
    "Fleece",
    "unbekannt",
]
