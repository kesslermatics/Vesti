"""Zentrale Definition der Parfuem-Vokabulare.

Analog zu categories.py: diese Werte dienen der KI als erlaubte Werte und
dem Frontend als Auswahllisten.
"""

# Konzentration / Produktart
FRAGRANCE_CONCENTRATIONS = [
    "Eau de Cologne",
    "Eau Fraîche",
    "Eau de Toilette",
    "Eau de Parfum",
    "Eau de Parfum Intense",
    "Parfum / Extrait",
    "Parfum Öl",
    "Body Mist",
    "Aftershave",
    "unbekannt",
]

# Duftfamilien
FRAGRANCE_FAMILIES = [
    "Frisch / Zitrisch",
    "Aquatisch / Marin",
    "Grün",
    "Fruchtig",
    "Blumig",
    "Weiß-Blumig",
    "Aromatisch / Kräutrig",
    "Fougère",
    "Chypre",
    "Holzig",
    "Erdig / Vetiver",
    "Gewürzig",
    "Orientalisch / Amber",
    "Gourmand",
    "Ledrig",
    "Tabak",
    "Moschus",
    "Pudrig",
    "Räucherig / Weihrauch",
]

# Duftnoten, nach Sinngruppen sortiert (fuer gruppierte Auswahl im Frontend)
NOTE_GROUPS = [
    {
        "group": "Zitrus",
        "items": [
            "Bergamotte",
            "Zitrone",
            "Limette",
            "Grapefruit",
            "Orange",
            "Blutorange",
            "Mandarine",
            "Yuzu",
            "Petitgrain",
            "Neroli",
        ],
    },
    {
        "group": "Früchte",
        "items": [
            "Apfel",
            "Birne",
            "Pfirsich",
            "Aprikose",
            "Pflaume",
            "Kirsche",
            "Himbeere",
            "Erdbeere",
            "Schwarze Johannisbeere",
            "Feige",
            "Ananas",
            "Melone",
            "Mango",
            "Litschi",
            "Rhabarber",
        ],
    },
    {
        "group": "Blüten",
        "items": [
            "Rose",
            "Jasmin",
            "Tuberose",
            "Orangenblüte",
            "Ylang-Ylang",
            "Maiglöckchen",
            "Veilchen",
            "Iris",
            "Lavendel",
            "Geranie",
            "Magnolie",
            "Freesie",
            "Osmanthus",
            "Narzisse",
            "Mimose",
            "Pfingstrose",
            "Lotus",
        ],
    },
    {
        "group": "Kräuter & Grün",
        "items": [
            "Basilikum",
            "Minze",
            "Salbei",
            "Rosmarin",
            "Thymian",
            "Estragon",
            "Grüner Tee",
            "Schwarzer Tee",
            "Grüne Blätter",
            "Frisch gemähtes Gras",
            "Tomatenblatt",
            "Gurke",
            "Bambus",
            "Galbanum",
        ],
    },
    {
        "group": "Gewürze",
        "items": [
            "Schwarzer Pfeffer",
            "Rosa Pfeffer",
            "Kardamom",
            "Zimt",
            "Nelke",
            "Muskatnuss",
            "Ingwer",
            "Safran",
            "Kreuzkümmel",
            "Koriander",
            "Anis",
            "Sternanis",
        ],
    },
    {
        "group": "Hölzer",
        "items": [
            "Sandelholz",
            "Zedernholz",
            "Vetiver",
            "Patchouli",
            "Oud / Agarholz",
            "Guajakholz",
            "Kaschmirholz",
            "Zypresse",
            "Wacholder",
            "Kiefer",
            "Birkenteer",
            "Papyrus",
            "Treibholz",
        ],
    },
    {
        "group": "Harze & Balsame",
        "items": [
            "Weihrauch",
            "Myrrhe",
            "Amber",
            "Ambroxan",
            "Labdanum",
            "Benzoe",
            "Styrax",
            "Elemi",
            "Tolubalsam",
            "Opoponax",
        ],
    },
    {
        "group": "Süß & Gourmand",
        "items": [
            "Vanille",
            "Tonkabohne",
            "Karamell",
            "Honig",
            "Praline",
            "Schokolade",
            "Kakao",
            "Kaffee",
            "Mandel",
            "Haselnuss",
            "Kokos",
            "Zuckerwatte",
            "Rum",
            "Whisky",
            "Lakritz",
        ],
    },
    {
        "group": "Moschus & Animalisch",
        "items": [
            "Weißer Moschus",
            "Moschus",
            "Ambra",
            "Zibet",
            "Castoreum",
            "Hyrax",
        ],
    },
    {
        "group": "Leder & Tabak",
        "items": [
            "Leder",
            "Wildleder",
            "Tabakblatt",
            "Honigtabak",
            "Pfeifentabak",
        ],
    },
    {
        "group": "Marin & Mineralisch",
        "items": [
            "Meeresnote",
            "Salz",
            "Algen",
            "Seetang",
            "Mineralische Note",
            "Feuerstein",
            "Regen / Petrichor",
            "Ozon",
            "Calone",
        ],
    },
    {
        "group": "Sonstige",
        "items": [
            "Pudrige Note",
            "Iso E Super",
            "Aldehyde",
            "Kreide",
            "Metallische Note",
            "Wäscheduft",
            "Cashmeran",
        ],
    },
]

