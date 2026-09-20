"""Zentrale Definition der Uhren-Vokabulare.

Analog zu categories.py: diese Werte dienen der KI als erlaubte Werte und
dem Frontend als Auswahllisten.
"""

# Uhrentyp / Charakter der Uhr
WATCH_STYLES = [
    "Dress / Elegant",
    "Business",
    "Casual",
    "Sport",
    "Taucheruhr",
    "Fliegeruhr",
    "Feld / Military",
    "GMT / Reise",
    "Chronograph",
    "Rennsport",
    "Skeleton",
    "Vintage",
    "Smartwatch",
    "Digital",
]

# Antrieb
WATCH_MOVEMENTS = [
    "Automatik",
    "Handaufzug",
    "Quarz",
    "Solar",
    "Kinetic",
    "Spring Drive",
    "Mecha-Quarz",
    "Smartwatch",
    "unbekannt",
]

# Gehäusematerial
WATCH_CASE_MATERIALS = [
    "Edelstahl",
    "Edelstahl PVD",
    "Edelstahl DLC",
    "Titan",
    "Gelbgold",
    "Weißgold",
    "Roségold",
    "Platin",
    "Bicolor",
    "Keramik",
    "Bronze",
    "Carbon",
    "Aluminium",
    "Messing",
    "Kunststoff",
    "unbekannt",
]

# Art des Armbands
WATCH_BAND_TYPES = [
    "Gliederarmband",
    "Oyster-Band",
    "Jubilee-Band",
    "Präsidentenband",
    "Milanaise",
    "Mesh",
    "Lederband",
    "Vintage-Leder",
    "Kautschukband",
    "Silikonband",
    "NATO-Band",
    "Perlonband",
    "Textilband",
    "Keramikband",
    "Integriertes Band",
]

# Material des Armbands
WATCH_BAND_MATERIALS = [
    "Edelstahl",
    "Titan",
    "Gold",
    "Keramik",
    "Kalbsleder",
    "Rindsleder",
    "Alligatorleder",
    "Krokodilleder",
    "Straußenleder",
    "Wildleder",
    "Kunstleder",
    "Kautschuk",
    "Silikon",
    "Nylon",
    "Textil",
    "Kunststoff",
    "unbekannt",
]

# Schließe
WATCH_CLASPS = [
    "Dornschließe",
    "Faltschließe",
    "Butterfly-Faltschließe",
    "Sicherheitsfaltschließe",
    "Druckknopfschließe",
    "Klettverschluss",
    "NATO-Durchzug",
    "Gliederverschluss",
    "unbekannt",
]

# Glas
WATCH_CRYSTALS = [
    "Saphirglas",
    "Saphirglas entspiegelt",
    "Mineralglas",
    "Hesalithglas / Acryl",
    "Kunststoffglas",
    "unbekannt",
]

# Zusatzfunktionen
WATCH_COMPLICATIONS = [
    "Datum",
    "Wochentag",
    "Tag & Datum",
    "Großdatum",
    "Jahresanzeige",
    "Ewiger Kalender",
    "Chronograph",
    "Tachymeter",
    "GMT / zweite Zeitzone",
    "Weltzeit",
    "Mondphase",
    "Gangreserveanzeige",
    "Kleine Sekunde",
    "Springende Stunde",
    "Wecker",
    "Tourbillon",
    "Minutenrepetition",
    "Drehbare Lünette",
    "Kompass",
    "Höhenmesser",
    "Schrittzähler",
    "Pulsmesser",
    "GPS",
]

# Anlaesse, zu denen die Uhr passt
WATCH_OCCASIONS = [
    "Alltag",
    "Büro",
    "Business",
    "Formell",
    "Abendveranstaltung",
    "Hochzeit",
    "Sport",
    "Fitness",
    "Outdoor",
    "Wassersport",
    "Tauchen",
    "Reise",
    "Urlaub",
    "Party",
    "Date",
    "Freizeit",
]

# Zustand
WATCH_CONDITIONS = [
    "neu",
    "ungetragen",
    "sehr gut",
    "gut",
    "gebraucht",
    "stark getragen",
    "defekt",
]

