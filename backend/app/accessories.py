"""Zentrale Definition der Accessoires-Vokabulare.

Unter 'Accessoires' fallen alle persönlichen Gegenstände die man trägt,
aber weder Kleidung noch Uhr noch Duft sind: Schmuck jeder Art, Taschen
und Brillen. Ein gemeinsames Modell mit Typ-Feld ist ausreichend, weil
die Attributmenge sich stark überschneidet und separate Tabs den Segmented
Control unlesbar machen würden.
"""

# ── Typ-Gruppen (fuer den Segmented Control und die Gruppierung in der Liste) ──

ACCESSORY_TYPE_GROUPS = [
    {
        "group": "Schmuck",
        "items": [
            "Ring",
            "Ehering",
            "Verlobungsring",
            "Halskette",
            "Kette",
            "Anhänger",
            "Armband",
            "Armreif",
            "Armkette",
            "Ohrringe",
            "Ohrring (einzeln)",
            "Ohrstecker",
            "Creolen",
            "Brosche",
            "Anstecker",
            "Manschettenknöpfe",
            "Krawattennadel",
            "Krawattenklammer",
            "Körperschmuck",
            "Haarschmuck",
            "Haarreif",
            "Haarspange",
        ],
    },
    {
        "group": "Taschen",
        "items": [
            "Handtasche",
            "Umhängetasche",
            "Schultertasche",
            "Crossbody-Bag",
            "Tote Bag",
            "Clutch",
            "Abendtasche",
            "Minibag",
            "Bucket Bag",
            "Hobo Bag",
            "Shopper",
            "Rucksack",
            "Laptoprucksack",
            "Daypack",
            "Gürteltasche / Fanny Pack",
            "Bauchtasche",
            "Aktentasche",
            "Dokumententasche",
            "Brieftasche",
            "Portemonnaie",
            "Kartenetui",
            "Schlüsseletui",
            "Kulturbeutel",
            "Weekender",
            "Duffle Bag",
            "Sporttasche",
        ],
    },
    {
        "group": "Brillen",
        "items": [
            "Sonnenbrille",
            "Lesebrille",
            "Computerbrille",
            "Korrektionsbrille",
            "Sportbrille",
            "Skibrille",
            "Pilotenbrille",
            "Aviatorbrille",
            "Retro-Brille",
            "Cat-Eye-Brille",
            "Browline-Brille",
            "Hornbrille",
            "Clubmaster",
            "Wayfarer",
        ],
    },
    {
        "group": "Sonstiges",
        "items": [
            "Gürtel",
            "Hosenträger",
            "Einstecktuch",
            "Foulard / Tuch",
            "Haarband",
            "Hut",
            "Cap",
            "Beanie",
            "Mütze",
            "Handschuhe",
            "Schal",
            "Sonstiges Accessoire",
        ],
    },
]

# Flache Liste aller Typen
ACCESSORY_TYPES = [t for g in ACCESSORY_TYPE_GROUPS for t in g["items"]]

# Legacy-Kategorien in clothing_items die in accessories migriert werden
LEGACY_ACCESSORY_CATEGORIES = [
    # Schmuck
    "Schmuck", "Halskette", "Armband", "Ring", "Ohrringe",
    # Taschen
    "Tasche", "Handtasche", "Umhängetasche", "Rucksack", "Clutch",
    # Brillen
    "Brille", "Sonnenbrille",
    # Sonstiges was besser hierher passt als in Kleidung
    "Einstecktuch",
]

# ── Materialien ──

ACCESSORY_METALS = [
    "Gelbgold", "Weißgold", "Roségold", "Platin", "Silber",
    "Edelstahl", "Titan", "Vergoldet", "Versilbert", "Messing",
    "Bronze", "Kupfer", "Palladium", "Rhodiniert",
]

ACCESSORY_LEATHERS = [
    "Kalbsleder", "Rindsleder", "Lambsleder", "Alligatorleder",
    "Krokodilleder", "Straußenleder", "Pferdeleder", "Wildleder",
    "Nubukleder", "Lackleder", "Canvas (Leder-Kombi)",
    "Kunstleder", "Vegan Leather",
]

ACCESSORY_FRAME_MATERIALS = [
    "Acetat", "Nylon", "Kunststoff", "Titan", "Edelstahl",
    "Aluminium", "Carbon", "Horn", "Holz", "Gold-filled",
]