# Flache Liste aller Noten (fuer die KI und Validierung)
FRAGRANCE_NOTES = [note for grp in NOTE_GROUPS for note in grp["items"]]

# Projektion / Duftwolke
FRAGRANCE_SILLAGES = [
    "Skin Scent (sehr dezent)",
    "dezent",
    "moderat",
    "kräftig",
    "raumfüllend",
]

# Haltbarkeit auf der Haut
FRAGRANCE_LONGEVITIES = [
    "kurz (unter 3 h)",
    "mittel (3–6 h)",
    "lang (6–10 h)",
    "sehr lang (über 10 h)",
]

# Tageszeit
FRAGRANCE_TIMES = [
    "Tag",
    "Abend",
    "Nacht",
    "Universal",
]

# Zielgruppe laut Hersteller
FRAGRANCE_AUDIENCES = [
    "Herren",
    "Damen",
    "Unisex",
]

# Jahreszeiten (deckungsgleich mit der Kleidung, damit Auswertungen zusammenpassen)
FRAGRANCE_SEASONS = [
    "Frühling",
    "Sommer",
    "Herbst",
    "Winter",
    "ganzjährig",
]

# Anlaesse
FRAGRANCE_OCCASIONS = [
    "Alltag",
    "Büro",
    "Business",
    "Formell",
    "Abendveranstaltung",
    "Hochzeit",
    "Date",
    "Party",
    "Club",
    "Sport",
    "Freizeit",
    "Urlaub",
    "Strand",
    "Zuhause",
]

# Gaengige Flakongroessen in ml
FRAGRANCE_BOTTLE_SIZES = [5, 10, 15, 20, 30, 50, 75, 100, 125, 150, 200]

# Bekannte Duefthaeuser als Startvorschlaege (kanonische Schreibweise)
FRAGRANCE_BRANDS = [
    "Acqua di Parma",
    "Amouage",
    "Armani",
    "Azzaro",
    "Bond No. 9",
    "Boss",
    "Bottega Veneta",
    "Burberry",
    "By Kilian",
    "Byredo",
    "Calvin Klein",
    "Carolina Herrera",
    "Cartier",
    "Chanel",
    "Chloé",
    "Clive Christian",
    "Comme des Garçons",
    "Creed",
    "Diptyque",
    "Dior",
    "Dolce & Gabbana",
    "Dries Van Noten",
    "Escentric Molecules",
    "Estée Lauder",
    "Etat Libre d'Orange",
    "Frederic Malle",
    "Givenchy",
    "Goldfield & Banks",
    "Gucci",
    "Guerlain",
    "Hermès",
    "Initio",
    "Issey Miyake",
    "Jean Paul Gaultier",
    "Jo Malone London",
    "Juliette Has a Gun",
    "Kayali",
    "Lancôme",
    "Lattafa",
    "Le Labo",
    "Loewe",
    "Louis Vuitton",
    "Maison Crivelli",
    "Maison Francis Kurkdjian",
    "Maison Margiela",
    "Mancera",
    "Marc Jacobs",
    "Memo Paris",
    "Montale",
    "Mugler",
    "Narciso Rodriguez",
    "Nasomatto",
    "Nishane",
    "Paco Rabanne",
    "Parfums de Marly",
    "Penhaligon's",
    "Prada",
    "Ralph Lauren",
    "Roja Parfums",
    "Serge Lutens",
    "Tiziana Terenzi",
    "Tom Ford",
    "Valentino",
    "Versace",
    "Viktor & Rolf",
    "Xerjoff",
    "Yves Saint Laurent",
    "Zadig & Voltaire",
]

# Empfohlene Aufnahmen bei der Erfassung (fuer das Frontend)
FRAGRANCE_SHOT_HINTS = [
    {"icon": "🧴", "label": "Flakon", "hint": "Das Hauptbild"},
    {"icon": "🏷️", "label": "Etikett", "hint": "Name & Konzentration"},
    {"icon": "📦", "label": "Verpackung", "hint": "Füllmenge"},
    {"icon": "🔢", "label": "Batch-Code", "hint": "Charge & Alter"},
]

# Haltbarkeit nach dem Oeffnen, grob nach Duftfamilie in Monaten.
# Zitrische und frische Duefte kippen deutlich schneller als schwere Basen.
SHELF_LIFE_MONTHS = {
    "Frisch / Zitrisch": 24,
    "Aquatisch / Marin": 30,
    "Grün": 30,
    "Fruchtig": 30,
    "Blumig": 36,
    "Weiß-Blumig": 36,
    "Aromatisch / Kräutrig": 30,
    "Fougère": 36,
    "Chypre": 48,
    "Holzig": 48,
    "Erdig / Vetiver": 48,
    "Gewürzig": 42,
    "Orientalisch / Amber": 60,
    "Gourmand": 48,
    "Ledrig": 60,
    "Tabak": 60,
    "Moschus": 48,
    "Pudrig": 36,
    "Räucherig / Weihrauch": 60,
}

DEFAULT_SHELF_LIFE_MONTHS = 36


def shelf_life_months(family: str) -> int:
    """Erwartete Haltbarkeit nach dem Oeffnen in Monaten."""
    return SHELF_LIFE_MONTHS.get(family, DEFAULT_SHELF_LIFE_MONTHS)