# Lieferumfang
WATCH_SETS = [
    "Box & Papiere",
    "nur Box",
    "nur Papiere",
    "ohne Zubehör",
    "unbekannt",
]

# Bekannte Uhrenmarken als Startvorschlaege (kanonische Schreibweise)
WATCH_BRANDS = [
    "A. Lange & Söhne",
    "Alpina",
    "Apple",
    "Audemars Piguet",
    "Baume & Mercier",
    "Bell & Ross",
    "Blancpain",
    "Boss",
    "Breitling",
    "Bremont",
    "Bulova",
    "Cartier",
    "Casio",
    "Certina",
    "Chopard",
    "Christopher Ward",
    "Citizen",
    "Doxa",
    "Emporio Armani",
    "Farer",
    "Fossil",
    "Frederique Constant",
    "Garmin",
    "Girard-Perregaux",
    "Glashütte Original",
    "Grand Seiko",
    "Hamilton",
    "Hublot",
    "IWC Schaffhausen",
    "Jaeger-LeCoultre",
    "Junghans",
    "Longines",
    "Maurice Lacroix",
    "Meistersinger",
    "Mido",
    "Mondaine",
    "Montblanc",
    "Moser & Cie.",
    "Mühle-Glashütte",
    "Nomos Glashütte",
    "Omega",
    "Oris",
    "Panerai",
    "Parmigiani Fleurier",
    "Patek Philippe",
    "Piaget",
    "Rado",
    "Raymond Weil",
    "Richard Mille",
    "Rolex",
    "Samsung",
    "Seiko",
    "Sinn",
    "Skagen",
    "Stowa",
    "Swatch",
    "TAG Heuer",
    "Timex",
    "Tissot",
    "Tudor",
    "Ulysse Nardin",
    "Union Glashütte",
    "Vacheron Constantin",
    "Zenith",
    "Zeppelin",
]

# Empfohlene Aufnahmen bei der Erfassung (fuer das Frontend)
WATCH_SHOT_HINTS = [
    {"icon": "⌚", "label": "Zifferblatt", "hint": "Das Hauptbild"},
    {"icon": "🔄", "label": "Gehäuseboden", "hint": "Referenznummer"},
    {"icon": "🔗", "label": "Armband", "hint": "Band & Schließe"},
    {"icon": "📦", "label": "Box & Papiere", "hint": "Lieferumfang"},
]


def wrist_size_advice(wrist_cm: float | None, case_diameter: float | None) -> str:
    """Grobe Einschaetzung, ob ein Gehaeusedurchmesser zum Handgelenk passt.

    Rein rechnerische Heuristik ohne KI, damit sie sofort verfuegbar ist.
    Faustregel: Gehaeusedurchmesser in mm etwa 22-30 % des Handgelenkumfangs in mm.
    """
    if not wrist_cm or not case_diameter:
        return ""

    wrist_mm = wrist_cm * 10
    ratio = case_diameter / wrist_mm

    # Kalibriert an gaengigen Kombinationen: 36 mm an 16 cm, 40 mm an 18 cm und
    # 44 mm an 20 cm gelten alle als stimmig und liegen bei ratio 0.22 bis 0.23.
    if ratio < 0.195:
        return (
            f"{case_diameter:g} mm wirken an {wrist_cm:g} cm Handgelenk eher klein – "
            "das kann bewusst zurückhaltend aussehen, verliert aber Präsenz."
        )
    if ratio < 0.215:
        return (
            f"{case_diameter:g} mm sind an {wrist_cm:g} cm Handgelenk dezent und klassisch – "
            "passt gut zu eleganten Anlässen."
        )
    if ratio <= 0.255:
        return (
            f"{case_diameter:g} mm sitzen an {wrist_cm:g} cm Handgelenk im ausgewogenen Bereich – "
            "eine sichere Größe."
        )
    if ratio <= 0.29:
        return (
            f"{case_diameter:g} mm sind an {wrist_cm:g} cm Handgelenk sportlich präsent. "
            "Achte darauf, dass die Bandanstöße nicht überstehen."
        )
    return (
        f"{case_diameter:g} mm sind an {wrist_cm:g} cm Handgelenk sehr groß – "
        "die Uhr dominiert und rutscht unter Hemdmanschetten kaum durch."
    )