ACCESSORY_MATERIALS_OTHER = [
    "Canvas", "Nylon", "Polyester", "Baumwolle", "Seide",
    "Satin", "Velours", "Jute", "Stroh / Bast", "Kork",
    "Gummi / Silikon", "Keramik", "Emaille", "Acryl",
    "Perlmutt", "Holz", "Bambus", "Metall (unbekannt)", "unbekannt",
]

ACCESSORY_MATERIALS = (
    ACCESSORY_METALS + ACCESSORY_LEATHERS +
    ACCESSORY_FRAME_MATERIALS + ACCESSORY_MATERIALS_OTHER
)

# ── Edelsteine & Besatz ──

ACCESSORY_STONES = [
    "ohne Stein",
    "Diamant",
    "Brillant",
    "Rubin",
    "Saphir",
    "Smaragd",
    "Amethyst",
    "Citrin",
    "Topas",
    "Aquamarin",
    "Perle",
    "Tahiti-Perle",
    "Süßwasserperle",
    "Koralle",
    "Türkis",
    "Onyx",
    "Achat",
    "Opal",
    "Lapislazuli",
    "Mondstein",
    "Granat",
    "Spinell",
    "Tansanit",
    "Zirkonia",
    "Strasssteine",
    "Emaille-Besatz",
    "unbekannt",
]

# ── Brillen-spezifisch ──

LENS_COLORS = [
    "klar",
    "getönt (grau)",
    "getönt (braun)",
    "getönt (grün)",
    "getönt (blau)",
    "getönt (gelb / orange)",
    "verspiegelt (silber)",
    "verspiegelt (gold)",
    "verspiegelt (blau)",
    "verspiegelt (bunt)",
    "photochrom / selbsttönend",
    "polarisiert",
    "Blaulichtfilter",
    "Entspiegelung",
]

UV_PROTECTIONS = [
    "UV400 / kategorie 3",
    "UV400 / kategorie 2",
    "UV400 / kategorie 4 (Gletscher)",
    "CE-zertifiziert",
    "kein UV-Schutz (rein modisch)",
    "unbekannt",
]

FRAME_SHAPES = [
    "rund",
    "oval",
    "eckig / rechteckig",
    "quadratisch",
    "Cat-Eye",
    "Aviator / Tropfen",
    "Browline / Clubmaster",
    "Wayfarer",
    "Geometrisch",
    "Halbrahmen",
    "rahmenlos",
    "Oversized",
    "Narrow / Schmal",
    "Shield / Sportmaske",
]

# ── Taschen-spezifisch ──

BAG_CLOSURES = [
    "Reißverschluss",
    "Magnetverschluss",
    "Druckknopf",
    "Schnappverschluss",
    "Überschlag / Flap",
    "Kordelverschluss",
    "Schnalle",
    "offen",
    "ohne Verschluss",
]

BAG_STRAPS = [
    "kurze Henkel (Tragetasche)",
    "langer Schulterriemen",
    "Umhängeband (fest)",
    "Umhängeband (abnehmbar)",
    "Kettenriemen",
    "Rucksackgurte",
    "kein Riemen",
]

BAG_SIZES = [
    "mini (unter 20 cm)",
    "klein (20–30 cm)",
    "mittel (30–40 cm)",
    "groß (über 40 cm)",
]

# ── Ringweiten / Kettenlängen ──

RING_SIZES_EU = [
    "44", "46", "48", "50", "52", "54", "56", "58", "60",
    "62", "64", "66", "68", "70",
]

NECKLACE_LENGTHS_CM = [
    "35–40 cm (Choker)",
    "42–45 cm (kurz / Princess)",
    "50–55 cm (Matinee)",
    "60–65 cm (Opera)",
    "über 70 cm (Rope)",
]

# ── Stil ──

ACCESSORY_STYLES = [
    "klassisch / zeitlos",
    "minimalistisch",
    "elegant / festlich",
    "business",
    "casual / alltäglich",
    "streetwear",
    "boho / verspielt",
    "vintage / antik",
    "Statement / auffällig",
    "sportlich",
    "romantisch",
    "gothic / edgy",
    "ethnic / handgemacht",
]

ACCESSORY_OCCASIONS = [
    "Alltag",
    "Büro",
    "Business",
    "Formell",
    "Abend",
    "Party",
    "Club",
    "Hochzeit",
    "Feier",
    "Date",
    "Outdoor",
    "Sport",
    "Strand / Urlaub",
    "Zuhause",
]

# ── Zustand ──

ACCESSORY_CONDITIONS = [
    "neu",
    "ungetragen",
    "sehr gut",
    "gut",
    "gebraucht",
    "restauriert",
    "defekt",
]

# ── Bekannte Marken (kanonische Schreibweise) ──

ACCESSORY_BRANDS = [
    # Schmuck
    "Bulgari",
    "Cartier",
    "Chopard",
    "Georg Jensen",
    "Gucci",
    "Hermès",
    "Pandora",
    "Swarovski",
    "Thomas Sabo",
    "Tiffany & Co.",
    "Van Cleef & Arpels",
    # Taschen
    "Acne Studios",
    "Balenciaga",
    "Bottega Veneta",
    "Burberry",
    "Calvin Klein",
    "Celine",
    "Chanel",
    "Coach",
    "Dior",
    "Furla",
    "Gucci",
    "Hermès",
    "Hugo Boss",
    "Kate Spade",
    "Loewe",
    "Louis Vuitton",
    "Marc Jacobs",
    "MCM",
    "Michael Kors",
    "Mulberry",
    "Prada",
    "Saint Laurent",
    "Ted Baker",
    "Tommy Hilfiger",
    "Valentino",
    "Versace",
    # Brillen
    "Ace & Tate",
    "Carrera",
    "Chanel",
    "Christian Dior",
    "Gucci",
    "Lindberg",
    "Maui Jim",
    "Mykita",
    "Oliver Peoples",
    "Oakley",
    "Persol",
    "Prada",
    "Ray-Ban",
    "Tom Ford",
    "Versace",
    "Warby Parker",
    # Lederwaren / Gürtel / sonstiges
    "Anderson's",
    "Azzaro",
    "Dunhill",
    "Ermenegildo Zegna",
    "Gucci",
    "Montblanc",
    "Salvatore Ferragamo",
]
# Duplikate durch mehrere Kategorien entfernen
ACCESSORY_BRANDS = list(dict.fromkeys(ACCESSORY_BRANDS))

# ── Shot-Hinweise für die Erfassung ──

ACCESSORY_SHOT_HINTS = {
    "Schmuck": [
        {"icon": "💍", "label": "Vorderseite", "hint": "Das Hauptbild"},
        {"icon": "🔍", "label": "Detail/Stein", "hint": "Punze oder Stempel"},
        {"icon": "📏", "label": "Größenkontext", "hint": "Neben Münze o.ä."},
        {"icon": "🏷️", "label": "Zertifikat", "hint": "Echtheitsstempel"},
    ],
    "Taschen": [
        {"icon": "👜", "label": "Vorderseite", "hint": "Das Hauptbild"},
        {"icon": "🔄", "label": "Rückseite", "hint": "Details hinten"},
        {"icon": "📂", "label": "Innenraum", "hint": "Fächer und Aufteilung"},
        {"icon": "🏷️", "label": "Logo/Prägung", "hint": "Echtheitsmerkmal"},
    ],
    "Brillen": [
        {"icon": "👓", "label": "Frontal", "hint": "Das Hauptbild"},
        {"icon": "↙️", "label": "Seite", "hint": "Bügeldesign"},
        {"icon": "🔍", "label": "Prägung", "hint": "Modell & Maße"},
    ],
    "Sonstiges": [
        {"icon": "✨", "label": "Vorderseite", "hint": "Das Hauptbild"},
        {"icon": "🔄", "label": "Rückseite", "hint": "Details"},
        {"icon": "🏷️", "label": "Etikett", "hint": "Material & Marke"},
    ],
}


def accessory_group(type_value: str) -> str:
    """Gibt die Gruppe ('Schmuck', 'Taschen', 'Brillen', 'Sonstiges') fuer einen Typ zurueck."""
    for grp in ACCESSORY_TYPE_GROUPS:
        if type_value in grp["items"]:
            return grp["group"]
    return "Sonstiges"


def shot_hints_for(type_value: str) -> list[dict]:
    """Passende Shot-Hinweise fuer einen Accessoire-Typ."""
    grp = accessory_group(type_value)
    return ACCESSORY_SHOT_HINTS.get(grp, ACCESSORY_SHOT_HINTS["Sonstiges"])
